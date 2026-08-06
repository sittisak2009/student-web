from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            fullname TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# สร้างตารางฐานข้อมูลทันทีเมื่อแอปเริ่มทำงาน
init_db()

@app.route('/')
def index():
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    c.execute("SELECT * FROM students ORDER BY id DESC")
    students = c.fetchall()
    conn.close()
    return render_template('index.html', students=students)

@app.route('/add', methods=['POST'])
def add_student():
    student_id = request.form.get('student_id')
    fullname = request.form.get('fullname')
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if student_id and fullname:
        conn = sqlite3.connect('students.db')
        c = conn.cursor()
        c.execute("INSERT INTO students (student_id, fullname, created_at) VALUES (?, ?, ?)",
                  (student_id, fullname, created_at))
        conn.commit()
        conn.close()
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
  
