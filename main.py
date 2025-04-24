import sqlite3, random
from flask import Flask, request, render_template, redirect, url_for, session, flash

app = Flask('app')
app.secret_key = "secret"

def get_db_connection():
    conn = sqlite3.connect('myDatabase.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def welcome():
    if 'uid' in session:
        role = session.get('role')
        return redirect_to_dashboard(role)
    return render_template('welcome.html')

def redirect_to_dashboard(role):
    if role == 'student':
        return redirect(url_for('stu_dashboard'))
    elif role == 'Admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'Faculty':
        return redirect(url_for('instructor_dashboard'))
    elif role == 'GS':
        return redirect(url_for('grad_secretary_dashboard'))
    elif role == 'Alumni':
        return redirect(url_for('alumni_dashboard'))
    else:
        flash("Unknown role type.")
        return redirect(url_for('logout'))

@app.route('/stu_dashboard')
def stu_dashboard():
    if 'uid' not in session:
        flash('Please login to access the stu_dashboard')
        return redirect(url_for('login'))
    return render_template('stu_dashboard.html', role=session['role'])

def generate_unique_uid():
    conn = sqlite3.connect('myDatabase.db')
    cursor = conn.cursor()
    existing_uids = {row[0] for row in cursor.execute("SELECT UID FROM user").fetchall()}
    conn.close()

    while True:
        uid = random.randint(10000000, 99999999)
        if uid not in existing_uids:
            return uid


@app.route('/grad_secretary_dashboard')
def grad_secretary_dashboard():
    if 'uid' not in session or session['role'] != 'GS':
        flash("Access denied.")
        return redirect(url_for('login'))
    return render_template('gs_dashboard.html')

@app.route('/alumni_dashboard')
def alumni_dashboard():
    if 'uid' not in session or session['role'] != 'Alumni':
        flash("Access denied.")
        return redirect(url_for('login'))
    return render_template('alumni_dashboard.html')

@app.route('/transcript')
def view_transcript():
    if 'uid' not in session or session['role'] not in ['student', 'Alumni']:
        flash('Please log in as a student or alumni to view transcripts.', 'error')
        return redirect(url_for('login'))

    student_id = session['uid']
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
    SELECT c.course_num, c.title, c.credits, 
        t.semester, t.year, t.section, 
        t.grade, t.graded 
    FROM transcript t 
    JOIN course c ON t.course_id = c.course_id 
    WHERE t.student_uid = ?
    ORDER BY t.year, 
            CASE t.semester 
                WHEN 'Spring' THEN 1 
                WHEN 'Summer' THEN 2 
                WHEN 'Fall' THEN 3 
                ELSE 4 
            END
    '''

    transcript = cursor.execute(query, (student_id,)).fetchall()
    GPA = calculate_gpa(transcript)
    conn.close()

    return render_template('transcript.html', transcript=transcript, GPA=GPA, student_id=student_id)

  
@app.route('/catalog', methods=['GET', 'POST'])
def catalog():
    conn = get_db_connection()

    departments = conn.execute('SELECT DISTINCT dept FROM course ORDER BY dept').fetchall()

    selected_dept = ''
    search_term = ''
    query = '''
        SELECT c.course_id, c.dept, c.course_num, c.title, c.credits,
               p1.dept AS prereq1_dept, p1.course_num AS prereq1_num,
               p2.dept AS prereq2_dept, p2.course_num AS prereq2_num
        FROM course c
        LEFT JOIN course_prerequisite cp1 ON c.course_id = cp1.course_id
        LEFT JOIN course p1 ON cp1.prereq_id = p1.course_id
        LEFT JOIN course_prerequisite cp2 ON c.course_id = cp2.course_id AND cp2.prereq_id != cp1.prereq_id
        LEFT JOIN course p2 ON cp2.prereq_id = p2.course_id
    '''
    filters = []
    params = []

    if request.method == 'POST':
        selected_dept = request.form.get('department', '')
        search_term = request.form.get('search', '')

        if selected_dept:
            filters.append('c.dept = ?')
            params.append(selected_dept)
        if search_term:
            filters.append('(c.title LIKE ? OR c.course_num LIKE ?)')
            params.extend(['%' + search_term + '%'] * 2)

    if filters:
        query += ' WHERE ' + ' AND '.join(filters)

    query += ' GROUP BY c.course_id ORDER BY c.course_num'

    courses = conn.execute(query, params).fetchall()
    conn.close()

    catalog_data = {}
    for course in courses:
        dept = course['dept']
        if dept not in catalog_data:
            catalog_data[dept] = []
        prereq1 = f"{course['prereq1_dept']} {course['prereq1_num']}" if course['prereq1_dept'] else "None"
        prereq2 = f"{course['prereq2_dept']} {course['prereq2_num']}" if course['prereq2_dept'] else "None"
        catalog_data[dept].append({
            'number': course['course_num'],
            'title': course['title'],
            'credits': course['credits'],
            'prereq1': prereq1,
            'prereq2': prereq2
        })

    return render_template('catalog.html', catalog=catalog_data, departments=departments, selected_dept=selected_dept, search_term=search_term)



@app.route('/register_course', methods=['GET', 'POST'])
def register_course():
    if 'uid' not in session or session['role'] != 'student':
        flash("Only logged-in students can register.")
        return redirect(url_for('login'))

    student_uid = session['uid']
    conn = sqlite3.connect('myDatabase.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'POST':
        course_id = int(request.form['course_id'])
        section = int(request.form['section'])
        semester = request.form['semester']

        # Fetch schedule first to access year
        cursor.execute('SELECT * FROM schedule WHERE course_id = ? AND section = ? AND semester = ?', 
                       (course_id, section, semester))
        schedule = cursor.fetchone()
        if not schedule:
            flash("Error: course schedule not found.", "error")
            return redirect(url_for('register_course'))

        year = schedule['year']

        # Already registered check 
        cursor.execute('''
            SELECT * FROM transcript 
            WHERE student_uid = ? AND course_id = ? AND section = ? AND semester = ?
        ''', (student_uid, course_id, section, semester))
        if cursor.fetchone():
            flash("Error: Already registered.", "error")
            return redirect(url_for('register_course'))

        # Conflict check 
        cursor.execute('''
            SELECT s.day, s.time_slot
            FROM schedule s
            JOIN transcript t 
              ON s.course_id = t.course_id 
             AND s.section = t.section 
             AND s.semester = t.semester 
             AND s.year = t.year
            WHERE t.student_uid = ? AND t.semester = ? AND t.year = ?
        ''', (student_uid, semester, year))
        for row in cursor.fetchall():
            if row['day'] == schedule['day'] and row['time_slot'] == schedule['time_slot']:
                flash("Error: schedule conflict with another course.", "error")
                return redirect(url_for('register_course'))
        cursor.execute('''
            SELECT prereq_id FROM course_prerequisite WHERE course_id = ?
        ''', (course_id,))
        prereqs = cursor.fetchall()

        for prereq in prereqs:
            prereq_id = prereq['prereq_id']
            cursor.execute('''
                SELECT grade FROM transcript
                WHERE student_uid = ? AND course_id = ? AND graded = TRUE
            ''', (student_uid, prereq_id))
            result = cursor.fetchone()
            if not result or result['grade'] not in ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C']:
                flash("Error: Prerequisite course not satisfied.", "error")
                return redirect(url_for('register_course'))
                
        # Insert registration 
        try:
            cursor.execute('''
                INSERT INTO transcript (student_uid, course_id, section, semester, year, grade, graded)
                VALUES (?, ?, ?, ?, ?, 'IP', FALSE)
            ''', (student_uid, course_id, section, semester, year))
            conn.commit()
            flash("Successfully registered.", "success")
        except sqlite3.IntegrityError as e:
            flash(f"Registration failed: {str(e)}", "error")
        return redirect(url_for('register_course'))

    # Fetch available offerings
    available_courses = cursor.execute('''
        SELECT s.*, c.title, c.course_num, u.firstName || ' ' || u.lastName AS instructor_name
        FROM schedule s
        JOIN course c ON s.course_id = c.course_id
        JOIN faculty i ON s.instructor_id = i.UID
        JOIN user u ON u.UID = i.UID
        WHERE s.year = 2024
        AND NOT EXISTS (
            SELECT 1 FROM transcript t
            WHERE t.student_uid = ? AND t.course_id = s.course_id 
              AND t.section = s.section AND t.semester = s.semester AND t.year = s.year
        )
    ''', (student_uid,)).fetchall()

    # Fetch enrolled courses
    enrolled_courses = cursor.execute('''
        SELECT s.*, c.title, c.course_num, u.firstName || ' ' || u.lastName AS instructor_name, t.graded
        FROM transcript t
        JOIN schedule s 
          ON t.course_id = s.course_id AND t.section = s.section 
         AND t.semester = s.semester AND t.year = s.year
        JOIN course c ON s.course_id = c.course_id
        JOIN faculty i ON s.instructor_id = i.UID
        JOIN user u ON u.UID = i.UID
        WHERE t.student_uid = ?
    ''', (student_uid,)).fetchall()

    conn.close()
    return render_template('register.html', available_courses=available_courses, enrolled_courses=enrolled_courses)

@app.route('/drop_course', methods=['POST'])
def drop_course():
    if 'uid' not in session or session['role'] != 'student':
        flash("Only students can drop courses.")
        return redirect(url_for('login'))

    student_uid = session['uid']
    course_id = request.form['course_id']
    section = request.form['section']
    semester = request.form['semester']

    conn = sqlite3.connect('myDatabase.db')
    cursor = conn.cursor()

    # Only allow drop if grade not yet assigned
    cursor.execute('''
        SELECT * FROM transcript
        WHERE student_uid = ? AND course_id = ? AND section = ? AND semester = ? AND graded = FALSE
    ''', (student_uid, course_id, section, semester))

    if cursor.fetchone():
        cursor.execute('''
            DELETE FROM transcript
            WHERE student_uid = ? AND course_id = ? AND section = ? AND semester = ?
        ''', (student_uid, course_id, section, semester))
        conn.commit()
        flash("Course dropped.", "success")
    else:
        flash("Course could not be dropped.", "error")

    conn.close()
    return redirect(url_for('register_course'))

@app.route('/personal_info', methods=['GET', 'POST'])
def personal_info():
    if 'uid' not in session or session['role'] not in ['student', 'Alumni']:
        flash("Login as a student or alumni to view personal info.")
        return redirect(url_for('login'))

    uid = session['uid']
    role = session['role']
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        new_first = request.form['firstName'].strip().title()
        new_last = request.form['lastName'].strip().title()
        new_email = request.form['email'].strip().lower()
        new_password = request.form['password'].strip()
        new_phone = request.form['phone'].strip()
        new_address = request.form['address'].strip()
        new_address2 = request.form.get('address2', '').strip()
        new_password = request.form['password'].strip()

        cursor.execute('''
            UPDATE user SET firstName = ?, lastName = ?, email = ?, phone = ?, address = ?, address2 = ? WHERE UID = ?
        ''', (new_first, new_last, new_email, new_phone, new_address, new_address2, uid))

        if new_password:
            cursor.execute('UPDATE user SET password = ? WHERE UID = ?', (new_password, uid))

        if role == 'student':
            new_program = request.form['program'].strip().title()
            new_gpa = request.form['GPA'].strip()
            new_thesis_status = request.form['thesis_status'].strip()
            cursor.execute('''
                UPDATE student
                SET program = ?, GPA = ?, thesis_status = ?
                WHERE UID = ?
            ''', (new_program, new_gpa, new_thesis_status, uid))
        conn.commit()
        flash("Profile updated successfully.", "success")
        conn.close()
        return redirect(url_for('personal_info'))

    if role == 'student':
        cursor.execute('''
            SELECT u.UID, u.firstName, u.lastName, u.email, u.phone, u.address, u.address2,
                   s.program, s.GPA, s.thesis_status
            FROM user u
            JOIN student s ON u.UID = s.UID
            WHERE u.UID = ?
        ''', (uid,))
    else:  # alumni
        cursor.execute('''
            SELECT u.UID, u.firstName, u.lastName, u.email, u.phone, u.address, u.address2,
                   a.grad_year, a.degree
            FROM user u
            JOIN alumni a ON u.UID = a.UID
            WHERE u.UID = ?
        ''', (uid,))
    user = cursor.fetchone()
    conn.close()
    return render_template('personal_info.html', user=user, role=role)


@app.route('/course_offerings', methods=['GET'])
def course_offerings():
    if 'uid' not in session or session['role'] != 'student':
        flash("Login as a student to view course offerings.", "error")
        return redirect(url_for('login'))

    # Clean and normalize input
    search = request.args.get('search', '').strip()
    semester = request.args.get('semester', '').strip().capitalize()

    # Validate semester
    valid_semesters = ['Fall', 'Spring', 'Summer']
    if semester and semester not in valid_semesters:
        flash("Invalid semester selected.", "error")
        return redirect(url_for('course_offerings'))

    # Limit length of search input
    if len(search) > 50:
        flash("Search term is too long.", "error")
        return redirect(url_for('course_offerings'))

    # Build query
    conn = get_db_connection()
    cursor = conn.cursor()
    query = '''
        SELECT c.dept, c.course_num, c.title, c.course_id,
               s.section, s.semester, s.year, s.day, s.time_slot,
               u.firstName || ' ' || u.lastName AS instructor_name
        FROM schedule s
        JOIN course c ON s.course_id = c.course_id
        JOIN faculty i ON s.instructor_id = i.UID
        JOIN user u ON i.UID = u.UID
        WHERE s.year = 2024
        AND 1=1
    '''
    filters = []

    if semester:
        query += ' AND s.semester = ?'
        filters.append(semester)

    if search:
        query += '''
            AND (
                LOWER(c.title) LIKE ? OR
                LOWER(c.course_num) LIKE ? OR
                LOWER(u.firstName) LIKE ? OR
                LOWER(u.lastName) LIKE ?
            )
        '''
        search_pattern = f'%{search.lower()}%'
        filters.extend([search_pattern] * 4)

    query += ' ORDER BY s.semester, s.day, s.time_slot'

    offerings = cursor.execute(query, tuple(filters)).fetchall()
    conn.close()

    return render_template(
        'course_offerings.html',
        offerings=offerings,
        search_term=search,
        semester_filter=semester
    )


# Helper function to check if they have admin capabilities
def is_admin():
    return 'uid' in session and session.get('role') == 'Admin'

@app.route('/admin/manage')
def admin_manage():
    if not is_admin():
        flash("Unauthorized access.")
        return redirect(url_for('login'))
    return render_template('admin/manage.html')

@app.route('/gs_dashboard')
def gs_dashboard():
    if 'uid' not in session or session['role'] != 'GS':
        flash("Login as a Grad Secretary to access this page.")
        return redirect(url_for('login'))

    return render_template('gs_dashboard.html')

@app.route('/gs_transcripts', methods=['GET', 'POST'])
def gs_transcripts():
    if 'uid' not in session or session['role'] != 'GS':
        flash("Login as a Grad Secretary to access this page.")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    filters = {
        "student_uid": request.form.get("student_uid", request.args.get("student_uid", "")).strip(),
        "course_num": request.form.get("course_num", request.args.get("course_num", "")).strip(),
        "semester": request.form.get("semester", request.args.get("semester", "")).strip(),
        "year": request.form.get("year", request.args.get("year", "")).strip()
    }


    query = '''
        SELECT t.student_uid, u.firstName, u.lastName,
               c.course_num, c.title, c.credits,
               s.semester, s.year, t.grade, t.graded
        FROM transcript t
        JOIN schedule s ON t.course_id = s.course_id AND t.section = s.section AND t.semester = s.semester
        JOIN course c ON t.course_id = c.course_id
        JOIN student st ON t.student_uid = st.UID
        JOIN user u ON u.UID = st.UID
        WHERE 1=1
    '''
    params = []
    if filters["student_uid"]:
        query += " AND t.student_uid = ?"
        params.append(filters["student_uid"])
    if filters["course_num"]:
        query += " AND c.course_num = ?"
        params.append(filters["course_num"])
    if filters["semester"]:
        query += " AND LOWER(s.semester) = ?"
        params.append(filters["semester"].lower())
    if filters["year"]:
        query += " AND s.year = ?"
        params.append(filters["year"])

    query += " ORDER BY t.student_uid, s.year, s.semester"

    results = cursor.execute(query, params).fetchall()
    GPA = calculate_gpa(results)
    conn.close()

    return render_template("gs_transcripts.html", results=results, filters=filters, GPA=GPA)

@app.route('/gs_students')
def gs_students():
    if 'uid' not in session or session['role'] != 'GS':
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT u.UID, u.firstName, u.lastName, s.program
        FROM user u
        JOIN student s ON u.UID = s.UID
        ORDER BY u.lastName
    ''')
    students = cursor.fetchall()
    conn.close()

    return render_template('gs_students.html', students=students)

