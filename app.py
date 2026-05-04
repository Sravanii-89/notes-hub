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
    file_url TEXT,
    filename TEXT
)
""")

cur.execute("""
ALTER TABLE notes
ADD COLUMN IF NOT EXISTS filename TEXT
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
    branches = ["CSE", "ECE", "EEE", "MECH", "IT", "CIVIL"]
    years = ["1", "2", "3", "4"]

    if request.method == "POST":
        try:
            if "file" not in request.files:
                return "Upload Error: No file selected", 400

            file = request.files["file"]
            if file.filename == "":
                return "Upload Error: No file selected", 400

            title = request.form.get("title", "Untitled")
            branch = request.form.get("branch")
            year = request.form.get("year")
            subject = request.form.get("subject")

            if not branch or not year or not subject:
                return "Upload Error: Branch, year, and subject are required.", 400

            conn = get_db()
            cur = conn.cursor()

            result = cloudinary.uploader.upload(file, resource_type="auto")
            file_url = result.get("secure_url")
            filename = file.filename or "notes.pdf"

            cur.execute(
                "INSERT INTO notes (title, branch, year, subject, file_url, filename) VALUES (%s,%s,%s,%s,%s,%s)",
                (title, branch, year, subject, file_url, filename)
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
        subject=request.args.get("subject"),
        branches=branches,
        years=years
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
    file_name = note[6] if len(note) > 6 and note[6] else f"{note[1]}.pdf"

    try:
        response = requests.get(file_url, stream=True)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "application/octet-stream")
        return send_file(
            BytesIO(response.content),
            as_attachment=True,
            download_name=file_name,
            mimetype=content_type
        )
    except Exception as e:
        return f"Download failed: {str(e)}", 500


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)