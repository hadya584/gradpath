import sqlite3, random, uuid
from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask import Flask, render_template, request, session, redirect, url_for, flash
from datetime import datetime
app = Flask('app')
app.secret_key = "BLOPRH"
app.debug = True

def get_db_connection():
    conn = sqlite3.connect('myDatabase.db')
    conn.row_factory = sqlite3.Row
    return conn

def redirect_to_dashboard(role):
    if role == 'Student':
        return redirect(url_for('stu_dashboard'))
    elif role == 'Admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'Faculty':
        return redirect(url_for('instructor_dashboard'))
    elif role == 'GS':
        return redirect(url_for('grad_secretary_dashboard'))
    elif role == 'Alumni':
        return redirect(url_for('alumni_dashboard'))
    elif role == 'Applicant':
        return redirect(url_for('applicantHome'))
    else:
        flash("Unknown role type.", 'error')
        return redirect(url_for('logout'))

@app.route('/stu_dashboard')
def stu_dashboard():
    if 'UID' not in session:
        flash('Please login to access the stu_dashboard', 'error')
        return redirect(url_for('login'))
    
    UID = session['UID']

    connection = sqlite3.connect('myDatabase.db')
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    # check if they have advising hold
    cursor.execute("SELECT advising_hold, program FROM student WHERE UID = ?", (UID,))
    student = cursor.fetchone()
    advisinghold = student['advising_hold']
    program = student['program']

    # check if suspended
    suspended = False
    if count_low_grades(UID) >= 3:
      suspended = True

    return render_template('stu_dashboard.html', role=session['role'], advisinghold = advisinghold, suspended = suspended, program = program)

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
    if 'UID' not in session or session['role'] != 'GS':
        flash("Access denied.", 'error')
        return redirect(url_for('login'))
    return render_template('gs_dashboard.html')

@app.route('/alumni_dashboard')
def alumni_dashboard():
    if 'UID' not in session or session['role'] != 'Alumni':
        flash("Access denied.", 'error')
        return redirect(url_for('login'))
    return render_template('alumni_dashboard.html')

@app.route('/transcript')
def view_transcript():
    if 'UID' not in session or session['role'] not in ['Student', 'Alumni']:
        flash('Please log in as a Student or alumni to view transcripts.', 'error')
        return redirect(url_for('login'))

    student_id = session['UID']
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
    GPA = calculategpa(transcript)
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
    if 'UID' not in session or session['role'] != 'Student':
        flash("Only logged-in Students can register.")
        return redirect(url_for('login'))

    student_uid = session['UID']
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
    if 'UID' not in session or session['role'] != 'Student':
        flash("Only Students can drop courses.")
        return redirect(url_for('login'))

    student_uid = session['UID']
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
    if 'UID' not in session or session['role'] not in ['Student', 'Alumni', 'GS', 'Faculty', 'Admin']:
        flash("Login to view personal info.")
        return redirect(url_for('login'))

    uid = session['UID']
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

        cursor.execute('''
            UPDATE user SET firstName = ?, lastName = ?, email = ?, phone = ?, address = ?, address2 = ? WHERE UID = ?
        ''', (new_first, new_last, new_email, new_phone, new_address, new_address2, uid))

        if new_password:
            cursor.execute('UPDATE user SET password = ? WHERE UID = ?', (new_password, uid))

        if role == 'Student':
            new_program = request.form['program'].strip().title()
            new_gpa = request.form['GPA'].strip()
            new_thesis_status = request.form['thesis_status'].strip()
            cursor.execute('''
                UPDATE student
                SET program = ?, GPA = ?, thesis_status = ?
                WHERE UID = ?
            ''', (new_program, new_gpa, new_thesis_status, uid))

        elif role == 'GS':
            new_office = request.form['office'].strip()
            cursor.execute('''
                UPDATE grad_secretary
                SET office = ?
                WHERE UID = ?
            ''', (new_office, uid))

        elif role == 'Faculty':
            new_dept = request.form['dept'].strip()
            cursor.execute('''
                UPDATE faculty
                SET dept = ?
                WHERE UID = ?
            ''', (new_dept, uid))

        elif role == 'Admin':
            new_access = request.form['access_level'].strip()
            cursor.execute('''
                UPDATE admin
                SET access_level = ?
                WHERE UID = ?
            ''', (new_access, uid))

        conn.commit()
        flash("Profile updated successfully.", "success")
        conn.close()
        return redirect(url_for('personal_info'))

    # GET: Fetch user info for pre-filling form
    if role == 'Student':
        cursor.execute('''
            SELECT u.UID, u.firstName, u.lastName, u.email, u.phone, u.address, u.address2,
                   s.program, s.GPA, s.thesis_status
            FROM user u
            JOIN student s ON u.UID = s.UID
            WHERE u.UID = ?
        ''', (uid,))
    elif role == 'Alumni':
        cursor.execute('''
            SELECT u.UID, u.firstName, u.lastName, u.email, u.phone, u.address, u.address2,
                   a.grad_year, a.degree
            FROM user u
            JOIN alumni a ON u.UID = a.UID
            WHERE u.UID = ?
        ''', (uid,))
    elif role == 'GS':
        cursor.execute('''
            SELECT u.UID, u.firstName, u.lastName, u.email, u.phone, u.address, u.address2,
                   g.office
            FROM user u
            JOIN grad_secretary g ON u.UID = g.UID
            WHERE u.UID = ?
        ''', (uid,))
    elif role == 'Faculty':
        cursor.execute('''
            SELECT u.UID, u.firstName, u.lastName, u.email, u.phone, u.address, u.address2,
                   f.dept
            FROM user u
            JOIN faculty f ON u.UID = f.UID
            WHERE u.UID = ?
        ''', (uid,))
    elif role == 'Admin':
        cursor.execute('''
            SELECT u.UID, u.firstName, u.lastName, u.email, u.phone, u.address, u.address2,
                   a.access_level
            FROM user u
            JOIN admin a ON u.UID = a.UID
            WHERE u.UID = ?
        ''', (uid,))
        
    user = cursor.fetchone()
    conn.close()
    return render_template('personal_info.html', user=user, role=role)



@app.route('/course_offerings', methods=['GET'])
def course_offerings():
    if 'UID' not in session or session['role'] != 'Student':
        flash("Login as a Student to view course offerings.", "error")
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
    return 'UID' in session and session.get('role') == 'Admin'

@app.route('/admin/manage')
def admin_manage():
    if not is_admin():
        flash("Unauthorized access.")
        return redirect(url_for('login'))
    return render_template('admin/manage.html')

@app.route('/gs_dashboard')
def gs_dashboard():
    if 'UID' not in session or session['role'] != 'GS':
        flash("Login as a Grad Secretary to access this page.", 'error')
        return redirect(url_for('login'))

    return render_template('gs_dashboard.html')

@app.route('/gs_transcripts', methods=['GET', 'POST'])
def gs_transcripts():
    if 'UID' not in session or session['role'] not in ['GS', 'Admin']:
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
    GPA = calculategpa(results)
    conn.close()

    return render_template("gs_transcripts.html", results=results, filters=filters, GPA=GPA)

@app.route('/gs_students')
def gs_students():
    if 'UID' not in session or session['role'] != 'GS':
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
    if 'UID' not in session or session['role'] != 'GS':
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
    if 'UID' not in session or session['role'] != 'Faculty':
        flash("Login as an instructor to access this page.", 'error')
        return redirect(url_for('login'))

    return render_template('instructor_dashboard.html')

@app.route('/instructor_schedule')
def instructor_schedule():
    if 'UID' not in session or session['role'] != 'Faculty':
        flash("Login as an instructor to access this page.")
        return redirect(url_for('login'))

    instructor_id = session['UID']
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
    if 'UID' not in session or session['role'] != 'Faculty':
        flash("Login as an instructor to access this page.")
        return redirect(url_for('login'))

    instructor_id = session['UID']
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
    if 'UID' not in session or session['role'] != 'Faculty':
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
    if 'UID' not in session or session['role'] != 'Faculty':
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    instructor_id = session['UID']
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
    if 'UID' not in session or session['role'] != 'Faculty':
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
    if 'UID' not in session or session['role'] != 'Admin':
        flash("Unauthorized access.", 'error')
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
        raw_role = request.form['role'].strip()
        role_map = {
            'admin': 'Admin',
            'student': 'Student',
            'faculty': 'Faculty',
            'gs': 'GS',
            'grad secretary': 'GS',
            'alumni': 'Alumni',
            'applicant': 'Applicant',
            'cac': 'CAC'
        }

        role = role_map.get(raw_role.lower())
        if role is None:
            raise ValueError(f"Unsupported role selected: {raw_role}")

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

            if role == 'Student':
                if program not in ['Masters', 'PhD']:
                    raise ValueError("Program must be 'Masters' or 'PhD'")
                cur.execute("INSERT INTO student (UID, advisor_id, GPA, program, thesis_status) VALUES (?, ?, ?, ?, ?)",
                            (uid, None, None, program, None))

            elif role == 'Faculty':
                cur.execute("INSERT INTO Faculty (UID, dept) VALUES (?, ?)", (uid, dept))

            elif role == 'Admin':
                pass

            elif role == 'GS':
                cur.execute("INSERT INTO grad_secretary (UID, office) VALUES (?, ?)", (uid, office))

            elif role == 'Alumni':
                degree = request.form.get('degree', '').strip().upper()
                grad_year = request.form.get('grad_year', '').strip()
                if not grad_year.isdigit():
                    raise ValueError("Graduation year must be numeric")
                cur.execute("INSERT INTO alumni (UID, grad_year, degree) VALUES (?, ?, ?)",
                            (uid, grad_year, degree))
            elif role == 'Applicant':
                pass
            elif role == 'CAC':
                pass
            else:
                raise ValueError("Unsupported role selected.")
            conn.commit()
            flash(f"User created successfully. Assigned UID: {uid}", "success")

        except (sqlite3.Error, ValueError) as e:
            flash(f"Error: {str(e)} Role trying to insert: {role}", "error")
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
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        if table in ['student', 'faculty', 'admin', 'grad_secretary', 'alumni']:
            query = f'''
                SELECT r.*, u.firstName || ' ' || u.lastName AS full_name, u.email, u.role
                FROM {table} r
                JOIN user u ON r.UID = u.UID
            '''
        elif table == 'course':
            query = '''
                SELECT c.*, u.firstName || ' ' || u.lastName AS instructor_name
                FROM course c
                LEFT JOIN faculty f ON c.instructor_id = f.UID
                LEFT JOIN user u ON f.UID = u.UID
            '''
        elif table == 'schedule':
            query = '''
                SELECT s.*, c.title AS course_title, u.firstName || ' ' || u.lastName AS instructor_name
                FROM schedule s
                LEFT JOIN course c ON s.course_id = c.course_id
                LEFT JOIN faculty f ON s.instructor_id = f.UID
                LEFT JOIN user u ON f.UID = u.UID
            '''
        elif table == 'transcript':
            query = '''
                SELECT t.*, c.title AS course_title, u.firstName || ' ' || u.lastName AS student_name
                FROM transcript t
                LEFT JOIN course c ON t.course_id = c.course_id
                LEFT JOIN student s ON t.student_uid = s.UID
                LEFT JOIN user u ON s.UID = u.UID
            '''
        else:
            query = f"SELECT * FROM {table}"

        cursor.execute(query)
        data = cursor.fetchall()
        columns = [description[0] for description in cursor.description]

        if 'full_name' in columns:
            columns.insert(0, columns.pop(columns.index('full_name')))
    except sqlite3.Error as e:
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('admin_dashboard'))
    finally:
        conn.close()

    print(f"Columns: {columns}")
    print(f"First row: {data[0] if data else 'No rows'}")

    return render_template('admin/view_table.html', table=table, columns=columns, data=data)



def get_role_specific_columns(table):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    columns = [col['name'] for col in cur.fetchall()]
    conn.close()
    return columns

