from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_change_this'  # ใช้สำหรับเข้ารหัส Session ความปลอดภัย

# ฐานข้อมูลจำลองในหน่วยความจำ (สามารถเปลี่ยนไปใช้ฐานข้อมูลจริงภายหลังได้)
users_db = []

@app.route('/')
def index():
    """หน้าแรกของเว็บไซต์"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """ระบบเข้าสู่ระบบ"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # ค้นหาผู้ใช้งานจากระบบจำลอง
        user = next((u for u in users_db if u['username'] == username), None)
        
        if user and check_password_hash(user['password'], password):
            session['user'] = username
            session['role'] = user.get('role', 'student')
            
            # แยกหน้าตามสิทธิ์ผู้ใช้งาน
            if session['role'] == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            return redirect(url_for('student_profile'))
        else:
            flash('ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง', 'error')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """ระบบลงทะเบียนนักเรียนใหม่"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'student') # กำหนดสิทธิ์เริ่มต้นเป็นนักเรียน
        
        # ตรวจสอบว่ามีชื่อผู้ใช้นี้อยู่แล้วหรือไม่
        if any(u['username'] == username for u in users_db):
            flash('ชื่อผู้ใช้งานนี้ถูกใช้งานแล้ว', 'error')
            return redirect(url_for('register'))
            
        # เข้ารหัสรหัสผ่านก่อนเก็บ
        hashed_password = generate_password_hash(password)
        users_db.append({
            'username': username, 
            'password': hashed_password, 
            'role': role
        })
        
        flash('ลงทะเบียนสำเร็จ กรุณาเข้าสู่ระบบ', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/profile')
def student_profile():
    """หน้าโปรไฟล์นักเรียน"""
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('student_profile.html', username=session['user'])

@app.route('/teacher')
def teacher_dashboard():
    """หน้าแดชบอร์ดสำหรับอาจารย์"""
    if 'user' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    return render_template('teacher_dashboard.html', username=session['user'])

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """ระบบเปลี่ยนรหัสผ่าน"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        
        user = next((u for u in users_db if u['username'] == session['user']), None)
        
        if user and check_password_hash(user['password'], current_password):
            user['password'] = generate_password_hash(new_password)
            flash('เปลี่ยนรหัสผ่านสำเร็จ', 'success')
            return redirect(url_for('student_profile'))
        else:
            flash('รหัสผ่านเดิมไม่ถูกต้อง', 'error')
            
    return render_template('change_password.html')

@app.route('/logout')
def logout():
    """ออกจากระบบ"""
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
