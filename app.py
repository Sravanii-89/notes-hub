from flask import Flask, render_template, request, redirect, session
import psycopg2
import os
import cloudinary
import cloudinary.uploader
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecret")

# ---------- CLOUDINARY ----------
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

# ---------- DATABASE ----------
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        branch TEXT,
        year TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id SERIAL PRIMARY KEY,
        title TEXT,
        subject TEXT,
        branch TEXT,
        year TEXT,
        file_path TEXT,
        uploaded_by INTEGER,
        downloads INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

init_db()

# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        email = request.form.get("email")
        password = request.form.get("password")

        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if not user:
            return "User not found"

        if not check_password_hash(user[3], password):
            return "Wrong password"

        session["user_id"] = user[0]
        return redirect("/home")

    return render_template("login.html")

# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email=%s", (request.form["email"],))
        if cur.fetchone():
            return "User already exists"

        hashed = generate_password_hash(request.form["password"])

        cur.execute("""
        INSERT INTO users (name, email, password, branch, year)
        VALUES (%s,%s,%s,%s,%s)
        """, (
            request.form["name"],
            request.form["email"],
            hashed,
            request.form["branch"],
            request.form["year"]
        ))

        conn.commit()
        cur.close()
        conn.close()

        return redirect("/")

    return render_template("register.html")

# ---------- HOME ----------
@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM notes")
    total_notes = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(downloads), 0) FROM notes")
    total_downloads = cur.fetchone()[0]

    cur.execute("SELECT name, branch, year FROM users WHERE id=%s", (session["user_id"],))
    user = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        "home.html",
        total_notes=total_notes,
        total_downloads=total_downloads,
        user=user
    )

# ---------- UPLOAD ----------
@app.route("/upload", methods=["GET", "POST"])
def upload():

    if "user_id" not in session:
        return redirect("/")

    # -------- GET --------
    if request.method == "GET":
        branch = request.args.get("branch", "").strip().upper()
        year = request.args.get("year", "").strip()
        subject = request.args.get("subject", "").strip()

        return render_template(
            "upload.html",
            branch=branch,
            year=year,
            subject=subject
        )

    # -------- POST --------
    if request.method == "POST":

        if "file" not in request.files:
            return "No file uploaded"

        file = request.files["file"]

        if file.filename == "":
            return "No file selected"

        try:
            result = cloudinary.uploader.upload(file, resource_type="raw")
            file_url = result["secure_url"]
        except Exception as e:
            return f"Upload failed: {str(e)}"

        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "").strip()
        branch = request.form.get("branch", "").strip().upper()
        year = request.form.get("year", "").strip()

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO notes (title, subject, branch, year, file_path, uploaded_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            title,
            subject,
            branch,
            year,
            file_url,
            session.get("user_id")
        ))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(f"/notes/{branch}/{year}/{subject}")

# ---------- SUBJECT DATA ----------
subjects_data = {
    "CSE": {"2": ["Database Management Systems"]},
    "EEE": {"2": ["DC Machines"]},
    "ECE": {"2": ["Signals and Systems"]},
    "IT": {"2": ["DBMS"]},
    "COMMON": {"1": ["Engineering Physics"]}
}

# ---------- SUBJECT PAGE ----------
@app.route("/subjects/<branch>/<year>")
def subjects(branch, year):
    subjects = subjects_data.get(branch, {}).get(year, [])
    return render_template("subjects.html", subjects=subjects, branch=branch, year=year)

# ---------- BRANCH ----------
@app.route("/branch/<branch>")
def branch_page(branch):
    return render_template("years.html", branch=branch)

# ---------- YEAR ----------
@app.route("/year/<branch>/<year>")
def year_page(branch, year):
    subjects = subjects_data.get(branch, {}).get(year, [])
    return render_template("subjects.html", subjects=subjects, branch=branch, year=year)

# ---------- NOTES ----------
@app.route("/notes/<branch>/<year>/<subject>")
def notes(branch, year, subject):

    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, file_path
        FROM notes
        WHERE LOWER(branch)=LOWER(%s)
        AND year=%s
        AND LOWER(subject)=LOWER(%s)
    """, (branch.strip(), year.strip(), subject.strip()))

    notes = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "notes.html",
        notes=notes,
        branch=branch,
        year=year,
        subject=subject
    )

# ---------- DOWNLOAD ----------
@app.route("/download/<int:note_id>")
def download(note_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT file_path FROM notes WHERE id=%s", (note_id,))
    file = cur.fetchone()

    if not file:
        return "File not found"

    file_url = file[0]

    cur.execute("UPDATE notes SET downloads = downloads + 1 WHERE id=%s", (note_id,))
    conn.commit()

    cur.close()
    conn.close()

    return redirect(file_url)

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)