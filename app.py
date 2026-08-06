from flask import Flask, render_template, request, redirect, url_for, session, Response
import sqlite3
from datetime import datetime
import io
import csv

app = Flask(__name__)
app.secret_key = 'darkwick_secret_key_1234'

TEACHER_USER = "admin"
TEACHER_PASS = "1234"

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
            updated_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ---- หน้าเลือกล็อกอิน / ล็อกอินครู-นักเรียน ----
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
                error = 'รหัสนักเรียนหรือรหัสผ่านไม่ถูกต้อง! (หรือยังไม่ได้ลงทะเบียน)'
                
    return render_template('login.html', error=error)

# สมัครบัญชีนักเรียนใหม่
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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---- ฝั่งนักเรียน: หน้ากรอก/อัปเดตข้อมูลส่วนตัว ----
@app.route('/student')
def student_profile():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    c.execute("SELECT * FROM students WHERE student_id = ?", (session.get('student_id'),))
    student = c.fetchone()
    conn.close()
    
    return render_template('student_profile.html', student=student)

@app.route('/student/update', methods=['POST'])
def update_student():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
        
    fullname = request.form.get('fullname')
    grade = request.form.get('grade')
    phone = request.form.get('phone')
    address = request.form.get('address')
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    c.execute('''
        UPDATE students 
        SET fullname = ?, grade = ?, phone = ?, address = ?, updated_at = ?
        WHERE student_id = ?
    ''', (fullname, grade, phone, address, updated_at, session.get('student_id')))
    conn.commit()
    conn.close()
    
    return redirect(url_for('student_profile'))

# ---- ฝั่งครู: แดชบอร์ดดูข้อมูลทั้งหมด ----
@app.route('/')
@app.route('/teacher')
def teacher_dashboard():
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))

    search_query = request.args.get('search', '')
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    
    if search_query:
        c.execute("SELECT * FROM students WHERE student_id LIKE ? OR fullname LIKE ? ORDER BY id DESC", 
                  (f'%{search_query}%', f'%{search_query}%'))
    else:
        c.execute("SELECT * FROM students ORDER BY id DESC")
        
    students = c.fetchall()
    total_students = len(students)
    conn.close()
    
    return render_template('teacher_dashboard.html', students=students, total=total_students, search=search_query)

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
    c.execute("SELECT student_id, fullname, grade, phone, address, updated_at FROM students ORDER BY id DESC")
    students = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student ID', 'Full Name', 'Grade', 'Phone', 'Address', 'Updated At'])
    writer.writerows(students)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=students_list.csv"}
    )

if __name__ == '__main__':
    app.run(debug=True)
  
