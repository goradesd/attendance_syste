from flask import Flask, render_template, request, redirect, session, jsonify
from datetime import datetime
import sqlite3, os, base64

app = Flask(__name__)
app.secret_key = "fabledtech"
DB_FILE = "attendance.db"

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    password TEXT,
                    role TEXT DEFAULT 'employee')''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    emp_id TEXT,
                    date TEXT,
                    check_in TEXT,
                    check_out TEXT,
                    latitude TEXT,
                    longitude TEXT,
                    photo TEXT)''')
    # Default users
    c.execute("INSERT OR IGNORE INTO users VALUES ('F001', 'Ravi', 'Ravi123', 'Chif Oprating Officer')")
    c.execute("INSERT OR IGNORE INTO users VALUES ('F002', 'Rajendra', 'Raj123', 'Chif Marketing Officer')")
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'Admin User', 'admin123', 'admin')")
    conn.commit()
    conn.close()

init_db()
os.makedirs("static/photos", exist_ok=True)

# ---------- ROUTES ----------
@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        emp_id = request.form['emp_id']
        password = request.form['password']
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id=? AND password=?", (emp_id, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['emp_id'] = user[0]
            session['name'] = user[1]
            session['role'] = user[3]
            if user[3] == 'admin':
                return redirect('/admin')
            return redirect('/dashboard')
        else:
            return render_template('login.html', error="Invalid credentials!")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'emp_id' not in session:
        return redirect('/login')
    return render_template('dashboard.html', name=session['name'])

@app.route('/checkin', methods=['POST'])
def checkin():
    if 'emp_id' not in session:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    emp_id = session['emp_id']
    name = session['name']
    today = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")
    lat = data.get('latitude')
    lon = data.get('longitude')
    photo_data = data.get('photo')

    # Save photo
    photo_filename = f"{emp_id}_{today}_{current_time.replace(':','-')}.jpg"
    photo_path = os.path.join("static/photos", photo_filename)
    if photo_data:
        photo_bytes = base64.b64decode(photo_data.split(",")[1])
        with open(photo_path, "wb") as f:
            f.write(photo_bytes)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM attendance WHERE emp_id=? AND date=?", (emp_id, today))
    record = c.fetchone()

    if not record:
        c.execute("""INSERT INTO attendance 
                     (emp_id, date, check_in, latitude, longitude, photo) 
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (emp_id, today, current_time, lat, lon, photo_filename))
        conn.commit()
        message = f"✅ {name} checked in at {current_time}"
    elif not record[4]:
        c.execute("""UPDATE attendance 
                     SET check_out=?, latitude=?, longitude=?, photo=? 
                     WHERE emp_id=? AND date=?""",
                  (current_time, lat, lon, photo_filename, emp_id, today))
        conn.commit()
        message = f"👋 {name} checked out at {current_time}"
    else:
        message = "⚠️ You already checked out today."
    conn.close()
    return jsonify({"message": message})

@app.route('/admin')
def admin():
    if 'role' not in session or session['role'] != 'admin':
        return redirect('/login')
    conn = sqlite3.connect(DB_FILE)
    df = conn.execute("SELECT * FROM attendance").fetchall()
    conn.close()
    return render_template('admin.html', records=df)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
