from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
DB = "shoghlni.db"

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        price INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS interests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        UNIQUE(job_id, user_id),
        FOREIGN KEY(job_id) REFERENCES jobs(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    conn.commit()
    conn.close()

@app.context_processor
def common():
    return {"current_user": session.get("username")}

@app.route("/")
def home():
    q = request.args.get("q", "").strip()
    conn = db()
    if q:
        jobs = conn.execute(
            "SELECT jobs.*, users.username FROM jobs JOIN users ON users.id=jobs.user_id "
            "WHERE jobs.title LIKE ? OR jobs.description LIKE ? ORDER BY jobs.id DESC",
            (f"%{q}%", f"%{q}%")
        ).fetchall()
    else:
        jobs = conn.execute(
            "SELECT jobs.*, users.username FROM jobs JOIN users ON users.id=jobs.user_id "
            "ORDER BY jobs.id DESC"
        ).fetchall()
    conn.close()
    return render_template("index.html", jobs=jobs, q=q)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        if len(username) < 3 or len(password) < 6:
            flash("اسم المستخدم 3 حروف على الأقل وكلمة السر 6 حروف على الأقل.")
            return redirect(url_for("register"))
        conn = db()
        try:
            conn.execute("INSERT INTO users(username,password) VALUES (?,?)",
                         (username, generate_password_hash(password)))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash("اسم المستخدم مستخدم بالفعل.")
            return redirect(url_for("register"))
        conn.close()
        flash("تم إنشاء الحساب، سجل دخولك.")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        conn = db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("home"))
        flash("اسم المستخدم أو كلمة السر غير صحيحة.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/add", methods=["GET", "POST"])
def add_job():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        try:
            price = int(request.form["price"])
        except ValueError:
            flash("اكتب سعرًا صحيحًا.")
            return redirect(url_for("add_job"))
        if not title or not description or price < 0:
            flash("املأ البيانات بشكل صحيح.")
            return redirect(url_for("add_job"))
        conn = db()
        conn.execute("INSERT INTO jobs(title,description,price,user_id) VALUES (?,?,?,?)",
                     (title, description, price, session["user_id"]))
        conn.commit()
        conn.close()
        return redirect(url_for("home"))
    return render_template("add.html")

@app.route("/job/<int:job_id>")
def job(job_id):
    conn = db()
    item = conn.execute(
        "SELECT jobs.*, users.username FROM jobs JOIN users ON users.id=jobs.user_id WHERE jobs.id=?",
        (job_id,)
    ).fetchone()
    conn.close()
    if not item:
        return "الشغلة غير موجودة", 404
    return render_template("job.html", job=item)

@app.post("/interest/<int:job_id>")
def interest(job_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = db()
    try:
        conn.execute("INSERT INTO interests(job_id,user_id) VALUES (?,?)",
                     (job_id, session["user_id"]))
        conn.commit()
        flash("تم تسجيل اهتمامك بالشغلة.")
    except sqlite3.IntegrityError:
        flash("أنت سجلت اهتمامك بالشغلة دي بالفعل.")
    conn.close()
    return redirect(url_for("job", job_id=job_id))

if __name__ == "__main__":
    init_db()
app.run(host="0.0.0.0", port=5000, debug=True)
