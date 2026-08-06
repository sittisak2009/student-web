import os
import sqlite3
import io
import csv
import math
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, Response, flash

app = Flask(__name__)
app.secret_key = 'darkwick_secret_key_1234'

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
    
    # ตารางนักเรียน
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
    
    # ตารางประวัติน้ำหนักส่วนสูง
    c.execute('''
        CREATE TABLE IF NOT EXISTS height_weight_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            height REAL,
            weight REAL,
            recorded_at TEXT
        )
    ''')
    
    # ตรวจสอบและอัปเดตโครงสร้างคอลัมน์อัตโนมัติ
    c.execute("PRAGMA table_info(students)")
    cols = [col[1] for col in c.fetchall()]
    if 'height' not in cols: c.execute("ALTER TABLE students ADD COLUMN height REAL")
    if 'weight' not in cols: c.execute("ALTER TABLE students ADD COLUMN weight REAL")
    if 'profile_img' not in cols: c.execute("ALTER TABLE students ADD COLUMN profile_img TEXT")
    if 'status' not in cols: c.execute("ALTER TABLE students ADD COLUMN status TEXT DEFAULT 'รอตรวจสอบ'")
    if 'note' not in cols: c.execute("ALTER TABLE students ADD COLUMN note TEXT")
    if 'updated_at' not in cols: c.execute("ALTER TABLE students ADD COLUMN updated_at TEXT")
    
    conn.commit()
    conn.close()

init_db()

# ---- Auth Routes ----
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role')
        username = request.form.get('username')
        password = request.form.get('password')
        
        if role == 'teacher':
            if username == TEACHER_USER and password == TEACHER_PASS:
                session['role'] = 'teacher'
                session['user'] = username
                flash('ยินดีต้อนรับเข้าสู่ระบบครูประจำชั้น', 'success')
                return redirect(url_for('teacher_dashboard'))
            else:
                flash('ชื่อผู้ใช้หรือรหัสผ่านครูไม่ถูกต้อง!', 'error')
        elif role == 'student':
            conn = sqlite3.connect('students.db')
            c = conn.cursor()
            c.execute("SELECT * FROM students WHERE student_id = ? AND password = ?", (username, password))
            student = c.fetchone()
            conn.close()
            if student:
                session['role'] = 'student'
                session['student_id'] = student[1]
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
        try:
            conn = sqlite3.connect('students.db')
            c = conn.cursor()
            c.execute("INSERT INTO students (student_id, password, fullname, updated_at) VALUES (?, ?, ?, ?)",
                      (student_id, password, fullname, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            flash('ลงทะเบียนสำเร็จ! กรุณาเข้าสู่ระบบ', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('รหัสนักเรียนนี้มีในระบบแล้ว!', 'error')
    return render_template('register.html')

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if not session.get('role'):
        return redirect(url_for('login'))
        
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
                flash('เปลี่ยนรหัสผ่านเรียบร้อยแล้ว!', 'success')
            else:
                flash('รหัสผ่านเดิมไม่ถูกต้อง!', 'error')
            conn.close()
            
    return render_template('change_password.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('ออกจากระบบเรียบร้อยแล้ว', 'info')
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

    # ดึงประวัติส่วนสูงน้ำหนักอย่างปลอดภัย
    history = []
    try:
        c.execute("SELECT height, weight, recorded_at FROM height_weight_history WHERE student_id = ? ORDER BY id DESC LIMIT 5", (session.get('student_id'),))
        history = c.fetchall()
    except Exception:
        pass
    conn.close()
    
    # คำนวณ BMI
    bmi, bmi_text = None, "-"
    if s and s[7] and s[8]:
        try:
            h_m = float(s[7]) / 100
            w = float(s[8])
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
            try:
                ext = file.filename.rsplit('.', 1)[1].lower()
                img_filename = f"{session.get('student_id')}_{int(datetime.now().timestamp())}.{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], img_filename))
            except Exception:
                img_filename = None

    conn = sqlite3.connect('students.db')
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

    # บันทึกลงตารางประวัติอย่างปลอดภัย
    try:
        if height or weight:
            c.execute("INSERT INTO height_weight_history (student_id, height, weight, recorded_at) VALUES (?, ?, ?, ?)",
                      (session.get('student_id'), height, weight, now_str))
    except Exception:
        pass

    conn.commit()
    conn.close()
    flash('บันทึกข้อมูลเรียบร้อยแล้ว!', 'success')
    return redirect(url_for('student_profile'))

@app.route('/student/card')
def student_card():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    c.execute("SELECT * FROM students WHERE student_id = ?", (session.get('student_id'),))
    s = c.fetchone()
    conn.close()
    return render_template('student_card.html', s=s)

# ---- Teacher Dashboard Routes ----
@app.route('/')
@app.route('/teacher')
def teacher_dashboard():
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))

    search = request.args.get('search', '')
    selected_grade = request.args.get('grade', '')
    page = int(request.args.get('page', 1))
    per_page = 10

    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    
    query = "FROM students WHERE 1=1"
    params = []
    
    if search:
        query += " AND (student_id LIKE ? OR fullname LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])
    if selected_grade:
        query += " AND grade = ?"
        params.append(selected_grade)

    c.execute(f"SELECT COUNT(*) {query}", params)
    total_count = c.fetchone()[0]
    total_pages = math.ceil(total_count / per_page) or 1

    offset = (page - 1) * per_page
    c.execute(f"SELECT * {query} ORDER BY id DESC LIMIT ? OFFSET ?", params + [per_page, offset])
    students = c.fetchall()

    c.execute("SELECT DISTINCT grade FROM students WHERE grade IS NOT NULL AND grade != ''")
    grades = [row[0] for row in c.fetchall()]

    c.execute("SELECT status, COUNT(*) FROM students GROUP BY status")
    status_counts = dict(c.fetchall())

    conn.close()
    return render_template('teacher_dashboard.html', students=students, grades=grades, 
                           selected_grade=selected_grade, search=search, status_counts=status_counts,
                           page=page, total_pages=total_pages)

@app.route('/teacher/update_status/<int:id>', methods=['POST'])
def update_status(id):
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))
        
    new_status = request.form.get('status')
    note = request.form.get('note', '')
    
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    c.execute("UPDATE students SET status = ?, note = ? WHERE id = ?", (new_status, note, id))
    conn.commit()
    conn.close()
    flash('อัปเดตสถานะและหมายเหตุสำเร็จ', 'success')
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
    flash('ลบข้อมูลเรียบร้อยแล้ว', 'info')
    return redirect(url_for('teacher_dashboard'))

@app.route('/export')
def export_csv():
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    c.execute("SELECT student_id, fullname, grade, phone, height, weight, status, note, updated_at FROM students ORDER BY id DESC")
    students = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student ID', 'Full Name', 'Grade', 'Phone', 'Height (cm)', 'Weight (kg)', 'Status', 'Note', 'Updated At'])
    writer.writerows(students)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-disposition": "attachment; filename=students_data.csv"})

if __name__ == '__main__':
    app.run(debug=True)
                