@app.route('/update_grade', methods=['POST'])
def update_grade():
    if 'uid' not in session or session['role'] != 'GS':
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    student_uid = request.form['student_uid']
    course_num = request.form['course_num']
    semester = request.form['semester']
    grade = request.form['grade'].upper()

    valid_grades = ['A','A-','B+','B','B-','C+','C','F']
    if grade not in valid_grades:
        flash("Invalid grade submitted.")
        return redirect(url_for('gs_transcripts',
                                student_uid=student_uid,
                                course_num=course_num,
                                semester=semester))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT t.course_id, t.section FROM transcript t
        JOIN course c ON t.course_id = c.course_id
        WHERE t.student_uid = ? AND c.course_num = ? AND t.semester = ?
    ''', (student_uid, course_num, semester))
    result = cursor.fetchone()
    if result:
        course_id, section = result['course_id'], result['section']
        cursor.execute('''
            UPDATE transcript
            SET grade = ?, graded = TRUE
            WHERE student_uid = ? AND course_id = ? AND section = ? AND semester = ?
        ''', (grade, student_uid, course_id, section, semester))
        conn.commit()

    conn.close()
    flash("Grade updated successfully.")
    return redirect(url_for('gs_transcripts', student_uid=student_uid))

@app.route('/instructor_dashboard')
def instructor_dashboard():
    if 'uid' not in session or session['role'] != 'Faculty':
        flash("Login as an instructor to access this page.")
        return redirect(url_for('login'))

    return render_template('instructor_dashboard.html')

@app.route('/instructor_schedule')
def instructor_schedule():
    if 'uid' not in session or session['role'] != 'Faculty':
        flash("Login as an instructor to access this page.")
        return redirect(url_for('login'))

    instructor_id = session['uid']
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
        SELECT c.course_num, c.title, s.semester, s.year, s.day, s.time_slot
        FROM schedule s
        JOIN course c ON s.course_id = c.course_id
        WHERE s.instructor_id = ?
        ORDER BY s.year DESC, s.semester
    '''
    courses = cursor.execute(query, (instructor_id,)).fetchall()
    conn.close()

    return render_template('instructor_schedule.html', courses=courses)

