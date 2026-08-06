@app.route('/student')
def student_profile():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    c.execute("SELECT * FROM students WHERE student_id = ?", (session.get('student_id'),))
    s = c.fetchone()

    # หากไม่พบข้อมูลนักเรียนในตาราง ให้ส่งกลับไปหน้า Login
    if not s:
        conn.close()
        session.clear()
        flash('ไม่พบข้อมูลบัญชีนักเรียน กรุณาเข้าสู่ระบบใหม่', 'error')
        return redirect(url_for('login'))

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
    if len(s) > 8 and s[7] and s[8]:
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
    
