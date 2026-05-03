import os
from flask import Flask, render_template, request, redirect, session, url_for
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
        file_path TEXT,
        uploaded_by INTEGER,
        downloads INTEGER DEFAULT 0
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
    },
    "ECE": {
        "1": ["Engineering Physics","Engineering Chemistry","Mathematics I","Basic Electrical Engineering","English","Engineering Graphics"],
        "2": ["Electronic Devices","Signals and Systems","Digital Logic Design","Network Theory","Mathematics II"],
        "3": ["Analog Communications","Microprocessors","Control Systems","Digital Signal Processing","VLSI Design"],
        "4": ["Wireless Communication","Embedded Systems","IoT","Satellite Communication","Project Work"]
    },
    "EEE": {
        "1": ["Engineering Physics","Engineering Chemistry","Mathematics I","Basic Electrical Engineering","English"],
        "2": ["Electrical Machines I","Network Theory","Control Systems","Electrical Measurements","Mathematics II"],
        "3": ["Power Systems","Electrical Machines II","Power Electronics","Microcontrollers"],
        "4": ["Renewable Energy Systems","Smart Grid","HVDC Transmission","Project Work"]
    },
    "MECH": {
        "1": ["Engineering Mechanics","Engineering Physics","Mathematics I","Engineering Graphics","English"],
        "2": ["Thermodynamics","Fluid Mechanics","Manufacturing Processes","Strength of Materials"],
        "3": ["Machine Design","Heat Transfer","Dynamics of Machines","Industrial Engineering"],
        "4": ["CAD/CAM","Robotics","Automation","Project Work"]
    },
    "CIVIL": {
        "1": ["Engineering Mechanics","Engineering Physics","Mathematics I","Engineering Graphics","English"],
        "2": ["Structural Analysis","Fluid Mechanics","Geotechnical Engineering","Surveying"],
        "3": ["Reinforced Concrete","Environmental Engineering","Transportation Engineering"],
        "4": ["Construction Management","Urban Planning","Project Work"]
    },
    "IT": {
        "1": ["Engineering Physics","Engineering Chemistry","Mathematics I","Programming in C","English"],
        "2": ["Data Structures","Database Systems","Operating Systems","Computer Networks"],
        "3": ["Web Technologies","Software Engineering","Machine Learning","Cloud Computing"],
        "4": ["Cyber Security","Big Data Analytics","AI","Project Work"]
    }
}

# ---------- AUTH ----------
@app.route("/", methods=["GET","POST"])
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


@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()

        name = request.form.get("name")
        email = request.form.get("email")
        password = generate_password_hash(request.form.get("password"))
        branch = request.form.get("branch")
        year = request.form.get("year")

        try:
            cur.execute("INSERT INTO users(name,email,password,branch,year) VALUES(%s,%s,%s,%s,%s)",
                        (name,email,password,branch,year))
            conn.commit()
        except:
            return "Email already exists"

        cur.close()
        conn.close()
        return redirect("/")

    return render_template("register.html")


# ---------- HOME (BRANCHES) ----------
@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect("/")
    branches = list(subjects_data.keys())
    return render_template("home.html", branches=branches)


# ---------- YEAR PAGE ----------
@app.route("/branch/<branch>")
def branch_page(branch):
    return render_template("years.html", branch=branch)


# ---------- SUBJECT PAGE ----------
@app.route("/year/<branch>/<year>")
def year_page(branch, year):
    subjects = subjects_data.get(branch, {}).get(year, [])
    return render_template("subjects.html", subjects=subjects, branch=branch, year=year)


# ---------- NOTES PAGE ----------
@app.route("/notes/<branch>/<year>/<subject>")
def notes(branch, year, subject):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""SELECT id, title, file_path FROM notes
                   WHERE branch=%s AND year=%s AND subject=%s""",
                (branch, year, subject))
    notes = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("notes.html",
                           notes=notes,
                           branch=branch,
                           year=year,
                           subject=subject)


# ---------- UPLOAD ----------
@app.route("/upload", methods=["GET","POST"])
def upload():
    if "user_id" not in session:
        return redirect("/")

    if request.method == "POST":
        title = request.form.get("title")
        branch = request.form.get("branch")
        year = request.form.get("year")
        subject = request.form.get("subject")
        file = request.files.get("file")

        if not file:
            return "No file selected"

        # Upload as RAW so PDFs open without 401
        result = cloudinary.uploader.upload(
            file,
            resource_type="raw",
            format="pdf"
        )
        file_url = result.get("secure_url")

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO notes(title,subject,branch,year,file_path,uploaded_by)
            VALUES(%s,%s,%s,%s,%s,%s)
        """, (title, subject, branch, year, file_url, session["user_id"]))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(f"/notes/{branch}/{year}/{subject}")

    # GET (auto-fill from URL)
    return render_template("upload.html",
                           branch=request.args.get("branch",""),
                           year=request.args.get("year",""),
                           subject=request.args.get("subject",""))


# ---------- DOWNLOAD ----------
@app.route("/download/<int:note_id>")
def download(note_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT file_path FROM notes WHERE id=%s", (note_id,))
    note = cur.fetchone()

    if not note:
        return "File not found"

    file_url = note[0]

    cur.execute("UPDATE notes SET downloads = downloads + 1 WHERE id=%s", (note_id,))
    conn.commit()

    cur.close()
    conn.close()

    return redirect(file_url + "?fl_attachment=true")
@app.route("/clear")
def clear_notes():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM notes")
    conn.commit()
    cur.close()
    conn.close()
    return "All notes deleted"


if __name__ == "__main__":
    app.run(debug=True)