from flask import Flask, render_template, request, redirect, url_for, Response
import sqlite3
from datetime import datetime
import io
import csv

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

init_db()

@app.route('/')
def index():
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
    
    return render_template('index.html', students=students, total=total_students, search=search_query)

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

@app.route('/delete/<int:id>')
def delete_student(id):
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    c.execute("DELETE FROM students WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/export')
def export_csv():
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    c.execute("SELECT student_id, fullname, created_at FROM students ORDER BY id DESC")
    students = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student ID', 'Full Name', 'Created At'])
    writer.writerows(students)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=students_list.csv"}
    )

if __name__ == '__main__':
    app.run(debug=True)
