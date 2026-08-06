@app.route('/student/update', methods=['POST'])
def update_student():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
        
    fullname = request.form.get('fullname')
    grade = request.form.get('grade')
    phone = request.form.get('phone')
    address = request.form.get('address')
    
    # แปลงค่าน้ำหนัก ส่วนสูง ป้องกันการส่งค่าว่าง
    height_raw = request.form.get('height')
    weight_raw = request.form.get('weight')
    
    height = float(height_raw) if height_raw and height_raw.strip() else None
    weight = float(weight_raw) if weight_raw and weight_raw.strip() else None
    
    updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # จัดการอัปโหลดรูปภาพพร้อมป้องกันการล่มเมื่อเซิร์ฟเวอร์เขียนไฟล์ไม่ได้
    img_filename = None
    if 'profile_img' in request.files:
        file = request.files['profile_img']
        if file and file.filename != '' and allowed_file(file.filename):
            try:
                ext = file.filename.rsplit('.', 1)[1].lower()
                img_filename = f"{session.get('student_id')}_{int(datetime.now().timestamp())}.{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], img_filename))
            except Exception as e:
                print(f"File upload error: {e}")
                img_filename = None

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
    