# Edits records
@app.route('/admin/edit/<table>/<path:ids>', methods=['GET', 'POST'])
def edit_record(table, ids):
    if not is_admin():
        flash("Unauthorized.")
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    id_list = ids.split(',')

    user_related_tables = ['student', 'faculty', 'admin', 'grad_secretary', 'alumni']

    if table in user_related_tables:
        # Handle user + role-specific table
        role_cols = get_role_specific_columns(table)
        role_select = ", ".join([f"r.{col}" for col in role_cols if col != 'UID'])  # no duplicate UID
        cur.execute(f'''
            SELECT u.UID, u.firstName, u.lastName, u.email, u.password, u.role, {role_select}
            FROM user u
            JOIN {table} r ON u.UID = r.UID
            WHERE u.UID = ?
        ''', (int(id_list[0]),))
        record = cur.fetchone()

        if not record:
            flash("Record not found.", "error")
            return redirect(url_for('view_table', table=table))

        if request.method == 'POST':
            # Update USER table first
            user_update_fields = ['firstName', 'lastName', 'email', 'password', 'role']
            user_update_values = [
                request.form['firstName'].strip().title(),
                request.form['lastName'].strip().title(),
                request.form['email'].strip().lower(),
                request.form['password'],
                request.form['role']
            ]
            user_update_values.append(id_list[0])

            cur.execute(f'''
                UPDATE user
                SET firstName = ?, lastName = ?, email = ?, password = ?, role = ?
                WHERE UID = ?
            ''', user_update_values)

            # Update ROLE-SPECIFIC table now
            updates = []
            values = []
            for col in role_cols:
                if col != 'UID':  # UID should not be editable
                    updates.append(f"{col} = ?")
                    values.append(request.form.get(col))  # from form input

            values.append(id_list[0])

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
                               columns=record.keys())
    elif table == 'course':
      cur.execute('SELECT * FROM course WHERE course_id = ?', (int(id_list[0]),))
      record = cur.fetchone()

      if not record:
          flash("Course not found.", "error")
          return redirect(url_for('view_table', table='course'))

      if request.method == 'POST':
          updates = []
          values = []
          for col in record.keys():
              if col != 'course_id':  # don't allow editing primary key
                  updates.append(f"{col} = ?")
                  values.append(request.form.get(col))
          values.append(id_list[0])

          cur.execute(f'''
              UPDATE course
              SET {', '.join(updates)}
              WHERE course_id = ?
          ''', values)

          conn.commit()
          flash("Course updated successfully.", "success")
          return redirect(url_for('view_table', table='course'))

      return render_template('admin/edit_record.html', table=table, record=record, columns=record.keys())

    elif table == 'schedule':
        # Composite key
        cur.execute('''
            SELECT * FROM schedule
            WHERE course_id = ? AND section = ? AND semester = ? AND year = ?
        ''', tuple(id_list))
        record = cur.fetchone()

        if not record:
            flash("Record not found.", "error")
            return redirect(url_for('view_table', table=table))

        if request.method == 'POST':
            updates = ['day = ?', 'time_slot = ?', 'instructor_id = ?']
            values = [
                request.form['day'],
                request.form['time_slot'],
                request.form['instructor_id']
            ]
            values.extend(id_list)

            cur.execute(f'''
                UPDATE schedule
                SET {', '.join(updates)}
                WHERE course_id = ? AND section = ? AND semester = ? AND year = ?
            ''', values)

            conn.commit()
            flash("Schedule updated successfully.", "success")
            return redirect(url_for('view_table', table='schedule'))

        return render_template('admin/edit_record.html', table=table, record=record, columns=record.keys())

    elif table == 'transcript':
        cur.execute('''
            SELECT * FROM transcript
            WHERE student_uid = ? AND course_id = ? AND section = ? AND semester = ? AND year = ?
        ''', tuple(id_list))
        record = cur.fetchone()

        if not record:
            flash("Record not found.", "error")
            return redirect(url_for('view_table', table=table))

        if request.method == 'POST':
            updates = ['grade = ?', 'graded = ?']
            values = [
                request.form['grade'],
                request.form['graded']
            ]
            values.extend(id_list)

            cur.execute(f'''
                UPDATE transcript
                SET {', '.join(updates)}
                WHERE student_uid = ? AND course_id = ? AND section = ? AND semester = ? AND year = ?
            ''', values)

            conn.commit()
            flash("Transcript updated successfully.", "success")
            return redirect(url_for('view_table', table='transcript'))

        return render_template('admin/edit_record.html', table=table, record=record, columns=record.keys())

    else:
        flash("Unsupported table.", "error")
        return redirect(url_for('admin_dashboard'))



# Re-defining the GPA calculation function after code state reset.

def calculategpa(transcript_rows):
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


""" Applicant ROUTES """

