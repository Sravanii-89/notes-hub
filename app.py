import os
from flask import Flask, render_template, request, redirect, session
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# ---------- INIT DB ----------
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
    },
    "ECE": {
        "1": ["Engineering Physics","Engineering Chemistry","Mathematics I","Programming in C","English","Engineering Graphics"],
        "2": ["Electronic Devices","Circuit Analysis","Electromagnetic Fields","Signals and Systems","Digital Logic Design","Communication Engineering"],
        "3": ["Control Systems","Power Electronics","Microprocessors","VLSI Design","Antennas and Wave Propagation","Optical Communication"],
        "4": ["Renewable Energy Systems","Power Systems","Telecommunication Engineering","Embedded Systems","Wireless Communication","Project Work"]
    },
    "EEE": {
        "1": ["Engineering Physics","Engineering Chemistry","Mathematics I","Programming in C","English","Engineering Graphics"],
        "2": ["Circuit Analysis","Electromagnetic Fields","Signals and Systems","Electrical Machines","Power Systems","Control Systems"],
        "3": ["Power Electronics","Microprocessors","Renewable Energy Systems","Power System Protection","Electrical Measurements","Project Work"],
        "4": ["Smart Grid Technology","High Voltage Engineering","Electric Vehicle Technology","Energy Storage Systems","Power System Stability","Project Work"]
    },
    "CIVIL": {
        "1": ["Engineering Physics","Engineering Chemistry","Mathematics I","Programming in C","English","Engineering Graphics"],
        "2": ["Strength of Materials","Fluid Mechanics","Surveying","Structural Analysis","Geotechnical Engineering","Construction Materials"],
        "3": ["Transportation Engineering","Environmental Engineering","Water Resources Engineering","Concrete Technology","Project Management","Project Work"],
        "4": ["Advanced Structural Analysis","Earthquake Engineering","Sustainable Construction Practices","Construction Planning and Management","Hydrology and Irrigation Engineering","Project Work"]
    },
    "MECH": {
        "1": ["Engineering Physics","Engineering Chemistry","Mathematics I","Programming in C","English","Engineering Graphics"],
        "2": ["Engineering Mechanics","Thermodynamics","Fluid Mechanics","Manufacturing Processes","Material Science","Dynamics of Machinery"],
        "3": ["Heat Transfer","Machine Design","Control Systems","Automobile Engineering","Robotics","Project Work"],
        "4": ["Renewable Energy Systems","Finite Element Analysis","Mechatronics","Computer-Aided Design (CAD)","Advanced Manufacturing Processes","Project Work"]
    },
    "IT": {
        "1": ["Engineering Physics","Engineering Chemistry","Mathematics I","Programming in C","English","Engineering Graphics"],
        "2": ["Data Structures","Database Management Systems","Operating Systems","Computer Networks","OOPs using Java","Discrete Mathematics"],
        "3": ["Compiler Design","Machine Learning","Artificial Intelligence","Web Technologies","Software Engineering","Data Analytics"],
        "4": ["Cloud Computing","Cyber Security","Big Data","Blockchain","Deep Learning","Project Work"]
    }
}

# ---------- ROUTES ----------

@app.route("/", methods=["GET","POST"])
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
    if request.method == "GET":
        return render_template(
            "upload.html",
            branch=request.args.get("branch"),
            year=request.args.get("year"),
            subject=request.args.get("subject")
        )

    file = request.files["file"]

    result = cloudinary.uploader.upload(file, resource_type="auto")
    file_url = result["secure_url"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO notes (title, branch, year, subject, file_path)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        request.form["title"],
        request.form["branch"],
        request.form["year"],
        request.form["subject"],
        file_url
    ))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(f"/notes/{request.form['branch']}/{request.form['year']}/{request.form['subject']}")


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

    return redirect(note[0])   # simple + stable


if __name__ == "__main__":
    app.run(debug=True)