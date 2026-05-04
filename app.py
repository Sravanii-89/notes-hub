import os
import psycopg2
import cloudinary
import cloudinary.uploader
import requests
from io import BytesIO

from flask import Flask, render_template, request, redirect, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "secret")

# -----------------------------
# DATABASE
# -----------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


# -----------------------------
# CLOUDINARY
# -----------------------------
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# -----------------------------
# INIT TABLES
# -----------------------------
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
    branch TEXT,
    year TEXT,
    subject TEXT,
    file_url TEXT
)
""")

conn.commit()
cur.close()
conn.close()

# -----------------------------
# LOGIN
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email=%s", (request.form["email"],))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and check_password_hash(user[3], request.form["password"]):
            session["user_id"] = user[0]
            return redirect("/home")

        return "Invalid login"

    return render_template("login.html")


# -----------------------------
# REGISTER
# -----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            conn = get_db()
            cur = conn.cursor()

            cur.execute(
                "INSERT INTO users (name,email,password,branch,year) VALUES (%s,%s,%s,%s,%s)",
                (
                    request.form["name"],
                    request.form["email"],
                    generate_password_hash(request.form["password"]),
                    request.form["branch"],
                    request.form["year"]
                )
            )
            conn.commit()

            cur.close()
            conn.close()

            return redirect("/")
        except:
            return "User already exists"

    return render_template("register.html")


# -----------------------------
# HOME
# -----------------------------
@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect("/")

    branches = ["CSE", "ECE", "EEE", "MECH", "IT", "CIVIL"]
    return render_template("home.html", branches=branches)


# -----------------------------
# YEARS
# -----------------------------
@app.route("/branch/<branch>")
def branch(branch):
    return render_template("years.html", branch=branch)


# -----------------------------
# SUBJECTS
# -----------------------------
@app.route("/year/<branch>/<year>")
def year(branch, year):
    subjects = [
        "Mathematics",
        "Physics",
        "Chemistry",
        "Database Management Systems",
        "Operating Systems",
        "Computer Networks"
    ]
    return render_template("subjects.html", branch=branch, year=year, subjects=subjects)


# -----------------------------
# NOTES
# -----------------------------
@app.route("/notes/<branch>/<year>/<subject>")
def notes(branch, year, subject):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM notes WHERE branch=%s AND year=%s AND subject=%s",
        (branch, year, subject)
    )
    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("notes.html", notes=data, branch=branch, year=year, subject=subject)


# -----------------------------
# UPLOAD (FIXED)
# -----------------------------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        try:
            conn = get_db()
            cur = conn.cursor()

            title = request.form["title"]
            branch = request.form["branch"]
            year = request.form["year"]
            subject = request.form["subject"]
            file = request.files["file"]

            result = cloudinary.uploader.upload(file, resource_type="raw")
            file_url = result["secure_url"]

            cur.execute(
                "INSERT INTO notes (title, branch, year, subject, file_url) VALUES (%s,%s,%s,%s,%s)",
                (title, branch, year, subject, file_url)
            )
            conn.commit()

            cur.close()
            conn.close()

            return redirect(f"/notes/{branch}/{year}/{subject}")

        except Exception as e:
            return f"Upload Error: {str(e)}"

    # GET
    return render_template(
        "upload.html",
        branch=request.args.get("branch"),
        year=request.args.get("year"),
        subject=request.args.get("subject")
    )


# -----------------------------
# DOWNLOAD (FIXED)
# -----------------------------
@app.route("/download/<int:id>")
def download(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM notes WHERE id=%s", (id,))
    note = cur.fetchone()

    cur.close()
    conn.close()

    if not note:
        return "File not found", 404

    file_url = note[5]

    try:
        response = requests.get(file_url)
        return send_file(
            BytesIO(response.content),
            as_attachment=True,
            download_name="notes.pdf",
            mimetype="application/pdf"
        )
    except Exception as e:
        return f"Download failed: {str(e)}", 500


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)