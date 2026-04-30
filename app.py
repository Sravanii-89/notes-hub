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

if not DATABASE_URL:
    raise Exception("DATABASE_URL not set")
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

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

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
    return render_template("home.html")

# ---------- UPLOAD ----------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user_id" not in session:
        return redirect("/")

    if request.method == "POST":
        file = request.files["file"]

        result = cloudinary.uploader.upload(file, resource_type="auto")
        file_url = result["secure_url"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO notes (title, subject, branch, year, file_path, uploaded_by)
        VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            request.form["title"],
            request.form["subject"],
            request.form["branch"],
            request.form["year"],
            file_url,
            session["user_id"]
        ))

        conn.commit()
        cur.close()
        conn.close()

        return redirect("/home")

    return render_template("upload.html")

if __name__ == "__main__":
    app.run(debug=True)