@app.route('/instructor_courses')
def instructor_courses():
    if 'uid' not in session or session['role'] != 'Faculty':
        flash("Login as an instructor to access this page.")
        return redirect(url_for('login'))

    instructor_id = session['uid']
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all courses taught by this instructor
    query = '''
        SELECT s.course_id, c.course_num, c.title, s.section, s.semester, s.year
        FROM schedule s
        JOIN course c ON s.course_id = c.course_id
        WHERE s.instructor_id = ?
        ORDER BY s.year DESC, s.semester
    '''
    courses = cursor.execute(query, (instructor_id,)).fetchall()
    conn.close()

    return render_template('instructor_courses.html', courses=courses)

@app.route('/instructor_roster', methods=['POST'])
def instructor_roster():
    if 'uid' not in session or session['role'] != 'Faculty':
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    course_id = request.form['course_id']
    section = request.form['section']
    semester = request.form['semester']

    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
        SELECT t.student_uid, u.firstName, u.lastName, t.grade, t.graded
        FROM transcript t
        JOIN user u ON t.student_uid = u.UID
        WHERE t.course_id = ? AND t.section = ? AND t.semester = ?
    '''
    students = cursor.execute(query, (course_id, section, semester)).fetchall()

    # Also fetch course details for header
    course_info = cursor.execute('''
        SELECT c.course_num, c.title, s.year
        FROM course c
        JOIN schedule s ON c.course_id = s.course_id
        WHERE c.course_id = ? AND s.section = ? AND s.semester = ?
        LIMIT 1
    ''', (course_id, section, semester)).fetchone()

    conn.close()

    return render_template('instructor_roster.html', students=students, course=course_info,
                           section=section, semester=semester)

@app.route('/instructor_grading', methods=['GET', 'POST'])
def instructor_grading():
    if 'uid' not in session or session['role'] != 'Faculty':
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    instructor_id = session['uid']
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch all courses the instructor teaches
    courses = cursor.execute('''
        SELECT s.course_id, c.course_num, c.title, s.section, s.semester, s.year
        FROM schedule s
        JOIN course c ON s.course_id = c.course_id
        WHERE s.instructor_id = ?
        ORDER BY s.year DESC, s.semester
    ''', (instructor_id,)).fetchall()

    selected_students = []
    selected_course = {}

    if request.method == 'POST' and 'course_info' in request.form:
        course_id, section, semester = request.form['course_info'].split('|')

        selected_students = cursor.execute('''
            SELECT t.student_uid, u.firstName, u.lastName, t.grade, t.graded
            FROM transcript t
            JOIN user u ON t.student_uid = u.UID
            WHERE t.course_id = ? AND t.section = ? AND t.semester = ?
        ''', (course_id, section, semester)).fetchall()

        selected_course = {
            'course_id': course_id,
            'section': section,
            'semester': semester
        }

    conn.close()
    return render_template('instructor_grading.html', 
                           courses=courses,
                           students=selected_students,
                           selected_course=selected_course)

@app.route('/submit_grade', methods=['POST'])
def submit_grade():
    if 'uid' not in session or session['role'] != 'Faculty':
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    student_uid = request.form['student_uid']
    course_id = request.form['course_id']
    section = request.form['section']
    semester = request.form['semester']
    grade = request.form['grade'].upper()

    valid_grades = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'F']

    if grade not in valid_grades:
        flash("Invalid grade.")
        return redirect(url_for('instructor_grading'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE transcript
        SET grade = ?, graded = TRUE
        WHERE student_uid = ? AND course_id = ? AND section = ? AND semester = ? AND graded = FALSE
    ''', (grade, student_uid, course_id, section, semester))
    conn.commit()
    conn.close()

    flash("Grade submitted.")
    return redirect(url_for('instructor_grading'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'uid' not in session or session['role'] != 'Admin':
        flash("Unauthorized access.")
        return redirect(url_for('login'))
    return render_template('admin/dashboard.html')

# Creates a user
@app.route('/admin/create_user', methods=['GET', 'POST'])
def create_user():
    if not is_admin():
        flash("Unauthorized.")
        return redirect(url_for('login'))
    if request.method == 'POST':
        uid = generate_unique_uid()
        firstName = request.form['firstName'].strip().title()
        lastName = request.form['lastName'].strip().title()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        role = request.form['role'].strip()
        ssn = request.form.get('ssn', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        address2 = request.form.get('address2', '').strip()
        # Normalize role-specific values
        program = request.form.get('program', '').strip().title()  # Masters or PhD
        degree = request.form.get('degree', '').strip().upper()    # e.g., BS, MS, PHD
        dept = request.form.get('dept', '').strip().upper()
        office = request.form.get('office', '').strip()
        grad_year = request.form.get('grad_year', '').strip()

        try:
            conn = sqlite3.connect('myDatabase.db')
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO user (UID, firstName, lastName, email, password, role, ssn, phone, address, address2)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, firstName, lastName, email, password, role, ssn, phone, address, address2))

            if role == 'student':
                if program not in ['Masters', 'PhD']:
                    raise ValueError("Program must be 'Masters' or 'PhD'")
                cur.execute("INSERT INTO student (UID, advisor_id, GPA, program, thesis_status) VALUES (?, ?, ?, ?, ?)",
                            (uid, None, None, program, None))

            elif role == 'Faculty':
                cur.execute("INSERT INTO Faculty (UID, dept) VALUES (?, ?)", (uid, dept))

            elif role == 'Admin':
                cur.execute("INSERT INTO admin (UID, access_level) VALUES (?, ?)", (uid, 'full'))

            elif role == 'GS':
                cur.execute("INSERT INTO grad_secretary (UID, office) VALUES (?, ?)", (uid, office))

            elif role == 'Alumni':
                if not grad_year.isdigit():
                    raise ValueError("Graduation year must be numeric")
                cur.execute("INSERT INTO alumni (UID, grad_year, degree) VALUES (?, ?, ?)",
                            (uid, grad_year, degree))

            conn.commit()
            flash(f"User created successfully. Assigned UID: {uid}", "success")

        except (sqlite3.Error, ValueError) as e:
            flash(f"Error: {str(e)}", "error")
            conn.rollback()

        finally:
            conn.close()

        return redirect(url_for('create_user'))

    return render_template('admin/create_user.html')

# Assigns instructor to a course
@app.route('/admin/assign_instructor', methods=['GET', 'POST'])
def assign_instructor():
    if not is_admin():
        flash("Unauthorized.")
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('myDatabase.db')
    conn.row_factory = sqlite3.Row  # <--- important for dict-like access
    cur = conn.cursor()

    if request.method == 'POST':
        course_id = int(request.form['course_id'])
        instructor_id = int(request.form['instructor_id'])
        try:
            # Update instructor for the course
            cur.execute("UPDATE course SET instructor_id = ? WHERE course_id = ?", (instructor_id, course_id))

            # Update instructor for all current/future offerings of that course
            cur.execute("""
                UPDATE schedule
                SET instructor_id = ?
                WHERE course_id = ?
            """, (instructor_id, course_id))

            conn.commit()
            flash("Faculty assigned to course and all offerings.", "success")

        except sqlite3.Error as e:
            flash(f"Error assigning instructor: {e}", "error")
            conn.rollback()

        finally:
            conn.close()

        return redirect(url_for('assign_instructor'))

    instructors = cur.execute("""
        SELECT UID, firstName || ' ' || lastName AS name 
        FROM user 
        WHERE role = 'Faculty'
    """).fetchall()

    courses = cur.execute("""
        SELECT course_id, title 
        FROM course
    """).fetchall()

    conn.close()
    return render_template('admin/assign_instructor.html', instructors=instructors, courses=courses)


# Add course
@app.route('/admin/add_course', methods=['GET', 'POST'])
def add_course():
    if not is_admin():
        flash("Unauthorized.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        course_id = request.form['course_id'].strip()
        dept = request.form['dept'].strip().upper()
        course_num = request.form['course_num'].strip()
        title = request.form['title'].strip().title()
        credits = request.form['credits'].strip()
        instructor_id = request.form['instructor_id'].strip()

        # Basic field presence check
        if not (course_id and dept and course_num and title and credits):
            flash("All fields except instructor must be filled.", "error")
            return redirect(url_for('add_course'))

        # Digit-only checks
        if not course_id.isdigit():
            flash("Course ID must be numeric only.", "error")
            return redirect(url_for('add_course'))

        if not course_num.isdigit():
            flash("Course Number must be numeric only.", "error")
            return redirect(url_for('add_course'))

        if not credits.isdigit():
            flash("Credits must be a valid number.", "error")
            return redirect(url_for('add_course'))

        if instructor_id and not instructor_id.isdigit():
            flash("Faculty ID must be numeric only.", "error")
            return redirect(url_for('add_course'))

        credits = int(credits)

        try:
            conn = sqlite3.connect('myDatabase.db')
            cur = conn.cursor()

            # Validate instructor ID if provided
            if instructor_id:
                cur.execute("SELECT * FROM faculty WHERE UID = ?", (instructor_id,))
                if not cur.fetchone():
                    flash("Faculty ID does not exist.", "error")
                    return redirect(url_for('add_course'))

            # Insert the validated course
            cur.execute("""
                INSERT INTO course (course_id, dept, course_num, title, credits, instructor_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                int(course_id),
                dept,
                int(course_num),
                title,
                credits,
                int(instructor_id) if instructor_id else None
            ))

            conn.commit()
            flash("Course added successfully.", "success")

        except sqlite3.Error as e:
            flash(f"Database error: {e}", "error")
            conn.rollback()

        finally:
            conn.close()

        return redirect(url_for('add_course'))

    return render_template('admin/add_course.html')

# Add schedule offering
@app.route('/admin/add_schedule', methods=['GET', 'POST'])
def add_schedule():
    if not is_admin():
        flash("Unauthorized.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        course_id = request.form['course_id'].strip()
        semester = request.form['semester'].strip().capitalize()
        section = request.form['section'].strip()
        year = request.form['year'].strip()
        day = request.form['day'].strip()
        time_slot = request.form['time_slot'].strip()
        instructor_id = request.form['instructor_id'].strip()

        # Validate numeric fields
        if not course_id.isdigit():
            flash("Course ID must be numeric.", "error")
            return redirect(url_for('add_schedule'))
        course_id = int(course_id)

        if not year.isdigit() or len(year) != 4:
            flash("Year must be a 4-digit number.", "error")
            return redirect(url_for('add_schedule'))

        if not instructor_id.isdigit():
            flash("Faculty ID must be numeric.", "error")
            return redirect(url_for('add_schedule'))

        try:
            conn = sqlite3.connect('myDatabase.db')
            cur = conn.cursor()

            course_id = int(course_id)
            # Optional: check if course and instructor exist
            cur.execute("SELECT 1 FROM course WHERE course_id = ?", (course_id,))
            if not cur.fetchone():
                flash("Course ID does not exist.", "error")
                return redirect(url_for('add_schedule'))

            cur.execute("SELECT 1 FROM faculty WHERE UID = ?", (instructor_id,))
            if not cur.fetchone():
                flash("Faculty ID does not exist.", "error")
                return redirect(url_for('add_schedule'))

            cur.execute("""
                INSERT INTO schedule (course_id, semester, section, year, day, time_slot, instructor_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                int(course_id),
                semester,
                section,
                int(year),
                day,
                time_slot,
                int(instructor_id)
            ))

            conn.commit()
            flash("schedule added successfully.", "success")

        except sqlite3.Error as e:
            flash(f"Database error: {e}", "error")
            conn.rollback()

        finally:
            conn.close()

        return redirect(url_for('add_schedule'))

    return render_template('admin/add_schedule.html')

# Add prerequisite for course
@app.route('/admin/add_prerequisite', methods=['GET', 'POST'])
def add_prerequisite():
    if not is_admin():
        flash("Unauthorized.")
        return redirect(url_for('login'))

    conn = sqlite3.connect('myDatabase.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Fetch course list for dropdown
    courses = cur.execute("SELECT course_id, course_num, title FROM course").fetchall()

    if request.method == 'POST':
        course_id = request.form['course_id'].strip()
        prereq_id = request.form['prereq_id'].strip()

        # Validate that both are numeric
        if not course_id.isdigit() or not prereq_id.isdigit():
            flash("Both Course and Prerequisite must be valid numeric selections.", "error")
            conn.close()
            return redirect(url_for('add_prerequisite'))

        # Prevent course from being its own prerequisite
        if course_id == prereq_id:
            flash("A course cannot be a prerequisite of itself.", "error")
            conn.close()
            return redirect(url_for('add_prerequisite'))

        try:
            cur.execute("INSERT INTO course_prerequisite (course_id, prereq_id) VALUES (?, ?)",
                        (int(course_id), int(prereq_id)))
            conn.commit()
            flash("Prerequisite added successfully.", "success")
        except sqlite3.Error as e:
            flash(f"Database error: {e}", "error")
            conn.rollback()
        finally:
            conn.close()

        return redirect(url_for('add_prerequisite'))

    conn.close()
    return render_template('admin/add_prerequisite.html', courses=courses)


# Shows all records
@app.route('/admin/view/<table>')
def view_table(table):
    if not is_admin():
        flash("Unauthorized.")
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        user_tables = ['student', 'faculty', 'alumni', 'admin', 'grad_secretary']
        if table in user_tables:
            query = f'''
                SELECT r.*, u.firstName || ' ' || u.lastName AS full_name, u.email, u.role
                FROM {table} r
                JOIN user u ON r.UID = u.UID
            '''
            cursor.execute(query)

        elif table == 'course':
            query = '''
                SELECT c.*, u.firstName || ' ' || u.lastName AS instructor_name
                FROM course c
                LEFT JOIN faculty i ON c.instructor_id = i.UID
                LEFT JOIN user u ON i.UID = u.UID
            '''
            cursor.execute(query)
        elif table == 'schedule':
            query = '''
                SELECT s.*, c.title AS course_title, u.firstName || ' ' || u.lastName AS instructor_name
                FROM schedule s
                LEFT JOIN course c ON s.course_id = c.course_id
                LEFT JOIN faculty i ON s.instructor_id = i.UID
                LEFT JOIN user u ON i.UID = u.UID
            '''
            cursor.execute(query)
        elif table == 'transcript':
            query = '''
                SELECT t.*, c.title AS course_title,
                u.firstName || ' ' || u.lastName AS student_name
                FROM transcript t
                LEFT JOIN course c ON t.course_id = c.course_id
                LEFT JOIN student s ON t.student_uid = s.UID
                LEFT JOIN user u ON s.UID = u.UID
            '''
            cursor.execute(query)
        else:
            cursor.execute(f"SELECT * FROM {table}")

        data = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        if 'full_name' in columns:
            columns.insert(0, columns.pop(columns.index('full_name')))

    except sqlite3.Error as e:
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('admin_dashboard'))
    finally:
        conn.close()

    pk_column = columns[0]  # Assuming first column is primary key
    return render_template('admin/view_table.html', table=table, columns=columns, data=data, pk_column=pk_column)

def get_role_specific_columns(table):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    columns = [col['name'] for col in cur.fetchall()]
    conn.close()
    return columns

# Edits records
@app.route('/admin/edit/<table>/<id>', methods=['GET', 'POST'])
def edit_record(table, id):
    if not is_admin():
        flash("Unauthorized.")
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    user_related_tables = ['student', 'faculty', 'admin', 'grad_secretary', 'alumni']

    if table in user_related_tables:
        role_cols = get_role_specific_columns(table)
        role_select = ", ".join([f"r.{col}" for col in role_cols])
        cur.execute(f'''
            SELECT u.UID, u.firstName, u.lastName, u.email, u.password, u.role, {role_select}
            FROM user u
            JOIN {table} r ON u.UID = r.UID
            WHERE u.UID = ?
        ''', (int(id),))
        record = cur.fetchone()

        if not record:
            flash("Record is not found.", "error")
            return redirect(url_for('view_table', table=table))

        user_columns = ['UID', 'firstName', 'lastName', 'email', 'password', 'role']
        role_columns = [col for col in role_cols if col != 'UID']

        if request.method == 'POST':
            # Update u
            cur.execute('''
                UPDATE user SET firstName = ?, lastName = ?, email = ?, password = ?, role = ?
                WHERE UID = ?
            ''', (
                request.form['firstName'].strip().title(),
                request.form['lastName'].strip().title(),
                request.form['email'].strip().lower(),
                request.form['password'],
                request.form['role'],
                id
            ))

            # Update Role
            updates = []
            values = []
            for col in role_columns:
                updates.append(f"{col} = ?")
                values.append(request.form.get(col))
            values.append(id)

            cur.execute(f'''
                UPDATE {table}
                SET {', '.join(updates)}
                WHERE UID = ?
            ''', values)

            conn.commit()
            flash("Record updated successfully.", "success")
            return redirect(url_for('view_table', table=table))

        return render_template('admin/edit_record.html',
                               table=table,
                               record=record,
                               user_columns=user_columns,
                               role_columns=role_columns)

    else:
        cur.execute(f"PRAGMA table_info({table})")
        columns_info = cur.fetchall()
        pk_column = columns_info[0]['name']

        cur.execute(f"SELECT * FROM {table} WHERE {pk_column} = ?", (id,))
        record = cur.fetchone()

        if not record:
            flash("Record not found.", "error")
            return redirect(url_for('view_table', table=table))

        columns = record.keys()

        if request.method == 'POST':
            updates = []
            values = []
            for col in columns[1:]:  
                updates.append(f"{col} = ?")
                values.append(request.form[col])
            values.append(id)

            cur.execute(f"UPDATE {table} SET {', '.join(updates)} WHERE {pk_column} = ?", values)
            conn.commit()
            flash("Record updated successfully.", "success")
            return redirect(url_for('view_table', table=table))

        return render_template('admin/edit_record.html', table=table, columns=columns, record=record)

# Re-defining the GPA calculation function after code state reset.

def calculate_gpa(transcript_rows):
    # Grade point mapping
    grade_points = {
        'A': 4.0,
        'A-': 3.7,
        'B+': 3.3,
        'B': 3.0,
        'B-': 2.7,
        'C+': 2.3,
        'C': 2.0,
        'F': 0.0
    }

    total_points = 0
    total_credits = 0

    for row in transcript_rows:
        grade = row['grade']
        credits = row['credits']
        if grade in grade_points:
            total_points += grade_points[grade] * credits
            total_credits += credits

    if total_credits == 0:
        return 0.0  

    GPA = total_points / total_credits
    return round(GPA, 2)

app.run(host='0.0.0.0', port=8080, debug=True)