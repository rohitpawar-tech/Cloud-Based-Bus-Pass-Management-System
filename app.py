from flask import Flask, render_template, request, redirect, session
import sqlite3
import uuid
import datetime

app = Flask(__name__)
app.secret_key = "supersecretbuspass"

# ---------------- DATABASE INIT ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT 'user'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS passes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            route TEXT,
            duration TEXT,
            price INTEGER,
            pass_id TEXT UNIQUE,
            booking_date TEXT,
            status TEXT DEFAULT 'Active'
        )
    """)

    conn.commit()
    conn.close()

# ---------------- HOME ----------------
@app.route("/")
def home():
    return redirect("/login")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                           (name, email, password))
            conn.commit()
        except:
            conn.close()
            return "User already exists!"
        conn.close()
        return redirect("/login")

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["name"] = user[1]
            session["role"] = user[4]
            return redirect("/dashboard")
        else:
            return "Invalid Credentials"

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("dashboard.html", name=session["name"])

# ---------------- BOOK PASS ----------------
@app.route("/book_pass", methods=["GET", "POST"])
def book_pass():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        route = request.form["route"]
        duration = request.form["duration"]

        price_map = {
            "Monthly": 1000,
            "Quarterly": 2500,
            "Half-Yearly": 4500
        }

        price = price_map.get(duration, 0)
        pass_id = str(uuid.uuid4())[:8].upper()
        booking_date = datetime.datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO passes (user_id, route, duration, price, pass_id, booking_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session["user_id"], route, duration, price, pass_id, booking_date))
        conn.commit()
        conn.close()

        return redirect("/my_passes")

    return render_template("book_pass.html")

# ---------------- VIEW ALL PASSES ----------------
@app.route("/my_passes")
def my_passes():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, route, duration, price, pass_id, booking_date, status
        FROM passes WHERE user_id=? ORDER BY id DESC
    """, (session["user_id"],))
    passes = cursor.fetchall()
    conn.close()

    return render_template("my_passes.html", passes=passes)

# ---------------- CANCEL PASS ----------------
@app.route("/cancel_pass/<int:pass_id>")
def cancel_pass(pass_id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE passes SET status='Cancelled' WHERE id=?", (pass_id,))
    conn.commit()
    conn.close()
    return redirect("/my_passes")

# ---------------- ADMIN PANEL ----------------
@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return "Access Denied"

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM passes")
    total_passes = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(price) FROM passes WHERE status='Active'")
    total_revenue = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT users.name, passes.route, passes.duration, passes.price, passes.status
        FROM passes JOIN users ON users.id = passes.user_id
    """)
    records = cursor.fetchall()

    conn.close()

    return render_template("admin.html",
                           total_passes=total_passes,
                           total_revenue=total_revenue,
                           records=records)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
