from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS students 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  student_id TEXT UNIQUE NOT NULL, 
                  fullname TEXT NOT NULL, 
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

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
    student_id = request.form['student_id'].strip()
    fullname = request.form['fullname'].strip()
    if student_id and fullname:
        conn = sqlite3.connect('students.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO students (student_id, fullname) VALUES (?, ?)", (student_id, fullname))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        conn.close()
    return redirect(url_for('index'))

@app.route('/api/students')
def get_students_api():
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    c.execute("SELECT student_id, fullname, created_at FROM students ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    return jsonify([{"student_id": r[0], "fullname": r[1], "created_at": r[2]} for r in rows])

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
