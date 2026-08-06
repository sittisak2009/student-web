import os
import sqlite3
import io
import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, Response
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'darkwick_secret_key_1234'

# ตั้งค่าที่เก็บรูปโปรไฟล์นักเรียน
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TEACHER_USER = "admin"
TEACHER_PASS = "1234"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect('students.db')
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
            updated_at TEXT
        )
    ''')
    # เพิ่มคอลัมน์ให้อัตโนมัติหากมีตารางเดิมอยู่แล้ว
    c.execute("PRAGMA table_info(students)")
    cols = [col[1] for col in c.fetchall()]
    if 'height' not in cols: c.execute("ALTER TABLE students ADD COLUMN height REAL")
    if 'weight' not in cols: c.execute("ALTER TABLE students ADD COLUMN weight REAL")
    if 'profile_img' not in cols: c.execute("ALTER TABLE students ADD COLUMN profile_img TEXT")
    if 'status' not in cols: c.execute("ALTER TABLE students ADD COLUMN status TEXT DEFAULT 'รอตรวจสอบ'")
    conn.commit()
    conn.close()

init_db()

# ---- Authentication Routes ----
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        role = request.form.get('role')
        username = request.form.get('username')
        password = request.form.get('password')
        
        if role == 'teacher':
            if username == TEACHER_USER and password == TEACHER_PASS:
                session['role'] = 'teacher'
                session['user'] = username
                return redirect(url_for('teacher_dashboard'))
            else:
                error = 'ชื่อผู้ใช้หรือรหัสผ่านครูไม่ถูกต้อง!'
        elif role == 'student':
            conn = sqlite3.connect('students.db')
            c = conn.cursor()
            c.execute("SELECT * FROM students WHERE student_id = ? AND password = ?", (username, password))
            student = c.fetchone()
            conn.close()
            if student:
                session['role'] = 'student'
                session['student_id'] = student[1]
                return redirect(url_for('student_profile'))
            else:
                error = 'รหัสนักเรียนหรือรหัสผ่านไม่ถูกต้อง!'
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        password = request.form.get('password')
        fullname = request.form.get('fullname')
        try:
            conn = sqlite3.connect('students.db')
            c = conn.cursor()
            c.execute("INSERT INTO students (student_id, password, fullname, updated_at) VALUES (?, ?, ?, ?)",
                      (student_id, password, fullname, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            error = "รหัสนักเรียนนี้มีในระบบแล้ว!"
    return render_template('register.html', error=error)

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if not session.get('role'):
        return redirect(url_for('login'))
        
    msg, error = None, None
    if request.method == 'POST':
        old_pass = request.form.get('old_pass')
        new_pass = request.form.get('new_pass')
        
        if session.get('role') == 'student':
            conn = sqlite3.connect('students.db')
            c = conn.cursor()
            c.execute("SELECT password FROM students WHERE student_id = ?", (session.get('student_id'),))
            curr = c.fetchone()
            if curr and curr[0] == old_pass:
                c.execute("UPDATE students SET password = ? WHERE student_id = ?", (new_pass, session.get('student_id')))
                conn.commit()
                msg = "เปลี่ยนรหัสผ่านเรียบร้อยแล้ว!"
            else:
                error = "รหัสผ่านเดิมไม่ถูกต้อง!"
            conn.close()
            
    return render_template('change_password.html', msg=msg, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---- Student Routes ----
@app.route('/student')
def student_profile():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    c.execute("SELECT * FROM students WHERE student_id = ?", (session.get('student_id'),))
    s = c.fetchone()
    conn.close()
    
    # คำนวณ BMI
    bmi, bmi_text = None, "-"
    if s and s[7] and s[8]: # height, weight
        h_m = s[7] / 100
        bmi = round(s[8] / (h_m * h_m), 2)
        if bmi < 18.5: bmi_text = "ผอมเกินไป"
        elif bmi < 23.0: bmi_text = "น้ำหนักปกติ / สมส่วน"
        elif bmi < 25.0: bmi_text = "ท้วม / เริ่มอ้วน"
        elif bmi < 30.0: bmi_text = "อ้วนระดับ 1"
        else: bmi_text = "อ้วนระดับ 2"

    return render_template('student_profile.html', s=s, bmi=bmi, bmi_text=bmi_text)

@app.route('/student/update', methods=['POST'])
def update_student():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
        
    fullname = request.form.get('fullname')
    grade = request.form.get('grade')
    phone = request.form.get('phone')
    address = request.form.get('address')
    height = request.form.get('height') or None
    weight = request.form.get('weight') or None
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # จัดการอัปโหลดรูปภาพ
    img_filename = None
    if 'profile_img' in request.files:
        file = request.files['profile_img']
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            img_filename = f"{session.get('student_id')}_{int(datetime.now().timestamp())}.{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], img_filename))

    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    
    if img_filename:
        c.execute('''
            UPDATE students 
            SET fullname=?, grade=?, phone=?, address=?, height=?, weight=?, profile_img=?, status='รอตรวจสอบ', updated_at=?
            WHERE student_id=?
        ''', (fullname, grade, phone, address, height, weight, img_filename, updated_at, session.get('student_id')))
    else:
        c.execute('''
            UPDATE students 
            SET fullname=?, grade=?, phone=?, address=?, height=?, weight=?, status='รอตรวจสอบ', updated_at=?
            WHERE student_id=?
        ''', (fullname, grade, phone, address, height, weight, updated_at, session.get('student_id')))
        
    conn.commit()
    conn.close()
    return redirect(url_for('student_profile'))

# ---- Teacher Dashboard Routes ----
@app.route('/')
@app.route('/teacher')
def teacher_dashboard():
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))

    search = request.args.get('search', '')
    selected_grade = request.args.get('grade', '')

    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    
    # Query กรองตามห้องเรียนและคำค้นหา
    query = "SELECT * FROM students WHERE 1=1"
    params = []
    
    if search:
        query += " AND (student_id LIKE ? OR fullname LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])
    if selected_grade:
        query += " AND grade = ?"
        params.append(selected_grade)
        
    query += " ORDER BY id DESC"
    c.execute(query, params)
    students = c.fetchall()

    # ดึงรายชื่อห้องเรียนทั้งหมดมาใส่ Dropdown
    c.execute("SELECT DISTINCT grade FROM students WHERE grade IS NOT NULL AND grade != ''")
    grades = [row[0] for row in c.fetchall()]

    # นับสถิติสำหรับสร้างกราฟ Analytics
    c.execute("SELECT status, COUNT(*) FROM students GROUP BY status")
    status_counts = dict(c.fetchall())

    conn.close()
    return render_template('teacher_dashboard.html', students=students, grades=grades, 
                           selected_grade=selected_grade, search=search, status_counts=status_counts)

@app.route('/teacher/update_status/<int:id>', methods=['POST'])
def update_status(id):
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))
        
    new_status = request.form.get('status')
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    c.execute("UPDATE students SET status = ? WHERE id = ?", (new_status, id))
    conn.commit()
    conn.close()
    return redirect(url_for('teacher_dashboard'))

@app.route('/delete/<int:id>')
def delete_student(id):
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    c.execute("DELETE FROM students WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('teacher_dashboard'))

@app.route('/export')
def export_csv():
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    c.execute("SELECT student_id, fullname, grade, phone, height, weight, status, updated_at FROM students ORDER BY id DESC")
    students = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student ID', 'Full Name', 'Grade', 'Phone', 'Height (cm)', 'Weight (kg)', 'Status', 'Updated At'])
    writer.writerows(students)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=students_data.csv"})

if __name__ == '__main__':
    app.run(debug=True)
        
