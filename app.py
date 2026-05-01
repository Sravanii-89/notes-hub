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


# ✅ CALL AFTER DEFINITIONS
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

    # TOTAL NOTES
    cur.execute("SELECT COUNT(*) FROM notes")
    total_notes = cur.fetchone()[0]

    # TOTAL DOWNLOADS
    cur.execute("SELECT COALESCE(SUM(downloads), 0) FROM notes")
    total_downloads = cur.fetchone()[0]

    # USER DETAILS
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

    # -------- GET (open upload page) --------
    if request.method == "GET":
        branch = request.form.get("branch").strip().upper()
        year = request.form.get("year").strip()
        subject = request.form.get("subject").strip()

        return render_template(
            "upload.html",
            branch=branch,
            year=year,
            subject=subject
        )

    # -------- POST (upload file) --------
    if request.method == "POST":

        if "file" not in request.files:
            return "No file uploaded"

        file = request.files["file"]

        if file.filename == "":
            return "No file selected"

        try:
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(file, resource_type="raw")
            file_url = result["secure_url"]

        except Exception as e:
            return f"Upload failed: {str(e)}"

        # Get form data
        title = request.form.get("title")
        subject = request.form.get("subject")
        branch = request.form.get("branch")
        year = request.form.get("year")

        # Save to DB
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

        # ✅ CORRECT REDIRECT (THIS FIXES YOUR ERROR)
        return redirect(f"/notes/{branch}/{year}/{subject}")

subjects_data = {

# ---------- CSE ----------
"CSE": {
    "2": [
        "Design and Analysis of Algorithms",
        "Computer Organization and Architecture",
        "Operating Systems",
        "Database Management Systems",
        "Engineering economics and Project Management",
        "Discrete Mathematical Structures",
        "Object Oriented Programming With Java",
        "Problem Solving using Python",
        "Probability and Statistics Using Python",
        "Web Coding and Development",
        "Artificial Intelligence",
        "Mathematical Foundation for Data Science",
        "Foundations of Data Science",
        "Foundations of Machine Learning"
    ],
    "3": [
        "Optimization Techniques for ML",
        "Automata Theory & Language Processors",
        "Web Technologies",
        "Deep Learning for Data Science",
        "Data Analytics & Visualization",
        "Microprocessors and Microcontrollers",
        "Artificial Intelligence and Machine Learning",
        "Computer Networks",
        "Theory of Computation",
        "Artificial Neural Networks",
        "Backend Programming Languages",
        "Fundamentals of Security",
        "Fundamentals of Cloud Computing",
        "Compiler Design",
        "Cryptography and Network Security",
        "Software Engineering",
        "Cloud Services using AWS",
        "Cyber Security",
        "Web Application Frameworks",
        "Deep Learning Techniques"
    ],
    "4": [
        "Deep Learning",
        "Natural Language Processing",
        "Web Application Databases",
        "Cloud Security",
        "Cloud Security Essentials"
    ]
},

# ---------- EEE ----------
"EEE": {
    "2": [
        "Semiconductors and Devices",
        "Measurement Instruments",
        "Circuit Analysis II",
        "DC Machines",
        "Electromagnetic Field Theory",
        "Mathematics",
        "Linear Integrated Circuits",
        "Power Electronics",
        "Power Generation Transmission Distribution",
        "Signals and Systems"
    ],
    "3": [
        "Java OOP",
        "Control Systems",
        "Electrical Drives",
        "Power System Protection",
        "Economics & Project Management",
        "Power System Analysis",
        "Utilization of Electrical Energy"
    ]
},

# ---------- ECE ----------
"ECE": {
    "2": [
        "Python Programming",
        "Logic Circuit Design",
        "Electronic Devices and Circuits",
        "Signals and Systems",
        "Complex Variables",
        "Random Variables and Stochastic Process",
        "Linear Control Systems",
        "Analog and Digital Communication",
        "Object Oriented Programming",
        "Electromagnetic Waves and Transmission Lines",
        "Analog Electronic Circuits"
    ],
    "3": [
        "Linear & Digital IC Applications",
        "Microprocessors & Microcontrollers",
        "VLSI Design",
        "Antennas & Microwave Engineering",
        "Engineering Economics & Project Management",
        "Cellular & Mobile Communications",
        "Digital Signal Processing"
    ],
    "4": [
        "Project Work"
    ]
},

# ---------- CIVIL ----------
"CIVIL": {
    "3": [
        "RC Structures",
        "Environmental Engineering",
        "Foundation Engineering",
        "Hydrology",
        "OOPS",
        "Steel Structures",
        "Estimation & Costing"
    ]
},

# ---------- MECH ----------
"MECH": {
    "2": [
        "Materials & Manufacturing",
        "Machine Drawing",
        "Python Programming",
        "Fluid Mechanics",
        "Kinematics",
        "Thermodynamics",
        "Java OOP",
        "Applied Thermodynamics",
        "Dynamics of Machinery",
        "Metal Cutting",
        "Mechanics of Solids"
    ],
    "3": [
        "CAD & CAM",
        "Design of Machine Elements I",
        "Steam & Gas Turbines",
        "Measurements & Metrology",
        "Design of Machine Elements II",
        "FEM",
        "Heat Transfer"
    ],
    "4": [
        "Project Work"
    ]
},

# ---------- IT ----------
"IT": {
    "2": [
        "Python Programming and Applications",
        "Digital Logic Design",
        "Discrete Mathematical Structures",
        "Database Management Systems",
        "Data Communication Systems",
        "Object Oriented Programming through Java",
        "Probability and Statistics",
        "Computer Organization and Architecture",
        "Operating Systems",
        "Design and Analysis of Algorithms",
        "Web Technologies"
    ],
    "3": [
        "Computer Networking",
        "Artificial Intelligence",
        "Cloud Computing",
        "Software Engineering Principles",
        "Artificial Neural Networks",
        "Engineering Economics & Project Management",
        "Automata & Compiler Design",
        "Machine Learning",
        "Deep Learning"
    ],
    "4": [
        "Natural Language Processing"
    ]
},

# ---------- COMMON (1st Year) ----------
"COMMON": {
    "1": [
        "BEEE",
        "BCME",
        "Engineering Physics",
        "Engineering Graphics",
        "Engineering Chemistry",
        "Communicative English"
    ]
}
}

@app.route("/subjects/<branch>/<year>")
def subjects(branch, year):
    subjects = subjects_data.get(branch, {}).get(year, [])
    return render_template("subjects.html", subjects=subjects, branch=branch, year=year)

# ---------- BRANCH PAGE ----------
@app.route("/branch/<branch>")
def branch_page(branch):
    return render_template("years.html", branch=branch)


# ---------- YEAR PAGE ----------
@app.route("/year/<branch>/<year>")
def year_page(branch, year):
    subjects = subjects_data.get(branch, {}).get(year, [])
    return render_template("subjects.html", subjects=subjects, branch=branch, year=year)


# ---------- NOTES PAGE ----------
@app.route("/notes/<branch>/<year>/<subject>")
def notes(branch, year, subject):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, file_path
        FROM notes
        WHERE branch=%s AND year=%s AND subject=%s
    """, (branch, year, subject))

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



if __name__ == "__main__":
    app.run(debug=True)