import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'darkwick_system_key_2026'
app.config['SESSION_COOKIE_SECURE'] = True  # บังคับให้ส่ง Cookie เฉพาะผ่าน HTTPS เท่านั้น (แนะนำให้เปิดใช้งานเมื่อขึ้น production ที่มี SSL แล้ว)
app.config['SESSION_COOKIE_HTTPONLY'] = True # ป้องกันไม่ให้ JavaScript สามารถเข้าถึง Cookie ได้ ช่วยลดความเสี่ยงจากการโจรกรรม Session ผ่าน XSS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' # ป้องกันการโจมตีแบบ CSRF เบื้องต้น (สามารถปรับเป็น 'Strict' ได้ตามความเหมาะสม)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TEACHER_USER = "admin"
TEACHER_PASS_HASH = generate_password_hash("1234")

def get_db():
    conn = sqlite3.connect('students.db')
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            fullname TEXT NOT NULL,
            grade TEXT,
            phone TEXT,
            address TEXT,
            height REAL,
            weight REAL,
            profile_img TEXT,
            status TEXT DEFAULT 'รอตรวจสอบ',
            note TEXT,
            updated_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS height_weight_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            height REAL,
            weight REAL,
            recorded_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    if session.get('role') == 'student':
        return redirect(url_for('student_profile'))
    elif session.get('role') == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role')
        username = request.form.get('username')
        password = request.form.get('password')

        if role == 'teacher':
            if username == TEACHER_USER and check_password_hash(TEACHER_PASS_HASH, password):
                session['role'] = 'teacher'
                session['user'] = username
                flash('เข้าสู่ระบบครูประจำชั้นสำเร็จ', 'success')
                return redirect(url_for('teacher_dashboard'))
            else:
                flash('ชื่อผู้ใช้หรือรหัสผ่านครูไม่ถูกต้อง!', 'error')
        elif role == 'student':
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM students WHERE student_id = ?", (username,))
            s = c.fetchone()
            conn.close()

            if s and check_password_hash(s['password'], password):
                session['role'] = 'student'
                session['student_id'] = s['student_id']
                flash('เข้าสู่ระบบสำเร็จ!', 'success')
                return redirect(url_for('student_profile'))
            else:
                flash('รหัสนักเรียนหรือรหัสผ่านไม่ถูกต้อง!', 'error')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        password = request.form.get('password')
        fullname = request.form.get('fullname')

        if not student_id or not password or not fullname:
            flash('กรุณากรอกข้อมูลให้ครบทุกช่อง', 'error')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO students (student_id, password, fullname, updated_at) VALUES (?, ?, ?, ?)",
                      (student_id, hashed_password, fullname, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            flash('ลงทะเบียนสำเร็จ! กรุณาเข้าสู่ระบบ', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('รหัสนักเรียนนี้มีในระบบแล้ว!', 'error')

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('ออกจากระบบเรียบร้อยแล้ว', 'info')
    return redirect(url_for('login'))

@app.route('/student')
def student_profile():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM students WHERE student_id = ?", (session.get('student_id'),))
    s = c.fetchone()

    if not s:
        conn.close()
        session.clear()
        return redirect(url_for('login'))

    c.execute("SELECT height, weight, recorded_at FROM height_weight_history WHERE student_id = ? ORDER BY id DESC LIMIT 5", (session.get('student_id'),))
    history = c.fetchall()
    conn.close()

    bmi, bmi_text = None, "-"
    if s['height'] and s['weight']:
        try:
            h_m = float(s['height']) / 100
            w = float(s['weight'])
            if h_m > 0:
                bmi = round(w / (h_m * h_m), 2)
                if bmi < 18.5: bmi_text = "ผอมเกินไป"
                elif bmi < 23.0: bmi_text = "ปกติ / สมส่วน"
                elif bmi < 25.0: bmi_text = "ท้วม / เริ่มอ้วน"
                elif bmi < 30.0: bmi_text = "อ้วนระดับ 1"
                else: bmi_text = "อ้วนระดับ 2"
        except (ValueError, TypeError):
            pass

    return render_template('student_profile.html', s=s, bmi=bmi, bmi_text=bmi_text, history=history)

@app.route('/student/update', methods=['POST'])
def update_student():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    fullname = request.form.get('fullname')
    grade = request.form.get('grade')
    phone = request.form.get('phone')
    address = request.form.get('address')
    height_raw = request.form.get('height')
    weight_raw = request.form.get('weight')

    height = float(height_raw) if height_raw and height_raw.strip() else None
    weight = float(weight_raw) if weight_raw and weight_raw.strip() else None
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    img_filename = None
    if 'profile_img' in request.files:
        file = request.files['profile_img']
        if file and file.filename != '' and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            img_filename = f"{session.get('student_id')}_{int(datetime.now().timestamp())}.{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], img_filename))

    conn = get_db()
    c = conn.cursor()

    if img_filename:
        c.execute('''
            UPDATE students 
            SET fullname=?, grade=?, phone=?, address=?, height=?, weight=?, profile_img=?, status='รอตรวจสอบ', updated_at=?
            WHERE student_id=?
        ''', (fullname, grade, phone, address, height, weight, img_filename, now_str, session.get('student_id')))
    else:
        c.execute('''
            UPDATE students 
            SET fullname=?, grade=?, phone=?, address=?, height=?, weight=?, status='รอตรวจสอบ', updated_at=?
            WHERE student_id=?
        ''', (fullname, grade, phone, address, height, weight, now_str, session.get('student_id')))

    if height or weight:
        c.execute("INSERT INTO height_weight_history (student_id, height, weight, recorded_at) VALUES (?, ?, ?, ?)",
                  (session.get('student_id'), height, weight, now_str))

    conn.commit()
    conn.close()

    flash('บันทึกข้อมูลเรียบร้อยแล้ว!', 'success')
    return redirect(url_for('student_profile'))

@app.route('/student/card')
def student_card():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM students WHERE student_id = ?", (session.get('student_id'),))
    s = c.fetchone()
    conn.close()

    current_host = request.host_url.rstrip('/')
    verify_url = f"{current_host}/verify/{s['student_id']}" if s else ""

    return render_template('student_card.html', s=s, verify_url=verify_url)

@app.route('/verify/<student_id>')
def verify_student(student_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT student_id, fullname, grade, status FROM students WHERE student_id = ?", (student_id,))
    s = c.fetchone()
    conn.close()
    return render_template('verify.html', s=s)

@app.route('/teacher')
def teacher_dashboard():
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM students ORDER BY id DESC")
    students = c.fetchall()
    conn.close()

    return render_template('teacher_dashboard.html', students=students)

@app.route('/teacher/status/<student_id>', methods=['POST'])
def update_status(student_id):
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))

    status = request.form.get('status')
    note = request.form.get('note', '')

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE students SET status = ?, note = ? WHERE student_id = ?", (status, note, student_id))
    conn.commit()
    conn.close()

    flash(f'อัปเดตสถานะนักเรียนรหัส {student_id} เรียบร้อยแล้ว', 'success')
    return redirect(url_for('teacher_dashboard'))

@app.route('/teacher/delete/<student_id>', methods=['POST'])
def delete_student(student_id):
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))

    conn = get_db()
    c = conn.cursor()
    
    # 1. ดึงข้อมูลรูปภาพเพื่อไปลบไฟล์ออกจากเครื่อง
    c.execute("SELECT profile_img FROM students WHERE student_id = ?", (student_id,))
    s = c.fetchone()
    if s and s['profile_img']:
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], s['profile_img'])
        if os.path.exists(img_path):
            os.remove(img_path)

    # 2. ลบข้อมูลจากตาราง students และประวัติการบันทึก (ถ้ามี)
    c.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    c.execute("DELETE FROM height_weight_history WHERE student_id = ?", (student_id,))
    
    conn.commit()
    conn.close()

    flash(f'ลบข้อมูลนักเรียนรหัส {student_id} เรียบร้อยแล้ว', 'info')
    return redirect(url_for('teacher_dashboard'))
    
if __name__ == '__main__':
    app.run(debug=True)
            
