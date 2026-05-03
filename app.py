import os
import psycopg2
import cloudinary
import cloudinary.uploader
from flask import Flask, render_template, request, redirect, session, send_file, abort
from werkzeug.utils import secure_filename
import requests
from io import BytesIO

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
# INIT TABLE (SAFE)
# -----------------------------
cur.execute("""
CREATE TABLE IF NOT EXISTS notes (
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
# HOME
# -----------------------------
@app.route("/home")
def home():
    branches = ["CSE", "ECE", "EEE", "MECH"]
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
# UPLOAD PAGE
# -----------------------------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        try:
            title = request.form["title"]
            branch = request.form["branch"]
            year = request.form["year"]
            subject = request.form["subject"]
            file = request.files["file"]

            if file.filename == "":
                return "No file selected"

            filename = secure_filename(file.filename)

            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                file,
                resource_type="raw"
            )

            file_url = result["secure_url"]

            # Save to DB
            cur.execute(
                "INSERT INTO notes (title, branch, year, subject, file_url) VALUES (%s,%s,%s,%s,%s)",
                (title, branch, year, subject, file_url)
            )
            conn.commit()

            return redirect(f"/notes/{branch}/{year}/{subject}")

        except Exception as e:
            return f"Upload Error: {str(e)}"

    return render_template("upload.html")


# -----------------------------
# DOWNLOAD FIX (IMPORTANT)
# -----------------------------
@app.route("/download/<int:id>")
def download(id):
    try:
        cur.execute("SELECT * FROM notes WHERE id=%s", (id,))
        note = cur.fetchone()

        if not note:
            return "File not found"

        file_url = note[5]   # correct column

        response = requests.get(file_url)

        return send_file(
            BytesIO(response.content),
            as_attachment=True,
            download_name="notes.pdf",   # FIXED EXTENSION
            mimetype="application/pdf"
        )

    except Exception as e:
        return f"Download Error: {str(e)}"


# -----------------------------
# ROOT REDIRECT
# -----------------------------
@app.route("/")
def index():
    return redirect("/home")


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)