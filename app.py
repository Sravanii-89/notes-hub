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
# DATABASE FIX (IMPORTANT)
# -----------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

# -----------------------------
# CLOUDINARY CONFIG
# -----------------------------
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# -----------------------------
# INIT TABLES
# -----------------------------
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

# -----------------------------
# LOGIN
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        if user and check_password_hash(user[3], password):
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
            return redirect("/")
        except:
            return "User already exists"

    return render_template("register.html")


# -----------------------------
# HOME (BRANCHES)
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
# NOTES PAGE
# -----------------------------
@app.route("/notes/<branch>/<year>/<subject>")
def notes(branch, year, subject):
    cur.execute(
        "SELECT * FROM notes WHERE branch=%s AND year=%s AND subject=%s",
        (branch, year, subject)
    )
    data = cur.fetchall()

    return render_template(
        "notes.html",
        notes=data,
        branch=branch,
        year=year,
        subject=subject
    )


# -----------------------------
# UPLOAD
# -----------------------------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    branch = request.args.get("branch")
    year = request.args.get("year")
    subject = request.args.get("subject")

    if request.method == "POST":
        try:
            title = request.form["title"]
            file = request.files["file"]

            result = cloudinary.uploader.upload(file, resource_type="raw")
            file_url = result["secure_url"]

            cur.execute(
                "INSERT INTO notes (title, branch, year, subject, file_url) VALUES (%s,%s,%s,%s,%s)",
                (title, branch, year, subject, file_url)
            )
            conn.commit()

            return redirect(f"/notes/{branch}/{year}/{subject}")

        except Exception as e:
            return f"Upload Error: {str(e)}"

    return render_template("upload.html", branch=branch, year=year, subject=subject)


# -----------------------------
# DOWNLOAD (FINAL FIX)
# -----------------------------
@app.route("/download/<int:id>")
def download(id):
    cur.execute("SELECT * FROM notes WHERE id=%s", (id,))
    note = cur.fetchone()

    if not note:
        return "File not found"

    file_url = note[5]

    response = requests.get(file_url)

    return send_file(
        BytesIO(response.content),
        as_attachment=True,
        download_name="notes.pdf",
        mimetype="application/pdf"
    )


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)