# Defines the home page for applicants
@app.route('/applicantHome', methods=['GET', 'POST'])
def applicantHome():
  # Stores role in session
  role = session.get('role')
  if not role:
    flash("You must be logged in to access this page", "error")
    return redirect('/')
  
  # Redirects to appropriate home page based on role if not applicant
  if role != 'Applicant':
    return redirect_to_dashboard(role)

  # session stuff and action and error 
  UID = session.get('UID')
  if not UID:
    flash("Session expired. Please log in again.", "error")
    return redirect('/')
  
  # Error handling
  error = ''
  action = request.form.get('action')
  
  try:
    # Connection Stuff
    connection = sqlite3.connect("myDatabase.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()  

    # Gets all academic info
    cursor.execute('SELECT * FROM academicInformation WHERE UID = ?', (UID,))
    pastInfo = cursor.fetchone()

    # Gets all pers info and saves as var
    cursor.execute('SELECT * FROM user WHERE UID = ?', (UID,))
    applicant_results = cursor.fetchall()

    if not applicant_results:
      flash("Applicant information not found. Please complete your profile.", "error")
      return redirect('/')
    
    # Gets pers info
    persInfo = applicant_results[0]

    # Gets all prior degrees
    cursor.execute('SELECT * FROM priorDegree WHERE UID = ?', (UID,))
    priors = cursor.fetchall()

    # Gets application if it exists
    cursor.execute('SELECT * FROM application WHERE UID = ?', (UID,))
    app = cursor.fetchone()

    # get recommendation letters
    cursor.execute('SELECT * FROM recommendationLetter WHERE UID = ?', (UID,))
    recLets = cursor.fetchall()

    # Initialize prior degrees
    MS = None
    BABS = None

    # If there is both ms and ba/bs
    if len(priors) == 2:
      cursor.execute('SELECT * FROM priorDegree WHERE UID = ? AND degreeName = ?', (UID, 'MS',))
      MS = cursor.fetchone()
      cursor.execute('SELECT * FROM priorDegree WHERE UID = ? AND degreeName IN (?, ?)', (UID, 'BS', 'BA',))
      BABS = cursor.fetchone()

    # if theres only 1 prior it must be bs/ba
    elif len(priors) == 1:
      # sets bs/ba
      cursor.execute('SELECT * FROM priorDegree WHERE UID = ? AND degreeName IN (?, ?)', (UID, 'BS', 'BA',))
      BABS = cursor.fetchone()
    
    # Sets priors as a tuple
    priors = (MS, BABS)

    if request.method == 'POST':

      # Academic Stuff
      degree = request.form.get('degree')
      GRE_Verbal = request.form.get('greVerbal')
      GRE_Quant = request.form.get('greQuant')
      GRE_Year = request.form.get('greYear')
      GRE_Advanced = request.form.get('greAdScore')
      GRE_Subject = request.form.get('greAdSubject')
      TOEFL_Score = request.form.get('toeflScore')
      TOEFL_Date = request.form.get('toeflDate')
      Interests = request.form.get('aoi')
      priorWorkExp = request.form.get('workExp')
      priorUni1 = request.form.get('priorUni1')
      priorMajor1 = request.form.get('priorMajor1')
      priorGPA1 = request.form.get('priorGPA1')
      priorYear1 = request.form.get('priorYear1')
      degreeType2 = request.form.get('degreeType2')
      priorUni2 = request.form.get('priorUni2')
      priorMajor2 = request.form.get('priorMajor2')
      priorGPA2 = request.form.get('priorGPA2')
      priorYear2 = request.form.get('priorYear2')
      # Personal Stuff
      fName = request.form.get('firstName')
      lName = request.form.get('lastName')
      SSN = request.form.get('SSN')
      email = request.form.get('email')
      pNumber = request.form.get('pNumber')
      addr1 = request.form.get('addr1')
      addr2 = request.form.get('addr2')
      AppYear = request.form.get('yearPicker')
      AppSem = request.form.get('semesterPicker')

      # Validation
      validation_errors = []
      
      # Validate GRE scores and TOEFL scores are numbers
      if GRE_Verbal and not GRE_Verbal.isdigit():
        validation_errors.append("GRE Verbal score must be a number")
      if GRE_Quant and not GRE_Quant.isdigit():
        validation_errors.append("GRE Quantitative score must be a number")
      if GRE_Advanced and not GRE_Advanced.isdigit():
        validation_errors.append("GRE Advanced score must be a number")
      if TOEFL_Score and not TOEFL_Score.isdigit():
        validation_errors.append("TOEFL score must be a number")
      
      # Validate GRE scores are in valid range (130-170 for verbal and quant)
      if GRE_Verbal and GRE_Verbal.isdigit() and (int(GRE_Verbal) < 130 or int(GRE_Verbal) > 170):
        validation_errors.append("GRE Verbal score must be between 130 and 170")
      if GRE_Quant and GRE_Quant.isdigit() and (int(GRE_Quant) < 130 or int(GRE_Quant) > 170):
        validation_errors.append("GRE Quantitative score must be between 130 and 170")
      
      # Validate GPA is a float between 0.0 and 4.0
      if priorGPA1:
        try:
          gpa1 = float(priorGPA1)
          if gpa1 < 0.0 or gpa1 > 4.0:
            validation_errors.append("GPA must be between 0.0 and 4.0")
        except ValueError:
          validation_errors.append("GPA must be a number")
          
      if priorGPA2:
        try:
          gpa2 = float(priorGPA2)
          if gpa2 < 0.0 or gpa2 > 4.0:
            validation_errors.append("GPA must be between 0.0 and 4.0")
        except ValueError:
          validation_errors.append("GPA must be a number")
      
      # Validate email format
      import re
      if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        validation_errors.append("Invalid email format")
      
      # Validate SSN format (XXX-XX-XXXX)
      if SSN and not re.match(r"^\d{3}-\d{2}-\d{4}$", SSN):
        validation_errors.append("SSN must be in format XXX-XX-XXXX")
      
      # Validate phone number format (XXX-XXX-XXXX)
      if pNumber and not re.match(r"^\d{3}-\d{3}-\d{4}$", pNumber):
        validation_errors.append("Phone number must be in format XXX-XXX-XXXX")
      
      # If validation errors occurred, display them
      if validation_errors:
        error = "Validation errors: " + ", ".join(validation_errors)
      else:
        # Check if MS is all empty or filled, no partially filled table
        MSWhole = 1 if (priorUni1 and priorMajor1 and priorGPA1 and priorYear1) or (not priorUni1 and not priorMajor1 and not priorGPA1 and not priorYear1) else 0

        # If every field is filled out = 1 else = 0
        AllFilled = 1 if degree and GRE_Verbal and GRE_Quant and GRE_Year and GRE_Advanced and GRE_Subject and TOEFL_Score and TOEFL_Date and degreeType2 and priorUni2 and priorMajor2 and priorGPA2 and priorYear2 and Interests and priorWorkExp and fName and lName and  SSN and email and pNumber and addr1 and UID else 0
        AllFilled_forapp = 1 if degree and GRE_Verbal and GRE_Quant and GRE_Year and GRE_Advanced and GRE_Subject and TOEFL_Score and TOEFL_Date and degreeType2 and priorUni2 and priorMajor2 and priorGPA2 and priorYear2 and Interests and priorWorkExp and fName and lName and  SSN and email and pNumber and addr1 and UID and AppYear and AppSem else 0

        if action == 'submit' or 'apply':

          # If not all required fields are filled
          if not AllFilled:
            error = 'Please Fill In All Required Fields'

          # If the masters degree is only partially filled out
          if not MSWhole:
            error = 'The MS Degree cannot be partially filled out'
         
          # If either of the above are true
          if not error:

            # No previous prior MS, and MS was input
            if not MS and priorUni1:
              cursor.execute('INSERT INTO priorDegree (UID, degreeName, institution, major, GPA, year) VALUES (?, ?, ?, ?, ?, ?)', (UID, 'MS', priorUni1, priorMajor1, priorGPA1, priorYear1))

            # It was already in db so we update
            if MS and priorUni1:
              cursor.execute('UPDATE priorDegree set institution = ?, major = ?, GPA = ?, year = ? WHERE UID = ? AND degreeName = ?', (priorUni1, priorMajor1, priorGPA1, priorYear1, UID, 'MS'))

            # If there was no BABS before
            if not BABS:
              cursor.execute('INSERT INTO priorDegree (UID, degreeName, institution, major, GPA, year) VALUES (?, ?, ?, ?, ?, ?)', (UID, degreeType2, priorUni2, priorMajor2, priorGPA2, priorYear2))

            # If there was BABS before
            if BABS:
              cursor.execute('UPDATE priorDegree set institution = ?, major = ?, GPA = ?, year = ?, degreeName = ? WHERE UID = ? AND degreeName IN (?, ?)', (priorUni2, priorMajor2, priorGPA2, priorYear2, degreeType2, UID, 'BS', 'BA'))

            # If there was already a academicInfo table made
            if pastInfo:
              cursor.execute('UPDATE academicInformation set degree = ?, GRE_Verbal = ?, GRE_Quant = ?, GRE_Year = ?, GRE_Advanced = ?, GRE_Subject = ?, TOEFL_Score = ?, TOEFL_Date = ?, AreasOfInterest = ?, priorWorkExp = ?, applySemester = ?, applyYear = ? WHERE UID = ?',(degree, GRE_Verbal, GRE_Quant, GRE_Year, GRE_Advanced, GRE_Subject, TOEFL_Score, TOEFL_Date, Interests, priorWorkExp, AppSem, AppYear, UID))
          
            # If we need to make a new table
            else:
              cursor.execute('INSERT INTO academicInformation (UID, degree, GRE_Verbal, GRE_Quant, GRE_Year, GRE_Advanced, GRE_Subject, TOEFL_Score, TOEFL_Date, areasOfInterest, priorWorkExp, transcripts, applySemester, applyYear) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (UID, degree, GRE_Verbal, GRE_Quant, GRE_Year, GRE_Advanced, GRE_Subject, TOEFL_Score, TOEFL_Date, Interests, priorWorkExp, 1, AppSem, AppYear))

            # Updates personal info if no errors
            cursor.execute('UPDATE user set firstName = ?, lastName = ?, ssn = ?, email = ?, phone = ?, address = ?, address2 = ? WHERE UID = ?', (fName, lName, SSN, email, pNumber, addr1, addr2, UID))
            
            flash("Information saved successfully", "success")

        if action == 'apply':

          if len(recLets) < 3:
            error = 'Must Have Three Recommendation Letters'
          
          if not AllFilled_forapp:
            error = 'Please Fill Out Application Year and Semester'
          # Inserts the application into the db
          if not app and not error:
            cursor.execute('INSERT INTO application (UID, applicationStatus, applySemester, applyYear) VALUES (?, ?, ?, ?)', (UID, 'Complete and Under Review', AppSem, AppYear))
            flash("Application submitted successfully", "success")
      
    # Commit changes if no errors
    connection.commit()
      
    # Gets all pastinfo updated so that it displays the newly saved info if there was some
    cursor.execute('SELECT * FROM academicInformation WHERE UID = ?', (UID,))
    pastInfo = cursor.fetchone()

    # Gets all pers info updated so that it displays the newly saved info if there was some
    cursor.execute('SELECT * FROM user WHERE UID = ?', (UID,))
    persInfo = cursor.fetchall()[0]

    # Gets all prior degrees updated so that it displays the newly saved info if there was some
    cursor.execute('SELECT * FROM priorDegree WHERE UID = ?', (UID,))
    priors = cursor.fetchall()

    # Reset MS and BABS variables
    MS = None
    BABS = None
    
    # If there is both ms and ba/bs
    if len(priors) == 2:
      cursor.execute('SELECT * FROM priorDegree WHERE UID = ? AND degreeName = ?', (UID, 'MS',))
      MS = cursor.fetchone()
      cursor.execute('SELECT * FROM priorDegree WHERE UID = ? AND degreeName IN (?, ?)', (UID, 'BS', 'BA',))
      BABS = cursor.fetchone()
    # If there is only 1 prior it must be bs/ba
    elif len(priors) == 1:
      # Sets bs/ba
      cursor.execute('SELECT * FROM priorDegree WHERE UID = ? AND degreeName IN (?, ?)', (UID, 'BS', 'BA',))
      BABS = cursor.fetchone()
    
    priors = (MS, BABS)

    # Get application if it exists
    cursor.execute('SELECT * FROM application WHERE UID = ?', (UID,))
    app = cursor.fetchone()
    
    # If the user has applied, set condition to 1
    condition = 0
    if app:
      condition = 1
      
    connection.close()
    return render_template('applicantHome.html', error=error, pastInfo=pastInfo, persInfo=persInfo, UID=UID, condition=condition, priors=priors, app=app, recLets=recLets)
    
  except sqlite3.Error as e:
    if 'connection' in locals():
      connection.rollback()
      connection.close()
      
    flash(f"Database error: {str(e)}", "error")
    return redirect('/')
  except Exception as e:
    if 'connection' in locals():
      connection.close()
      
    flash(f"An error occurred: {str(e)}", "error")
    return redirect('/')
  
# Route for applicants to define recommenders
@app.route('/define-recommenders', methods=['GET', 'POST'])
def defineRecommenders():

  if request.method == 'POST':
    connection = sqlite3.connect("myDatabase.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    UID = session.get('UID')

    if not UID:
        flash('User session not found. Please log in again.', 'error')
        connection.close()
        return redirect(url_for('applicantHome'))
    
    # A list of dictionaries, each dictionary contains the name, email, and affiliation of a recommender
    recommenders = []
    # Get recommender 1 (required)
    rec1_name = request.form.get('rec1_name')
    rec1_email = request.form.get('rec1_email')
    rec1_affiliation = request.form.get('rec1_affiliation')
    if rec1_name and rec1_email: # Basic validation
        recommenders.append({'name': rec1_name, 'email': rec1_email, 'affiliation': rec1_affiliation})
    else:
        flash('Recommender 1 Name and Email are required.', 'error')
        connection.close()
        return render_template('defineRecommenders.html') # Stay on page if required info missing

    # Get optional recommenders 2 and 3
    for i in range(2, 4):
        rec_name = request.form.get(f'rec{i}_name')
        rec_email = request.form.get(f'rec{i}_email')
        rec_affiliation = request.form.get(f'rec{i}_affiliation')
        if rec_name and rec_email:
            recommenders.append({'name': rec_name, 'email': rec_email, 'affiliation': rec_affiliation})

    try:
        for rec in recommenders:
            # Generate a unique token for each recommender
            token = uuid.uuid4().hex
            # Insert placeholder, letter and submissionDate are null for now until the recommender submits the letter
            cursor.execute('SELECT * FROM recommendationLetter WHERE UID = ? AND writerEmail = ?', (UID, rec['email'],))
            if not cursor.fetchone():

              cursor.execute("""
                  INSERT INTO recommendationLetter 
                  (UID, writerName, writerEmail, writerAffiliation, token, status)
                  VALUES (?, ?, ?, ?, ?, ?)
              """, (UID, rec['name'], rec['email'], rec['affiliation'], token, 'Pending'))

              # Simulate email sending by flashing the message, follow link to submit recommendation
              submission_url = url_for('submitRecommendation', token=token, _external=True)
              flash(f"Simulated Email Sent To: {rec['email']}\nSubject: Recommendation Request for Applicant {UID}\nMessage: Please submit your recommendation using this link: {submission_url}", 'info')

        connection.commit()
        flash('Recommender information saved. Simulated emails have been sent.', 'success')
        # Redirect to home on success
        return redirect(url_for('applicantHome')) 

    except sqlite3.Error as e:
        connection.rollback()
        flash(f'Database error: {e}', 'error')
    finally:
        connection.close()

    # If we reach here due to an error after the initial check, redisplay the form
    return render_template('defineRecommenders.html', rec_Lets=None )

  # Handle GET request
  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()
  UID = session.get('UID')

  if not UID:
      flash('User session not found. Please log in again.', 'error')
      connection.close()
      return redirect(url_for('login'))
  
  cursor.execute('SELECT * FROM recommendationLetter WHERE UID = ? ORDER BY id', (UID,))
  rec_Lets = cursor.fetchall()


  return render_template('defineRecommenders.html', rec_Lets=rec_Lets)

# Defines a route for faculties to submit a recommendation letter, technically an applicant route since
# faculties never are actually able to get this thru email (it's simulated)
@app.route('/submit-recommendation/<token>', methods=['GET', 'POST'])
def submitRecommendation(token):
    if session.get('role') != 'Applicant':
      flash('Access denied. Applicant privileges required.', 'danger')
      return redirect(url_for('applicantHome'))
    
    connection = sqlite3.connect("myDatabase.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    error = None

    # Fetch the recommendation record by token
    cursor.execute("SELECT * FROM recommendationLetter WHERE token = ? AND status = 'Pending'", (token,))
    recommendation_info = cursor.fetchone()

    if not recommendation_info:
        connection.close()
        # Render the template with an indication that the link is invalid/used
        return render_template('submitRecommendation.html', recommendation_info=None, error="Invalid or already used submission link.")

    if request.method == 'POST':
        letter_text = request.form.get('letter')
        submission_date = datetime.now().strftime("%Y-%m-%d")

        if not letter_text: # Basic validation: Ensure letter text is provided
            error = "Letter text cannot be empty."
        else:
            try:
                # Update only letter, submissionDate, and status
                cursor.execute("""
                    UPDATE recommendationLetter 
                    SET letter = ?, submissionDate = ?, status = ?
                    WHERE token = ?
                """, (letter_text, submission_date, 'Submitted', token))
                connection.commit()
                connection.close()
                # Render a simple success message/page, don't need another page for this
                return "<h1>Recommendation Submitted Successfully!</h1><p>Thank you for submitting the recommendation.</p>" 
            except sqlite3.Error as e:
                connection.rollback()
                error = f"Database error: {e}"
        
        # If validation failed or DB error occurred during POST, re-render the form with error message
        connection.close() # Ensure connection is closed if not closed by success path
        return render_template('submitRecommendation.html', recommendation_info=recommendation_info, error=error)

    # Handle GET request (display the form)
    connection.close()
    return render_template('submitRecommendation.html', recommendation_info=recommendation_info, error=error)

# Route for applicants to sign up
@app.route('/signup', methods=['GET', 'POST'])
def signup():
  error = None
  if request.method == 'POST':
    try:
      connection = sqlite3.connect("myDatabase.db")
      connection.row_factory = sqlite3.Row
      cursor = connection.cursor()
      # Get form data
      firstName = request.form.get('firstName')
      lastName = request.form.get('lastName')
      ssn = request.form.get('ssn')
      email = request.form.get('email')
      phone = request.form.get('phone')
      address = request.form.get('address')
      address2 = request.form.get('address2', '')  # Optional field
      session['email'] = email
      session['role'] = 'Applicant'
      
      # Check if email already exists
      cursor.execute("SELECT * FROM user WHERE email = ?", (email,))
      if cursor.fetchone():
          error = "Email already registered. Please use a different email."
          return render_template('signup.html', error=error)
      
      # Store user details in the session
      session['new_user'] = {
          'firstName': firstName,
          'lastName': lastName,
          'ssn': ssn,
          'email': email,
          'phone': phone,
          'address': address,
          'address2': address2,
      }
          
      # Insert data into database and get the ID of the new user
      # cursor.execute("INSERT INTO user (firstName, lastName, ssn, email, phone, address, address2) VALUES (?, ?, ?, ?, ?, ?, ?)",
      #               (firstName, lastName, ssn, email, phone, address, address2))
      # connection.commit()
      # Redirect to create password page, user isn't fully created until they create a password
      return redirect(url_for('createPassword'))
    except Exception as e:
      connection.rollback()
      error = f"An error occurred: {str(e)}"
      return render_template('signup.html', error=error)
    finally:
      connection.close()
  else:
    return render_template('signup.html')
  
@app.route('/createPassword', methods=['GET', 'POST'])
def createPassword():
  try:
    # Check if user is already logged in (has a UID in session)
    if session.get('UID') and session.get('role') and not request.method == 'POST':
      # User is already authenticated, redirect based on role
      if session['role'] == 'Admin':
        return redirect(url_for('adminDashboard'))
      elif session['role'] in ['Faculty', 'CAC', 'GS']:
        return redirect(url_for('facultyHome'))
      elif session['role'] == 'Applicant':
        return redirect(url_for('applicantHome'))
      else: 
         return redirect(url_for('stu_dashboard'))
        
    # Check if we're in signup flow (should have email but not a fully created account)
    if not session.get('email') and not session.get('new_user') and not request.method == 'POST':
      # Not in signup flow, redirect to login
      return redirect(url_for('login'))
      
    if request.method == 'POST':
      password = request.form.get('password')
      confirm_password = request.form.get('confirm-password')
      
      # Validate password
      if not password:
        error = "Password is required"
        return render_template('createPassword.html', error=error, session=session)
        
      # Validate password strength
      if len(password) < 8:
        error = "Password must be at least 8 characters long"
        return render_template('createPassword.html', error=error, session=session)

      if password != confirm_password:
        # Passwords don't match, re-render the form with an error
        error = "Passwords do not match. Please try again."
        # Need to retain the UID in the session for the template
        return render_template('createPassword.html', error=error, session=session)

      # Ensure we have an email in the session
      if not session.get('email') or not session.get('new_user'):
        error = "Session expired. Please return to signup."
        return render_template('createPassword.html', error=error, session=session)
        
      # Passwords match, proceed with database operations
      connection = sqlite3.connect("myDatabase.db")
      connection.row_factory = sqlite3.Row
      cursor = connection.cursor()
      
      # Check if UID already exists
      cursor.execute("SELECT * FROM user WHERE UID = ?", (session['UID'],))
      if cursor.fetchone():
        error = "User ID already exists. Please try again."
        connection.close()
        return render_template('createPassword.html', error=error, session=session)
      
      try:
        # Insert new user
        new_user = session['new_user']
        cursor.execute(
            'INSERT INTO user (UID, role, password, firstName, lastName, ssn, email, phone, address, address2) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (session['UID'], session['role'], password, new_user['firstName'], new_user['lastName'], new_user['ssn'], new_user['email'], new_user['phone'], new_user['address'], new_user['address2'])
        )        
        
        # # Check if the applicant with this email exists
        # cursor.execute("SELECT * FROM user WHERE email = ?", (session['email'],))
        # if cursor.fetchone():
        #   # Update the existing applicant with the new UID
        #   cursor.execute('UPDATE applicant SET UID = ? WHERE email = ?', (session['UID'], session['email']))
        # else:
        #   error = "Applicant information not found. Please return to signup."
        #   connection.rollback()
        #   connection.close()
        #   return render_template('createPassword.html', error=error, session=session)
          
        connection.commit()
        session.pop('new_user', None)

        flash("Account created successfully. Please log in.", "success")
        return redirect('/')
      except sqlite3.Error as e:
        connection.rollback()
        error = f"Database error: {str(e)}"
        return render_template('createPassword.html', error=error, session=session)
      finally:
        connection.close()
    
    # Generate a random 8-digit UID
    num = random.randrange(0, 10**8)
    num_with_zeros = str(num).zfill(8)
    session['UID'] = num_with_zeros
    
    return render_template('createPassword.html', session=session)
    
  except Exception as e:
    error = f"An error occurred: {str(e)}"
    return render_template('createPassword.html', error=error, session=session)

# Home route, acts as a login page.
@app.route('/', methods=['GET', 'POST'])
def login():
  session.clear()

  # Initialize error variable
  error = None

  # For post routes
  if request.method == 'POST':
    try:
      # Make connection to db
      connection = sqlite3.connect("myDatabase.db")
      connection.row_factory = sqlite3.Row
      
      # Gets elements needed for this page from html
      action = request.form.get('action')
      UID = request.form.get('UID')
      password = request.form.get('pass')

      # if the action was login then goes here
      if action == 'login':
        # Validate inputs
        if not UID or not password:
          error = "Username and password are required."
          raise ValueError(error)
          
        # Gets a user given parameters, makes user a variable, and commits the execution
        cur = connection.cursor()
        cur.execute("SELECT * FROM user WHERE UID = ? AND password = ?", (UID, password,))
        isUser = cur.fetchone()
        connection.commit()

        # If a user has that pass & username
        if isUser:

          # Makes a session variable with their UID
          session['UID'] = UID
          
          # Get the user's first name from the applicant table
          cur.execute("SELECT firstName FROM user WHERE UID = ?", (UID,))
          user_info = cur.fetchone()
          
          # If the user's first name is found, make a session variable with it
          if user_info:
              session['firstName'] = user_info['firstName']

          # Make a session variable with the user's role
          role = isUser['role']
          session['role'] = role

          # Redirects to home page with username in session
          if role == 'Applicant':
            return redirect(url_for('applicantHome'))
          elif role == 'Student':
            return redirect(url_for('stu_dashboard'))
          elif role == 'Admin':
            return redirect(url_for('admin_dashboard'))
          elif role == 'GS':
            return redirect(url_for('gs_dashboard'))
          elif role == 'Faculty':
            return redirect(url_for('instructor_dashboard'))
          elif role == 'CAC':
            return redirect(url_for('facultyHome'))
          elif role == 'Alumni':
            return redirect(url_for('alumni_dashboard'))
          
        # If there is no user with that pass & username, sends error
        else:
          error = "Username and Password do not match. Please double check and re-enter."
      
      connection.close()

    except ValueError as e:
      error = str(e)
    except sqlite3.Error as e:
      error = f"Database error: {str(e)}"
      if 'connection' in locals():
        connection.rollback()
        connection.close()
  
  # For GET requests or if POST processing is complete
  try:
    connection = sqlite3.connect("myDatabase.db")
    connection.row_factory = sqlite3.Row
    # renders template with variables
    return render_template('login.html', error=error)
  except Exception as e:
    error = f"Error: {str(e)}"
    return render_template('login.html', error=error)
  finally:
    if 'connection' in locals():
      connection.close()


""" FACULTY ROUTES """

# Defines a route for faculties to submit a review of an applicants application
# This includes:
# 1. rating of recommendation letters (rating + generic/credible)
# 2. decision (reject/borderline admit/admit without aid/admit with aid)
# 3. deficiency courses
# 4. reject reason
# 5. recommended advisor
# This does not in any way make a final decision on the application, that is done by the CAC/GS
@app.route('/newReview/<UID>', methods=['GET', 'POST'])
def newReview(UID):
  try:
    # Input validation
    if not UID or not UID.isdigit():
      flash("Invalid applicant ID provided", "error")
      return redirect('/facultyHome')
      
    # Get the reviewer's UID from the session for documentation purposes
    reviewerID = session.get('UID')
    if not reviewerID:
      flash("You must be logged in to submit a review", "error")
      return redirect('/')

    # Get the date of the review
    reviewerDate = datetime.now().strftime('%Y-%m-%d')

    # Get the decision from the form
    val = request.form.get('decision')
    
    # Validate decision value
    valid_decisions = ['Reject', 'Borderline Admit', 'Admit without Aid', 'Admit with Aid']
    if not val or val not in valid_decisions:
      flash("Invalid decision value", "error")
      return redirect(f'/reviewForm/{UID}')

    # Set the score based on the decision
    if val == 'Reject':
      score = 0
    elif val == 'Borderline Admit':
      score = 1
    elif val == 'Admit without Aid':
      score = 2
    elif val == 'Admit with Aid':
      score = 3

    # Get the comments, deficiency courses, reject reason, and recommended advisor from the form
    comments = request.form.get('GAS', '')
    deficiency = request.form.get('Deficiency', '')
    rejectReason = request.form.get('rejectReason') if val == 'Reject' else None
    recommendedAdvisor = request.form.get('recommendedAdvisor', '')

    connection = sqlite3.connect("myDatabase.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    
    # First get all recommendation letters for this applicant
    cursor.execute("SELECT id FROM recommendationLetter WHERE UID = ?", (UID,))
    letters = cursor.fetchall()
    
    # Process and save ratings for each recommendation letter
    for letter in letters:
      letter_id = letter['id']  # Access using dictionary-style with row_factory
      rating_key = f"rating_{letter_id}"
      generic_key = f"generic_{letter_id}"
      credible_key = f"credible_{letter_id}"
      
      rating = request.form.get(rating_key, '')
      
      # Validate rating if provided
      if rating and not rating.isdigit():
        flash(f"Invalid rating format for letter {letter_id}", "error")
        connection.close()
        return redirect(f'/reviewForm/{UID}')
        
      # Checkboxes will only be in request.form if checked
      is_generic = 1 if request.form.get(generic_key) else 0
      is_credible = 1 if request.form.get(credible_key) else 0
      
      if rating:  # Only update if rating was provided
        cursor.execute("""
          UPDATE recommendationLetter 
          SET rating = ?, isGeneric = ?, isCredible = ?
          WHERE id = ?
        """, (rating, is_generic, is_credible, letter_id))
    
    # Then insert the review form
    cursor.execute("INSERT INTO reviewForm (id, UID, reviewerUID, reviewDate, GAS_Rating, comments) VALUES (?, ?, ?, ?, ?, ?)", 
                  (None, UID, reviewerID, reviewerDate, score, comments))
    
    # Update the application with deficiency courses, reject reason, and recommended advisor
    cursor.execute("""
      UPDATE application 
      SET applicationStatus = ?, deficiencyCourses = ?, rejectReason = ?, recommendedAdvisor = ? 
      WHERE UID = ?
    """, ("Reviewed", deficiency if deficiency else None, rejectReason, recommendedAdvisor if recommendedAdvisor else None, UID))
    
    connection.commit()
    connection.close()
    
    flash("Review submitted successfully", "success")
    return redirect('/facultyHome')
    
  except sqlite3.Error as e:
    if 'connection' in locals():
      connection.rollback()
      connection.close()
    flash(f"Database error: {str(e)}", "error")
    return redirect(f'/reviewForm/{UID}')
  except Exception as e:
    if 'connection' in locals():
      connection.close()
    flash(f"An error occurred: {str(e)}", "error")
    return redirect('/facultyHome')

# Defines a route for CAC/GS to view all reviews of an applicant.
@app.route('/viewReviews/<UID>', methods=['GET', 'POST'])
def viewReviews(UID):
  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()

  # Get all reviews of the applicant
  cursor.execute("SELECT * FROM reviewForm WHERE UID = ?", (UID,))
  rows = cursor.fetchall()

  # Get all application information of the applicant
  cursor.execute("SELECT * FROM application WHERE UID = ?", (UID,))
  application = cursor.fetchone()
  
  # Fetch recommendation letters for this applicant
  cursor.execute("SELECT * FROM recommendationLetter WHERE UID = ?", (UID,))
  recommendation_letters = cursor.fetchall()
  
  connection.commit()
  connection.close()
  if len(rows) < 3:
    isEmpty = 0
  else:
    isEmpty = 1
    
  # Create a dictionary structure that includes recommendation letters
  application_data = {
    'data': application,
    'recommendation_letters': recommendation_letters
  }
  
  return render_template('viewReviews.html', rows=rows, session=session, isEmpty=isEmpty, 
                         application=application_data, UID=UID)

# Defines a route for faculties to view all applicants
# Shows each applicant's name, email, UID, application status, and the ability to view their reviews and write new reviews
@app.route('/facultyHome', methods=['GET', 'POST'])
def facultyHome():
  if session.get('role') != 'Faculty' and session.get('role') != 'GS' and session.get('role') != 'CAC':
    flash('Access denied. Faculty privileges required.', 'danger')
    return redirect(url_for('applicantHome'))
  
  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()

  # Get all applicants with their application and academic information
  cursor.execute("""
    SELECT u.*, ap.*, ai.transcripts 
    FROM user u
    RIGHT JOIN application ap ON u.UID = ap.UID
    LEFT JOIN academicInformation ai ON u.UID = ai.UID
  """)
  rows_taken = cursor.fetchall()
  
  # map the status text to a code in one line
  code_map = {
        "Incomplete": 0,
        "Complete and Under Review": 1,
        "Reviewed": 4,
        "Admitted": 2,
        "Rejected": 3,
  }
  codes = [code_map.get(row['applicationStatus']) for row in rows_taken]

  # maps the number of reviews for the uid in row the same way codes is mapped
  numrevs = [cursor.execute("SELECT COUNT(*) FROM reviewForm WHERE UID = ?", (row['UID'],)).fetchone()[0] for row in rows_taken]

  # Build once, make it re‑iterable
  rows = list(zip(rows_taken, codes, numrevs))

  connection.commit()
  connection.close()
  return render_template('facultyHome.html', rows = rows, session = session) # For faculty, we want to put some if statements here

# Defines a route for faculties to view a specific applicant's reviews and write a new review
@app.route('/reviewForm/<UID>', methods=['GET', 'POST'])
def reviewForm(UID):
  if session.get('role') != 'Faculty' and session.get('role') != 'GS' and session.get('role') != 'CAC':
    flash('Access denied. Faculty privileges required.', 'danger')
    return redirect(url_for('applicantHome'))
  
  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()
  cursor.execute("SELECT * FROM user RIGHT JOIN academicInformation ON user.UID = academicInformation.UID WHERE user.UID = ?", (UID,))
  row = cursor.fetchone()
  cursor.execute("SELECT * FROM reviewForm WHERE UID = ?", (UID,))
  reviews = cursor.fetchall()
  if (reviews):
    numberOfReviews = len(reviews)
  else:
    numberOfReviews = 0

  cursor.execute("SELECT * FROM priorDegree WHERE UID = ?", (UID,))
  priorDegrees = cursor.fetchall()
  if (priorDegrees):
    condition = 1
  else:
    condition = 0

  cursor.execute("SELECT * FROM application WHERE UID = ?", (UID,))
  app = cursor.fetchone()
  
  # Fetch recommendation letters for this applicant
  cursor.execute("SELECT * FROM recommendationLetter WHERE UID = ?", (UID,))
  recommendationLetters = cursor.fetchall()

  connection.close()

  if request.method == 'POST':
    connection = sqlite3.connect("myDatabase.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    decision = request.form.get('decision')
    if (decision == 'Admit without Aid' or decision == 'Admit with Aid'):
      cursor.execute("UPDATE application set applicationStatus = ?, decisionType = ? WHERE UID = ?", ('Admitted', decision, UID))
    elif (decision == 'Reject'):
      cursor.execute("UPDATE application set applicationStatus = ?, decisionType = ? WHERE UID = ?", ('Rejected', decision, UID))
    connection.commit()
    connection.close()
    return redirect('/facultyHome')

  if (session['role'] == 'Faculty'):
    return render_template('reviewForm.html', row = row, role = 0, numberOfReviews = numberOfReviews, condition = condition, priorDegrees = priorDegrees, app = app, recommendationLetters = recommendationLetters) #For Faculty
  elif(session['role'] == 'GS'):
    return render_template('reviewForm.html', row = row, role = 1, numberOfReviews = numberOfReviews, condition = condition, priorDegrees = priorDegrees, app = app, recommendationLetters = recommendationLetters) #For GS
  elif(session['role'] == 'CAC'):
    return render_template('reviewForm.html', row = row, role = 2, numberOfReviews = numberOfReviews, condition = condition, priorDegrees = priorDegrees, app = app, recommendationLetters = recommendationLetters) #For CAC
  elif(session['role'] == 'Admin'):
    return render_template('reviewForm.html', row = row, role = 3, numberOfReviews = numberOfReviews, condition = condition, priorDegrees = priorDegrees, app = app, recommendationLetters = recommendationLetters) #For Admin
  else:
    flash("You are not authorized to access this page", 'danger')
    return redirect('/applicantHome') #You should not be here...

""" ADMIN ROUTES """

# Defines a route for admins to view the admin dashboard
# This includes:
# 1. The ability to create new users (Other than applicants, doesn't make sense in this context)
# 2. The ability to edit existing users
# 3. The ability to delete existing users
# 4. The ability to view all applicants
# 5. The ability to view all faculties
# 6. The ability to view all GS
# 7. The ability to view all CAC
@app.route('/admin-dashboard', methods=['GET', 'POST'])
def adminDashboard():
  # Check if user is admin
  if session.get('role') != 'Admin':
    flash('Access denied. Admin privileges required.', 'danger')
    return redirect(url_for('applicantHome'))
  
  # Get all applicants, faculties, GS, and CAC
  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()
  cursor.execute("SELECT * FROM user WHERE role = 'Applicant'")
  applicants = cursor.fetchall()
  cursor.execute("SELECT * FROM user WHERE role = 'Faculty'")
  faculty = cursor.fetchall()
  cursor.execute("SELECT * FROM user WHERE role = 'GS'")
  gs = cursor.fetchall()
  cursor.execute("SELECT * FROM user WHERE role = 'CAC'")
  advisors = cursor.fetchall()
  connection.close()

  # Render the admin dashboard
  return render_template('adminDashboard.html', applicants=applicants, faculties=faculty, gs=gs, advisors=advisors)


# Defines a route for admins to edit an existing user
@app.route('/edit-user/<uid>', methods=['GET', 'POST'])
def edit_user(uid):
  # Check if user is admin
  if session.get('role') != 'Admin':
    flash('Access denied. Admin privileges required.', 'danger')
    return redirect(url_for('applicantHome'))
    
  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()
  
  if request.method == 'POST':
    # Get form data
    password = request.form.get('password')
    role = request.form.get('role')
    
    try:
      # Update user
      cursor.execute("UPDATE user SET password = ?, role = ? WHERE UID = ?", 
                    (password, role, uid))
      connection.commit()
      flash("User updated successfully", "success")
      return redirect(url_for('adminDashboard'))
    except sqlite3.Error as e:
      connection.rollback()
      flash(f"Error updating user: {str(e)}", "danger")
  
  # Fetch user data for GET request
  cursor.execute("SELECT * FROM user WHERE UID = ?", (uid,))
  user = cursor.fetchone()
  
  if not user:
    connection.close()
    flash("User not found", "danger")
    return redirect(url_for('adminDashboard'))
  
  connection.close()
  return render_template('editUser.html', user=user)

# Defines a route for admins to delete a user
@app.route('/delete-user/<uid>', methods=['GET'])
def delete_user(uid):
  # Check if user is admin
  if session.get('role') != 'Admin':
    flash('Access denied. Admin privileges required.', 'danger')
    return redirect(url_for('applicantHome'))
  
  # Validate UID
  if not uid or not uid.isdigit():
    flash("Invalid user ID format", "danger")
    return redirect(url_for('adminDashboard'))
    
  connection = None
  try:
    connection = sqlite3.connect("myDatabase.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    
    # Begin transaction
    connection.execute("BEGIN TRANSACTION")
    
    # Check if the user exists first
    cursor.execute("SELECT * FROM user WHERE UID = ?", (uid,))
    user = cursor.fetchone()
    
    if not user:
      flash("User not found", "warning")
      return redirect(url_for('adminDashboard'))
      
    # Check if the user is an applicant
    cursor.execute("SELECT * FROM user WHERE UID = ?", (uid,))
    applicant = cursor.fetchone()
    
    if applicant:
      # Delete related records in dependency order to avoid constraint violations
      
      # First delete from reviewForm if exists
      cursor.execute("DELETE FROM reviewForm WHERE UID = ?", (uid,))
      
      # Delete from recommendationLetter table if exists
      cursor.execute("DELETE FROM recommendationLetter WHERE UID = ?", (uid,))
      
      # Delete from priorDegree table if exists
      cursor.execute("DELETE FROM priorDegree WHERE UID = ?", (uid,))
      
      # Delete from application table if exists
      cursor.execute("DELETE FROM application WHERE UID = ?", (uid,))
      
      # Delete from academicInformation
      cursor.execute("DELETE FROM academicInformation WHERE UID = ?", (uid,))
      
      # # If user is an applicant, delete from applicant table
      # cursor.execute("DELETE FROM applicant WHERE UID = ?", (uid,))
    
    # Finally delete from user table
    cursor.execute("DELETE FROM user WHERE UID = ?", (uid,))
    
    # Commit transaction
    connection.commit()
    flash("User deleted successfully", "success")
  except sqlite3.Error as e:
    if connection:
      connection.rollback()
    flash(f"Error deleting user: {str(e)}", "danger")
  finally:
    if connection:
      connection.close()
  
  return redirect(url_for('adminDashboard'))

""" GS ROUTES """
# Defines a route for GS to update a transcript status, again, a simulated type deal, implicit that
# the applicant 'mails' their transcripts to the university and GS updates accordingly
@app.route('/update_transcript/<UID>', methods=['POST'])
def update_transcript(UID):
  if session.get('role') != 'GS':
    flash('Access denied. GS privileges required.', 'danger')
    return redirect(url_for('applicantHome'))
    
  transcript_status = request.form.get('transcript_status')
  
  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()
  
  try:
    cursor.execute("UPDATE academicInformation SET transcripts = ? WHERE UID = ?", 
                  (transcript_status, UID))
    connection.commit()
    flash("Transcript status updated successfully", "success")
  except sqlite3.Error as e:
    connection.rollback()
    flash(f"Error updating transcript status: {str(e)}", "danger")
  finally:
    connection.close()
  
  return redirect(url_for('facultyHome'))

""" MISC ROUTES """

@app.route('/logout', methods=['GET', 'POST'])
def logout():
  session.clear()
  return redirect('/')

@app.route('/reset', methods=['GET', 'POST'])
def reset():

# APPS Starting State
# - Unused IDs: Make sure the following names and IDs are **not** used in your database start state/data.
# (The names are listed as Last name, First name and the ID)
# - Coltrane, John with SSN 111-22-3333 and Univ ID 11111111
# - Davis, Miles with SSN 222-22-3333 and univ ID 22222222
# - Monk, Thelonious with SSN 333-22-3333 and univ ID 33333333
# - Getz, Stan with SSN 444-22-3333 and ID 44444444
# - Applicants: There must be two applicants entered into the system with the Student numbers and other
# data as specified below:
# - John Lennon, SSN 111-11-1111, (and univ ID 12312312) and application is complete but no reviews.
# Provide us with their system login info (so they can check on their status).
# - Ringo Starr, SSN 222-11-1111 (and univ ID 66666666), application is incomplete. Provide us with
# their system login info (so they can check on their status).
# - Users: Create GS, CAC, and at least one faculty reviewer Narahari. Provide their system login info in
# your Git Issue. (Additional faculty reviewers should be Wood, Heller.)


  session.clear()
  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()
  cursor.execute("DELETE FROM academicInformation")
  cursor.execute("DELETE FROM application")
  cursor.execute("DELETE FROM priorDegree")
  cursor.execute("DELETE FROM recommendationLetter")
  cursor.execute("DELETE FROM reviewForm")
  cursor.execute("DELETE FROM sqlite_sequence")
  cursor.execute("DELETE FROM user")
  cursor.execute("INSERT INTO user (UID, role, password, firstName, lastName, ssn, email, phone, address, address2) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ('12312312', 'Applicant', 'pass', 'John', 'Lennon', '111-11-1111', 'lennon@gmail.com', '111-867-5309', 'Address #1', 'Address #2')) #John Lennon
  cursor.execute("INSERT INTO academicInformation (UID, degree, GRE_Verbal, GRE_Quant, GRE_Year, GRE_Advanced, GRE_Subject, TOEFL_Score, TOEFL_Date, areasOfInterest, priorWorkExp, transcripts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ('12312312', 'MS', '140', '150', '1969', None, None, '115', '1969-04-12', 'some cool interest', 'He worked here', 'transcripts'))
  cursor.execute("INSERT INTO application (UID, applicationStatus, applySemester, applyYear, decisionType, recommendedAdvisor, deficiencyCourses, rejectReason, finalDecisionDate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", ('12312312', 'Complete and Under Review', 'Spring', '2024', None, None, None, None, None))
  cursor.execute("INSERT INTO priorDegree (id, UID, degreeName, institution, major, GPA, year) VALUES (?, ?, ?, ?, ?, ?, ?)", (None, '12312312', 'BS', 'University A', 'Math', 3.8, '1968'))
  cursor.execute("INSERT INTO recommendationLetter (id, UID, writerName, writerEmail, writerAffiliation, letter, submissionDate, token, status, rating, isGeneric, isCredible) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (None, '12312312', 'Professor Bleepy', 'Bleepy@gwu.edu', 'BLEEP', 'HERE IS A LETTER', '1968-10-15','token1', 'Pending', 1, 1, 1))
  
  #Ringo Starr's incomplete application
  cursor.execute("INSERT INTO user (UID, role, password, firstName, lastName, ssn, email, phone, address, address2) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ('66666666', 'Applicant', 'pass', 'Ringo', 'Starr', '222-11-1111', 'starr@gmail.com', '101-010-1010', 'Address #1', 'Address #2')) 

  #Admin account
  cursor.execute("INSERT INTO user (UID, role, password, firstName, lastName, ssn, email, phone, address, address2) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ('00000000', 'Admin', 'pass', 'Ringo', 'Starr', '222-11-1111', 'starr@gmail.com', '101-010-1010', 'Address #1', 'Address #2'))
  
  #GS account
  cursor.execute("INSERT INTO user (UID, role, password, firstName, lastName, ssn, email, phone, address, address2) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ('10101010', 'GS', 'pass', 'Ringo', 'Starr', '222-11-1111', 'starr@gmail.com', '101-010-1010', 'Address #1', 'Address #2'))
  
  #CAC account
  cursor.execute("INSERT INTO user (UID, role, password, firstName, lastName, ssn, email, phone, address, address2) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ('12345678', 'CAC', 'pass', 'Ringo', 'Starr', '222-11-1111', 'starr@gmail.com', '101-010-1010', 'Address #1', 'Address #2'))
  
  #Faculty account
  cursor.execute("INSERT INTO user (UID, role, password, firstName, lastName, ssn, email, phone, address, address2) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ('12345679', 'Faculty', 'pass', 'Ringo', 'Starr', '222-11-1111', 'starr@gmail.com', '101-010-1010', 'Address #1', 'Address #2'))
 
  connection.commit()
  connection.close()
  return redirect('/')

@app.route('/home', methods=['GET', 'POST'])
def home():
  if 'UID' not in session:
    return redirect('/')
  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()
  if session['role'] == 'Student':
    #cursor.execute("SELECT UID FROM student JOIN user ON student.UID = user.UID WHERE user.email = ?", (session['email'],))
    #student_UID = cursor.fetchone()
    
    id = session['UID']
    GPA = calculate_gpa(id)
    cursor.execute("UPDATE student SET GPA = ? WHERE UID = ?",(GPA, id))
    low_grade_count = count_low_grades(id)
    if low_grade_count >= 3:
      connection.commit()
      connection.close()
      return render_template("login.html", error = False, is_suspended = True)
  else:
    id = session['UID']

  cursor.execute("SELECT * FROM user WHERE UID = ?", (id,))
  user = cursor.fetchone()

  connection.commit()
  connection.close()

  return render_template('home.html', role = session['role'], fname = user['firstName'], lname = user['lastName'], id = id)

#Form 1 
# student must enter at most 12 courses 
# form must meet degree req
#probably will be like okay if user in session -> show their name + id + let them add classes 
#shopping cart searched + login combined 
#will still need to have a button to add the course -> cart
#12 boxes -> dropdown for course 
#after they add their courses 
#submit -> insert into db 
#once logged in add a sesssion for like type of user

@app.route('/form1',methods = ['GET', 'POST'])
def form1():
  #if user isnt logged in, redirect to login
  if 'UID' not in session:
    return redirect (url_for('login'))

  #connect to db 
  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()

  # Get student info including advisor_id
  UID = session['UID']
  cursor.execute("SELECT program, advisor_id FROM student WHERE UID = ?", (UID,))
  student = cursor.fetchone()
  program = student['program']
  advisor_id = student['advisor_id']

  # Check if advisor_id is NULL (i.e., no advisor assigned)
  if advisor_id is None:
    connection.close()
    flash("You must have an advisor assigned before submitting a Form.", "warning")
    return redirect(url_for('stu_dashboard')) 
  
  #to display all courses 
  cursor.execute("SELECT * FROM course")
  rows = cursor.fetchall()

  # get their completed courses
  cursor.execute("SELECT t.course_id FROM transcript t WHERE t.student_uid = ?", (UID,))
  completed_courses = [row['course_id'] for row in cursor.fetchall()]
  
  # Check if the student already has a submitted form
  cursor.execute("SELECT form1_id FROM form1 WHERE UID = ? AND status = 'Submitted'", (UID,))
  existing_form1 = cursor.fetchone()
  #when form is submitted 
  if request.method == 'POST':

    if existing_form1:
      #if form 1 exists update it
      form1_id = existing_form1['form1_id']
      cursor.execute("UPDATE form1 SET status = 'Submitted' WHERE form1_id = ?", (form1_id,))
      #clear existing courses before inserting new ones
      cursor.execute("DELETE FROM form1_course WHERE form1_id = ?", (form1_id,))
    else:
      # If it's a new form, insert a new entry
      cursor.execute("INSERT INTO form1 (UID, status) VALUES (?, ?)", (UID, "Submitted"))
      form1_id = cursor.lastrowid 
    
    #list for all dropdown items (Course Fields) for form1 
    course_fields = [ "course_1", "course_2", "course_3", "course_4", "course_5", "course_6", 
                     "course_7","course_8", "course_9" ,"course_10" ,"course_11", "course_12"]
    
    #will be used to keep track of selected courses and check for duplicates 
    selected = []

    #for each field in course fields 
    for field in course_fields:
      course_id = request.form.get(field) #course id will be: getting the selected val from form1 field (dropdowns) 
      if course_id:
        if course_id in selected: #if course id was already in selected
          connection.close()
          flash("You selected the same course twice. Please fix it!", "danger")
          return redirect(url_for('form1'))
        selected.append(course_id) #if it hasnt been selected already, add it to the list for db 
        cursor.execute("INSERT INTO form1_course (form1_id, course_id) VALUES (?, ?)", (form1_id, course_id))

    connection.commit()
    connection.close()
    flash("Form 1 submitted successfully!", "success")
    return redirect(url_for('stu_dashboard'))

  connection.commit()
  connection.close
  return render_template("form1.html", courses = rows, program = program, completed_courses = completed_courses, existing_form1 = existing_form1)

@app.route('/personal_information/<UID>', methods = ['GET', 'POST'])
def personal_information(UID):
  if 'email' not in session:
    return redirect (url_for('login'))

  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()

  cursor.execute("SELECT * FROM user WHERE UID = ?", (UID,))
  userdata = cursor.fetchone()

  connection.commit()
  connection.close()

  return render_template("personal_info.html", UID = UID, userdata = userdata)

@app.route('/edit_personal_info/<UID>', methods = ['GET', 'POST'])
def edit_personal_info(UID):
  if 'email' not in session:
    return redirect (url_for('login'))

  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()
  
  if request.method == 'POST':
    new_fname = request.form['firstName']
    new_lname = request.form['lastName']
    new_email = request.form['email']
    cursor.execute("UPDATE user SET firstName = ?, lastName = ?, email = ? WHERE UID = ?",(new_fname, new_lname, new_email, UID))
    # if updating own info change session
    if int(UID) == session['UID']:
      session['email'] = new_email
      session['fname'] = new_fname
      session['lname'] = new_lname
    connection.commit()
    connection.close()
    return redirect(url_for('personal_information', UID = UID))

  cursor.execute("SELECT * FROM user WHERE UID = ?", (UID,))
  userdata = cursor.fetchone()

  connection.commit()
  connection.close()

  return render_template("edit_personal_info.html", userdata = userdata, UID = UID)


@app.route('/edit_student_info/<student_UID>', methods = ['GET', 'POST'])
def edit_student_info(student_UID):
  if 'UID' not in session:
    return redirect (url_for('login'))

  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()

  if request.method == 'POST':
    new_fname = request.form['firstName']
    new_lname = request.form['lastName']
    new_email = request.form['email']
    cursor.execute("UPDATE user SET firstName = ?, lastName = ?, email = ? WHERE UID = ?",(new_fname, new_lname, new_email, student_UID))
    connection.commit()
    connection.close()
    return redirect(url_for('student_information', student_UID = student_UID))

  cursor.execute("SELECT * FROM user WHERE UID = ?", (student_UID,))
  userdata = cursor.fetchone()

  connection.commit()
  connection.close()

  return render_template("edit_student_info.html", userdata = userdata, student_UID = student_UID)

@app.route('/assign_advisor/<student_UID>', methods = ['GET', 'POST'])
def assign_advisor(student_UID):
  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()

  cursor.execute("SELECT * FROM faculty JOIN user ON faculty.UID = user.UID")
  faculty_advisors = cursor.fetchall()

  if request.method == 'POST':
    advisor_id = request.form['advisor']
    cursor.execute("UPDATE student SET advisor_id = ? WHERE UID = ?",(advisor_id, student_UID))
    connection.commit()
    connection.close()
    return redirect(url_for('student_information', student_UID = student_UID))

  cursor.execute("SELECT user.firstName, user.lastName FROM student JOIN user ON student.UID = user.UID WHERE student.UID= ?", (student_UID,))
  studentdata = cursor.fetchone()

  connection.commit()
  connection.close()
  return render_template("assign_advisor.html", faculty_advisors = faculty_advisors, studentdata = studentdata, student_UID = student_UID)

@app.route('/pending_students', methods = ['GET', 'POST'])
def pending_students():
  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()

  cursor.execute("SELECT * FROM student JOIN user ON student.UID = user.UID WHERE student.advisor_id IS NULL")
  pending_students = cursor.fetchall()

  return render_template("pending_students.html", pending_students = pending_students)

@app.route('/student_information/<student_UID>', methods = ['GET', 'POST'])
def student_information(student_UID):
  if 'UID' not in session:
    return redirect (url_for('login'))

  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()
 
  # check if they have advising hold
  cursor.execute("SELECT advising_hold FROM student WHERE UID = ?", (student_UID,))
  advisinghold = cursor.fetchone()['advising_hold']
  
  #check if user is cleared for grad
  cursor.execute("SELECT * FROM applied_for_grad WHERE UID = ? AND cleared = 'Cleared'",(student_UID,))
  cleared = cursor.fetchone()
  is_cleared = True
  if cleared == None:
    is_cleared = False

  cursor.execute("SELECT status FROM form1 WHERE UID = ?", (student_UID,))
  form1 = cursor.fetchone()

  if form1 is not None:
    form1_submitted = True
    form1_status = form1['status']
  else:
    form1_submitted = False
    form1_status = 'not submitted'

  GPA = calculate_gpa(student_UID)
  cursor.execute("UPDATE student SET GPA = ? WHERE UID = ?", (GPA, student_UID))
  
  cursor.execute("SELECT user.firstName, user.lastName, user.email, student.UID, student.program, student.thesis_status, student.advisor_id, student.GPA FROM user JOIN student ON user.UID = student.UID WHERE student.UID = ?", (student_UID,))
  userdata = cursor.fetchone()
  if userdata:
    advisor_id = userdata['advisor_id']
    cursor.execute("SELECT user.firstName, user.lastName FROM user JOIN faculty ON user.UID = faculty.UID WHERE faculty.UID = ?",(advisor_id,))
    facultydata = cursor.fetchone()
  else: 
    facultydata = None

  if userdata:
    thesis_approved = userdata['thesis_status']

  # TRANSCRIPT INFO
  coursedetails = []
  cursor.execute("SELECT course.dept, course.course_num, course.title, course.credits, transcript.semester, transcript.year, transcript.grade, course.course_id FROM transcript JOIN course ON transcript.course_id = course.course_id JOIN student ON transcript.student_uid = student.UID WHERE student.UID = ? ORDER BY transcript.year ASC, CASE transcript.semester WHEN 'Fall' THEN 1 WHEN 'Spring' THEN 2 END, transcript.grade ASC", (student_UID,))
  transcript = cursor.fetchall()
  for row in transcript:
    coursedetails.append({
      'deptname': row[0],
      'coursenum': row[1],
      'coursename': row[2],
      'credits': row[3],
      'semester': row[4],
      'year': row[5],
      'grade': row[6],
      'course_id' : row[7]
    })

  cursor.execute("SELECT * FROM thesis WHERE UID = ?", (student_UID,))
  thesis = cursor.fetchone()
  thesis_submitted = False
  if thesis:
    thesis_submitted = True
     
  low_grade_count = count_low_grades(student_UID)
  if low_grade_count >= 3:
    connection.commit()
    connection.close()
    return render_template("student_info.html", userdata = userdata, is_cleared = is_cleared, role = session['role'], transcriptcourses = coursedetails, student_UID = student_UID,  form1_submitted = form1_submitted, form1_status = form1_status, thesis_approved = thesis_approved, facultydata = facultydata, is_suspended = True, advisinghold = advisinghold, thesis_submitted = thesis_submitted)
      
  connection.commit()
  connection.close()

  return render_template("student_info.html", userdata = userdata, is_cleared = is_cleared, role = session['role'], transcriptcourses = coursedetails, student_UID = student_UID,  form1_submitted = form1_submitted, form1_status = form1_status, thesis_approved = thesis_approved, facultydata = facultydata, is_suspended = False, advisinghold = advisinghold, thesis_submitted = thesis_submitted)

@app.route('/edit_grade/<student_UID>/<course_id>', methods = ['GET', 'POST'])
def edit_grade(student_UID, course_id):
  if 'email' not in session:
    return redirect(url_for('login'))
  
  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()
 
  if request.method == 'POST':
    new_grade = request.form['grade']
    cursor.execute("UPDATE transcript SET grade = ? WHERE student_UID = ? AND transcript.course_id = ?",(new_grade, student_UID, course_id))
    connection.commit()
    connection.close()
    return redirect(url_for('student_information', student_UID = student_UID))


  cursor.execute("SELECT * FROM course WHERE course_id = ?", (course_id,))
  coursedata = cursor.fetchone()

  connection.commit()
  connection.close()

  return render_template("edit_grade.html", coursedata = coursedata, student_UID = student_UID, course_id = course_id)

#perform the audit
@app.route('/admin_add_student', methods=['GET', 'POST'])
def admin_add_student():
  connection = sqlite3.connect("myDatabase.db")
  cursor = connection.cursor()
  if request.method == 'POST':
    #assign student ransom 8 digit id
    while True:
      new_UID = random.randint(10000000,99999999)
      cursor.execute("SELECT * FROM student WHERE UID = ?", (new_UID,))
      if not cursor.fetchone():
        break
    email = request.form["email"]
    passw = request.form["password"]
    fname = request.form["fname"]
    lname = request.form["lname"]
    ssn = request.form["ssn"]
    phone = request.form["phone"]
    address = request.form["address"]
    address2 = request.form["address2"]
    gradtype = request.form["gradtype"]
    cursor.execute("INSERT INTO user (UID, email, password, firstName, lastName, role, ssn, phone, address, address2) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",(new_UID, email, passw, fname, lname, 'Student', ssn, phone, address, address2))
    UID = cursor.lastrowid
    # Insert into student table
    if gradtype == 'Masters':
      cursor.execute("INSERT INTO student (UID, program) VALUES (?, ?)", (new_UID, "Masters"))
    if gradtype == 'PHD':
      cursor.execute("INSERT INTO student (UID, program) VALUES (?, ?)", (new_UID, "PhD"))
    connection.commit()
    connection.close()
    return redirect(url_for('display_students'))

  connection.commit()
  connection.close()
  return render_template('add_student.html')

@app.route('/admin_add_employee', methods=['GET', 'POST'])
def admin_add_employee():
  connection = sqlite3.connect("myDatabase.db")
  cursor = connection.cursor()
  if request.method == 'POST':
    email = request.form["email"]
    passw = request.form["password"]
    fname = request.form["fname"]
    lname = request.form["lname"]
    type_employee = request.form["type_employee"]
    if type_employee == 'faculty':
      dept = request.form["dept"]
      cursor.execute("INSERT INTO user (email, password, firstName, lastName, role) VALUES (?, ?, ?, ?, ?)",(email, passw, fname, lname, "Faculty"))
      UID = cursor.lastrowid
      #assign student ransom 8 digit id
      while True:
        new_UID = random.randint(10000000,99999999)
        cursor.execute("SELECT * FROM faculty WHERE UID = ?", (new_UID,))
        if not cursor.fetchone():
          break
      # Insert into student table
      cursor.execute("INSERT INTO faculty (UID, dept) VALUES (?, ?)", (new_UID, dept))
      connection.commit()
      connection.close()
      return redirect(url_for('display_faculty'))
    
    if type_employee == 'GS':
      cursor.execute("INSERT INTO user (email, password, firstName, lastName, role) VALUES (?, ?, ?, ?, ?)",(email, passw, fname, lname, "GS"))
      UID = cursor.lastrowid
      #assign student ransom 8 digit id
      while True:
        new_UID = random.randint(10000000,99999999)
        cursor.execute("SELECT * FROM grad_secretary WHERE UID = ?", (new_UID,))
        if not cursor.fetchone():
          break
      # Insert into student table
      cursor.execute("INSERT INTO grad_secretary (UID) VALUES ?", (new_UID,))
      connection.commit()
      connection.close()
      return redirect(url_for('display_faculty'))

  connection.commit()
  connection.close()
  return render_template('add_employee.html')

@app.route('/apply_graduation', methods=['GET', 'POST'])
def apply_graduation():
    # Connect to the database
    connection = sqlite3.connect('myDatabase.db')
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    # Retrieve student info
    cursor.execute("SELECT student.UID, student.program, student.GPA, student.thesis_status FROM student JOIN user ON student.UID = user.UID WHERE user.UID = ?", (session['UID'],))
    userdata = cursor.fetchone()
    UID = userdata['UID']
    grad_type = userdata['program']
    GPA = userdata['GPA']
    thesis_status = userdata['thesis_status']

    # Check if student has already applied
    cursor.execute("SELECT * FROM applied_for_grad WHERE UID = ? AND cleared = 'Cleared'", (UID,))
    applied = cursor.fetchone()
    if applied is not None:
        return render_template("applied.html", cleared=False, error=None, already_applied=True)

    # Check if Master's requirements are fulfilled
    if grad_type == 'Masters':
        # Initialize requirement statuses
        requirements_status = {
          'core_courses': False,
          'credits': False,
          'grades': False,
          'GPA': False,
          'advisor_approval': False,
          'form_match': False
        }
        if GPA >= 3.0:
          requirements_status['GPA'] = True
        # Check core courses
        cursor.execute("SELECT COUNT(*) AS core_courses FROM course c JOIN transcript t ON c.course_id = t.course_id WHERE t.student_uid = ? AND c.dept = 'CSCI' AND c.course_num IN (6212, 6221, 6461)", (UID,))
        core_courses = cursor.fetchone()['core_courses']
        requirements_status['core_courses'] = core_courses == 3

        # Check total credits
        cursor.execute("SELECT SUM(c.credits) AS total_credits FROM course c JOIN transcript t ON c.course_id = t.course_id WHERE t.student_uid = ?", (UID,))
        total_credits = cursor.fetchone()['total_credits']
        requirements_status['credits'] = total_credits >= 30

        # Check grades
        cursor.execute("SELECT COUNT(*) AS grades_count FROM course c JOIN transcript t ON c.course_id = t.course_id WHERE t.student_uid = ? AND t.grade IN ('C', 'C+', 'C-', 'D', 'D+', 'D-', 'F')", (UID,))
        grades_count = cursor.fetchone()['grades_count']
        requirements_status['grades'] = grades_count <= 2

    # Check if PhD requirements are fulfilled
    elif grad_type == 'PhD':
      # Initialize requirement statuses
      requirements_status = {
        'credits': False,
        'grades': False,
        'thesis': False,
        'GPA': False,
        'advisor_approval': False,
        'form_match': False
      }
      if GPA >= 3.5:
        requirements_status['GPA'] = True
      # Check total credits
      cursor.execute("SELECT SUM(c.credits) AS total_credits FROM course c JOIN transcript t ON c.course_id = t.course_id WHERE t.student_uid = ?", (UID,))
      total_credits = cursor.fetchone()['total_credits']
      requirements_status['credits'] = total_credits >= 36

      # Check CS credits
      cursor.execute("SELECT SUM(c.credits) AS total_credits FROM course c JOIN transcript t ON c.course_id = t.course_id WHERE t.student_uid = ? AND c.dept LIKE 'CSCI%'", (UID,))
      cs_credits = cursor.fetchone()['total_credits']
      requirements_status['cs_credits'] = cs_credits >= 30

      # Check grades
      cursor.execute("SELECT COUNT(*) AS grades_count FROM course c JOIN transcript t ON c.course_id = t.course_id WHERE t.student_uid = ? AND t.grade IN ('C', 'C+', 'C-', 'D', 'F')", (UID,))
      grades_count = cursor.fetchone()['grades_count']
      requirements_status['grades'] = grades_count <= 1

      # Check thesis status
      requirements_status['thesis'] = thesis_status == 'Approved'

    # Check if the advising form is approved
    cursor.execute("SELECT status, form1_id FROM form1 WHERE UID = ?", (UID,))
    form = cursor.fetchone()
    if form:
        requirements_status['advisor_approval'] = form['status'] == 'Approved'
        
        # Check if the advising form matches the transcript
        cursor.execute("SELECT course_id FROM form1_course WHERE form1_id = ?", (form['form1_id'],))
        form_courses = cursor.fetchall()
        cursor.execute("SELECT course_id FROM transcript WHERE student_uid = ?", (UID,))
        transcript_courses = cursor.fetchall()

        form_courses_set = set([course['course_id'] for course in form_courses])
        transcript_courses_set = set([course['course_id'] for course in transcript_courses])
        requirements_status['form_match'] = form_courses_set == transcript_courses_set
    else:
      requirements_status['advisor_approval'] = False
      requirements_status['form_match'] = False

    # Check if all conditions are met
    audit_passed = all(requirements_status.values())

    # Pass the requirements status to the template
    return render_template("applied.html", cleared=audit_passed, error=None, already_applied=False, requirements_status=requirements_status, audit_passed = audit_passed, UID = UID, grad_type = grad_type)

@app.route('/apply/<audit_passed>/<UID>', methods=['GET', 'POST'])
def apply(audit_passed, UID):
    # Connect to the database
    connection = sqlite3.connect('myDatabase.db')
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    # If the audit passes, insert into applied_for_grad
    if audit_passed:
        cursor.execute("INSERT INTO applied_for_grad (UID, cleared) VALUES (?, ?)", (UID, 'Cleared'))
        flash('You have successfully applied for graduation! Your application is cleared.', 'success')
    else:
        cursor.execute("INSERT INTO applied_for_grad (UID, cleared) VALUES (?, ?)", (UID, 'Not Cleared'))
        flash('Your graduation application was submitted but you did not meet all requirements.', 'danger')

    connection.commit()
    connection.close()
    
    # Redirect to the dashboard (or wherever you want the user to go after applying)
    return redirect(url_for('stu_dashboard'))

@app.route('/display_students', methods = ['GET', 'POST'])
def display_students():
  #check if type user in session
  role = session['role']
  connection = sqlite3.connect('myDatabase.db')
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()
  if role == 'GS':
    cursor.execute("SELECT * FROM student JOIN user ON student.UID = user.UID")
  if role == 'Faculty':
    UID = session['UID']
    cursor.execute("SELECT * FROM student JOIN user ON student.UID = user.UID WHERE student.advisor_id = ?",(UID,))
  if role == 'Admin':
    cursor.execute("SELECT * FROM student JOIN user ON student.UID = user.UID")
  studentData = cursor.fetchall()

  connection.commit()
  connection.close()

  return render_template("students.html", students = studentData, role = role)

@app.route('/display_faculty', methods = ['GET', 'POST'])
def display_faculty():
  #check if type user in session
  role = session['role']
  connection = sqlite3.connect('myDatabase.db')
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()

  if role != 'Admin':
    return redirect('/home')

  cursor.execute("SELECT * FROM faculty JOIN user ON faculty.UID = user.UID")
  facultyData = cursor.fetchall()

  cursor.execute("SELECT * FROM grad_secretary JOIN user ON grad_secretary.UID = user.UID")
  gsData = cursor.fetchall()
  
  connection.commit()
  connection.close()

  return render_template("faculty.html", faculties = facultyData, gsData = gsData, role = role)

@app.route('/display_alumni', methods = ['GET', 'POST'])
def display_alumni():
  #check if type user in session
  role = session['role']
  connection = sqlite3.connect('myDatabase.db')
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()

  if role != 'Admin':
    return redirect('/home')

  cursor.execute("SELECT * FROM alumni JOIN user ON alumni.UID = user.UID WHERE alumni.UID IS NOT NULL")
  alumniData = cursor.fetchall()
  
  connection.commit()
  connection.close()

  return render_template("alumni.html", alumni = alumniData, role = role)

@app.route('/alumni_transcript/<UID>', methods = ['GET', 'POST'])
def alumni_transcript(UID):
  #check if type user in session
  role = session['role']
  connection = sqlite3.connect('myDatabase.db')
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()

  if role != 'Alumni' and role != 'Admin':
    return redirect('/home')

  cursor.execute("SELECT * FROM alumni JOIN user ON alumni.UID = user.UID WHERE alumni.UID = ?", (UID,))
  alumniData = cursor.fetchone()
  # JOIN student ON user.UID = student.fUID 

  # TRANSCRIPT INFO
  coursedetails = []
  cursor.execute("SELECT course.dept, course.course_num, course.title, course.credits, transcript.semester, transcript.year, transcript.grade, course.course_id FROM transcript JOIN course ON transcript.course_id = course.course_id JOIN alumni ON alumni.UID = transcript.student_uid WHERE alumni.UID = ?", (UID,))
  transcript = cursor.fetchall()
  for row in transcript:
    coursedetails.append({
      'deptname': row[0],
      'coursenum': row[1],
      'coursename': row[2],
      'credits': row[3],
      'semester': row[4],
      'year': row[5],
      'grade': row[6],
      'course_id' : row[7]
    })
    
  connection.commit()
  connection.close()

  return render_template("alumni_transcript.html", alumniData = alumniData, role = session['role'], transcriptcourses = coursedetails, student_UID = UID)

@app.route('/clear_grad/<student_UID>', methods = ['GET', 'POST'])
def clear_grad(student_UID):
  # # make sure secretary
  if session['role'] not in ['GS', 'admin']:
    return redirect(url_for('home'))
  
  connection = sqlite3.connect('myDatabase.db')
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()

  # delete from graduate table and add to alumni table
  cursor.execute("UPDATE user SET role = 'Alumni' WHERE UID = ?", (student_UID,))
  cursor.execute("INSERT INTO alumni (UID) VALUES (?)", (student_UID,))
  cursor.execute("DELETE FROM student WHERE UID = (?)", (student_UID,))
  #might also want to delete from applied?
  
  connection.commit()
  connection.close()
  if session['role'] == 'GS':
    return redirect (url_for('gs_dashboard')) 
  return redirect (url_for('admin_dashboard')) 

def ms_requirements(UID):
  connection = sqlite3.connect('myDatabase.db')
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()
  # completed all 3 core courses required for MS: CSCI 6212, CSCI 6221, and CSCI 6461
  cursor.execute("SELECT COUNT(*) AS core_courses FROM course c JOIN transcript t ON c.course_id = t.course_id WHERE t.student_uid = ? AND c.dept = 'CSCI' AND c.course_num IN (6212, 6221, 6461)",(UID,))
  data = cursor.fetchone()
  core_courses_taken = data['core_courses']
  if core_courses_taken != 3:
    connection.close()
    return False
  # completed at least 30 credit hours of coursework
  cursor.execute("SELECT SUM(c.credits) AS total_credits FROM course c JOIN transcript t ON c.course_id = t.course_id WHERE t.student_uid = ?",(UID,))
  data = cursor.fetchone()
  total_credits = data['total_credits']
  if total_credits < 30:
    connection.close()
    return False
  # taken at most 2 courses outside the CS department as part of the 30 credit hours of coursework
  cursor.execute("SELECT COUNT(*) as course_count FROM course c JOIN transcript t ON c.course_id = t.course_id WHERE t.student_uid = ? AND dept NOT LIKE 'CSCI%'",(UID,))
  data = cursor.fetchone()
  course_count = data['course_count']
  if course_count > 2:
    connection.close()
    return False
  # no more than 2 grades below B
  cursor.execute("SELECT COUNT(*) as grades_count FROM course c JOIN transcript t ON c.course_id = t.course_id WHERE t.student_uid = ? AND t.grade IN ('C', 'C+', 'C-', 'D', 'D+', 'D-', 'F')",(UID,))
  data = cursor.fetchone()
  grades_count = data['grades_count']

  if grades_count > 2:
    connection.close()
    return False

  connection.close()
  return True

def phd_requirements(UID):
  connection = sqlite3.connect('myDatabase.db')
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()
  # completed at least 36 credit hours
  cursor.execute("SELECT SUM(c.credits) AS total_credits FROM course c JOIN transcript t ON c.course_id = t.course_id WHERE t.student_uid = ?",(UID,))
  data = cursor.fetchone()
  total_credits = data['total_credits']
  if total_credits < 36:
    connection.close()
    return False
  # completed at least 30 credit hours of coursework in CS
  cursor.execute("SELECT SUM(c.credits) AS total_credits FROM course c JOIN transcript t ON c.course_id = t.course_id WHERE t.student_uid = ? AND c.dept LIKE 'CSCI%'",(UID,))
  data = cursor.fetchone()
  total_credits = data['total_credits']
  if total_credits < 30:
    connection.close()
    return False
  # no more than 1 grades below B
  cursor.execute("SELECT COUNT(*) as grades_count FROM course c JOIN transcript t ON c.course_id = t.course_id WHERE t.student_uid = ? AND t.grade IN ('C', 'C+', 'C-', 'D', 'F')",(UID,))
  data = cursor.fetchone()
  grades_count = data['grades_count']
  if grades_count > 1:
    connection.close()
    return False

  connection.close()
  return True


@app.route('/form1submission/<student_UID>', methods = ['GET', 'POST'])
def form1submission(student_UID):
  if 'UID' not in session:
    return redirect (url_for('login'))

  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()

  cursor.execute("SELECT course.course_id, course.title, course.dept, course.course_num FROM form1 JOIN form1_course ON form1.form1_id = form1_course.form1_id JOIN course on form1_course.course_id = course.course_id WHERE form1.UID = ?", (student_UID, ))
  form1courses = cursor.fetchall()

  is_form1courses = True
  if form1courses == None:
    is_form1courses = False

  cursor.execute("SELECT user.firstName, user.lastName, user.email, student.UID FROM user JOIN student ON user.UID = student.UID WHERE student.UID = ?", (student_UID,))
  userdata = cursor.fetchone()
    
  connection.commit()
  connection.close()

  return render_template("form1submission.html", form1courses = form1courses, is_form1courses = is_form1courses, userdata = userdata, role = session['role'])

@app.route('/submit_thesis', methods=['GET', 'POST'])
def submit_thesis():
    connection = sqlite3.connect("myDatabase.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    UID = session['UID']  # Assuming you store UID after login
    
    if request.method == 'POST':
        thesis_text = request.form['thesis_text']
        
        # Insert or update the thesis and set status to 'Pending' (0)
        cursor.execute("INSERT INTO thesis (UID, thesis_text) VALUES (?, ?)", (UID, thesis_text))

        cursor.execute("UPDATE student SET thesis_status = 'Pending' WHERE UID = ?", (UID,))

        connection.commit()
        flash('Thesis submitted successfully!', 'success') 
        return redirect(url_for('submit_thesis'))

    # Fetch thesis text and approval status
    thesis = cursor.execute('SELECT thesis_text FROM thesis WHERE UID = ?', (UID,)).fetchone()
    approved = cursor.execute('SELECT thesis_status FROM student WHERE UID = ?', (UID,)).fetchone()
    connection.close()

    existing_thesis = thesis['thesis_text'] if thesis else None
    approved = approved['thesis_status'] if approved else None

    return render_template('thesis.html', existing_thesis=existing_thesis, approved=approved)


@app.route('/approve_thesis/<student_UID>', methods = ['GET', 'POST'])
def approve_thesis(student_UID):

  connection = sqlite3.connect('myDatabase.db')
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()

  cursor.execute("UPDATE student SET thesis_status = 'Approved' WHERE UID = ?", (student_UID,))

  connection.commit()
  connection.close()
  
  return redirect(url_for('student_information', student_UID = student_UID))  

@app.route('/deny_thesis/<student_UID>', methods=['GET', 'POST'])
def deny_thesis(student_UID):

    connection = sqlite3.connect('myDatabase.db')
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    # Update the thesis status to 'Denied' for the student
    cursor.execute("UPDATE student SET thesis_status = 'Denied' WHERE UID = ?", (student_UID,))
    cursor.execute("DELETE FROM thesis WHERE UID = ?", (student_UID,))
    connection.commit()
    connection.close()

    return redirect(url_for('student_information', student_UID=student_UID))

def calculate_gpa(student_UID):
  connection = sqlite3.connect('myDatabase.db')
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()

  cursor.execute("SELECT t.grade, c.credits FROM transcript t JOIN course c ON t.course_id = c.course_id WHERE t.student_uid = ?",(student_UID,))
  records = cursor.fetchall()

  grade_points = {"A": 4.0, "A-": 3.7, "B+": 3.3, "B": 3.0, "B-": 2.7, "C+": 2.3, "C": 2.0, "C-": 1.7,"D": 1.0, "F": 0.0}

  total_points = 0.0
  total_credits = 0

  for record in records:
    grade = record['grade']
    credits = record['credits']
    if grade in grade_points:
      total_points += grade_points[grade] * credits
      total_credits += credits

  connection.close()

  if total_credits == 0:
    return 0.0

  gpa = round(total_points/total_credits, 2)
  return gpa


@app.route('/handle_form1_decision/<student_UID>', methods=['POST'])
def handle_form1_decision(student_UID):
    decision = request.form.get('form1_decision')
    connection = sqlite3.connect('myDatabase.db')
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    decision = request.form.get('form1_decision')

    if decision in ['Approved', 'Rejected']:
      cursor.execute("UPDATE form1 SET status = ? WHERE UID = ?", (decision, student_UID))
      if decision == 'Approved':
        cursor.execute("")
        cursor.execute("UPDATE student SET advising_hold = FALSE WHERE UID = ?", (student_UID,))
      connection.commit()
    
    return redirect(url_for('student_information', student_UID=student_UID))

def count_low_grades(UID):
  connection = sqlite3.connect('myDatabase.db')
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()
  cursor.execute("SELECT COUNT(*) as low_grade_count FROM transcript WHERE student_uid = ? AND grade IN ('C', 'C+', 'C-', 'D', 'D+', 'D-', 'F')", (UID,))
  result = cursor.fetchone()
  connection.close()
  return result['low_grade_count']

app.run(host='0.0.0.0', port=5050, debug=True)