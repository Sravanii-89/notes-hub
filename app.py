import os
from flask import Flask, render_template, request, redirect, session
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# ---------- DB ----------
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        branch TEXT,
        year TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notes(
        id SERIAL PRIMARY KEY,
        title TEXT,
        subject TEXT,
        branch TEXT,
        year TEXT,
        file_path TEXT
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

init_db()

# ---------- CLOUDINARY ----------
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# ---------- SUBJECT DATA ----------
subjects_data = {
    "CSE": {
        "1": ["Engineering Physics","Engineering Chemistry","Mathematics I","Programming in C","English","Engineering Graphics"],
        "2": ["Data Structures","Database Management Systems","Operating Systems","Computer Networks","OOPs using Java","Discrete Mathematics"],
        "3": ["Compiler Design","Machine Learning","Artificial Intelligence","Web Technologies","Software Engineering","Data Analytics"],
        "4": ["Cloud Computing","Cyber Security","Big Data","Blockchain","Deep Learning","Project Work"]
    }
}

# ---------- LOGIN ----------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        email = request.form["email"]
        password = request.form["password"]

        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and check_password_hash(user[3], password):
            session["user_id"] = user[0]
            return redirect("/home")

        return "Invalid login"

    return render_template("login.html")


# ---------- REGISTER ----------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO users(name,email,password,branch,year)
                VALUES(%s,%s,%s,%s,%s)
            """, (
                request.form["name"],
                request.form["email"],
                generate_password_hash(request.form["password"]),
                request.form["branch"],
                request.form["year"]
            ))
            conn.commit()
        except:
            return "Email exists"

        cur.close()
        conn.close()
        return redirect("/")

    return render_template("register.html")


# ---------- HOME ----------
@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect("/")
    return render_template("home.html", branches=list(subjects_data.keys()))


@app.route("/branch/<branch>")
def branch_page(branch):
    return render_template("years.html", branch=branch)


@app.route("/year/<branch>/<year>")
def year_page(branch, year):
    subjects = subjects_data.get(branch, {}).get(year, [])
    return render_template("subjects.html", subjects=subjects, branch=branch, year=year)


# ---------- NOTES ----------
@app.route("/notes/<branch>/<year>/<subject>")
def notes(branch, year, subject):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, file_path FROM notes
        WHERE branch=%s AND year=%s AND subject=%s
    """, (branch, year, subject))

    notes = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("notes.html", notes=notes, branch=branch, year=year, subject=subject)


# ---------- UPLOAD ----------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    # GET → open page with values
    if request.method == "GET":
        return render_template(
            "upload.html",
            branch=request.args.get("branch"),
            year=request.args.get("year"),
            subject=request.args.get("subject")
        )

    # POST → upload file
    title = request.form["title"]
    branch = request.form["branch"]
    year = request.form["year"]
    subject = request.form["subject"]
    file = request.files["file"]

    if not file:
        return "No file selected"

    # Upload to Cloudinary
    result = cloudinary.uploader.upload(file, resource_type="raw")
    file_url = result["secure_url"]

    # Save to DB
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO notes (title, branch, year, subject, file_path)
        VALUES (%s, %s, %s, %s, %s)
    """, (title, branch, year, subject, file_url))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(f"/notes/{branch}/{year}/{subject}")
# ---------- DOWNLOAD ----------
@app.route("/download/<int:note_id>")
def download(note_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT file_path FROM notes WHERE id=%s", (note_id,))
    note = cur.fetchone()

    cur.close()
    conn.close()

    if not note:
        return "File not found", 404

    return redirect(note[0])


if __name__ == "__main__":
    app.run(debug=True)