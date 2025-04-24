'''
To reset the database, run this command in the Shell: 
  sqlite3 myDatabase.db ".read store_schema.sql"
'''

import sqlite3
from flask import Flask, session, render_template, redirect, url_for, request, flash
import random

app = Flask('app')
app.debug = True
app.secret_key = "CHANGE"

@app.route('/home', methods=['GET', 'POST'])
def home():
  if 'email' not in session:
    return redirect('/')
  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()
  if session['role'] == 'student':
    cursor.execute("SELECT UID FROM student JOIN user ON student.UID = user.UID WHERE user.email = ?", (session['email'],))
    student_UID = cursor.fetchone()
    id = student_UID[0]
    GPA = calculate_gpa(id)
    cursor.execute("UPDATE student SET GPA = ? WHERE UID = ?",(GPA, id))
    low_grade_count = count_low_grades(id)
    if low_grade_count >= 3:
      connection.commit()
      connection.close()
      return render_template("login.html", error = False, is_suspended = True)
  else:
    id = session['UID']
  connection.commit()
  connection.close()

  return render_template('home.html', role = session['role'], fname = session['fname'], lname = session['lname'], id = id)

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
  if 'email' not in session:
    return redirect (url_for('login'))

  #connect to db 
  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()

  # Get student info including advisor_id
  cursor.execute("SELECT UID, program, advisor_id FROM student WHERE UID = ?", (session['UID'],))
  student = cursor.fetchone()
  program = student['program']
  advisor_id = student['advisor_id']

  # Check if advisor_id is NULL (i.e., no advisor assigned)
  if advisor_id is None:
    connection.close()
    flash("You must have an advisor assigned before submitting Form 1.", "warning")
    return redirect(url_for('home'))  # Change 'homepage' to your actual homepage/dashboard route
  
  #to display all courses 
  cursor.execute("SELECT * FROM course")
  rows = cursor.fetchall()

  #get current student UID from their email - will be used for form1 submission 
  cursor.execute("SELECT student.UID, student.program FROM student JOIN user on student.UID = user.UID WHERE user.email = ?", (session['email'],))
  student = cursor.fetchone()
  UID = student['UID']
  program = student['program']

  #when form is submitted 
  if request.method == 'POST':
    # Check if the student already has a submitted form1
    cursor.execute("SELECT form1_id FROM form1 WHERE UID = ? AND status = 'Submitted'", (UID,))
    existing_form1 = cursor.fetchone()

    if existing_form1:
      #if form 1 exists update it
      form1_id = existing_form1['form1_id']
      cursor.execute("UPDATE form1 SET status = 'Submitted' WHERE form1_id = ?", (form1_id,))
      #clear existing courses before inserting new ones
      cursor.execute("DELETE FROM form1_course WHERE form1_id = ?", (form1_id,))
    else:
      #if no exisiting form new form1 for student withh their uid, and status changed to submitted
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
          return render_template("form1error.html") #direct to error page which will bring them back to form1 
        selected.append(course_id) #if it hasnt been selected already, add it to the list for db 
        cursor.execute("INSERT INTO form1_course (form1_id, course_id) VALUES (?, ?)", (form1_id, course_id))

    connection.commit()
    connection.close()
    return render_template("submitted.html") 

  connection.commit()
  connection.close
  return render_template("form1.html",  fname = session['fname'], courses = rows, program = program)

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
  if 'email' not in session:
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
  thesis_approved = False
  if userdata and userdata['thesis_status'] == 'Complete':
    thesis_approved = True

  # TRANSCRIPT INFO
  coursedetails = []
  cursor.execute("SELECT course.dept, course.course_num, course.title, course.credits, transcript.semester, transcript.year, transcript.grade, course.course_id FROM transcript JOIN course ON transcript.course_id = course.course_id JOIN student ON transcript.student_uid = student.UID WHERE student.UID = ?", (student_UID,))
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

  low_grade_count = count_low_grades(student_UID)
  if low_grade_count >= 3:
    connection.commit()
    connection.close()
    return render_template("student_info.html", userdata = userdata, is_cleared = is_cleared, role = session['role'], transcriptcourses = coursedetails, student_UID = student_UID,  form1_submitted = form1_submitted, form1_status = form1_status, thesis_approved = thesis_approved, facultydata = facultydata, is_suspended = True)
      
  connection.commit()
  connection.close()

  return render_template("student_info.html", userdata = userdata, is_cleared = is_cleared, role = session['role'], transcriptcourses = coursedetails, student_UID = student_UID,  form1_submitted = form1_submitted, form1_status = form1_status, thesis_approved = thesis_approved, facultydata = facultydata, is_suspended = False)

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

@app.route('/apply_graduation', methods = ['GET', 'POST'])
def apply_graduation():
  # make sure student is applying
  connection = sqlite3.connect('myDatabase.db')
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()


  cursor.execute("SELECT student.UID, student.program, student.GPA, student.thesis_status FROM student JOIN user ON student.UID = user.UID WHERE user.email = ?", (session['email'],))
  userdata = cursor.fetchone()
  UID = userdata['UID']
  grad_type = userdata['program']
  GPA = userdata['GPA']
  thesis_status = userdata['thesis_status']

  #check if student already applied
  cursor.execute("SELECT * FROM applied_for_grad WHERE UID = ? AND cleared = 'Cleared'",(UID,))
  applied = cursor.fetchone()
  #if already applied
  if applied is not None:
    return render_template("applied.html", cleared = False, error = None, already_applied = True)

  #check if form courses match transcript
  # get form 1 course IDs
  cursor.execute("SELECT course_id FROM form1_course JOIN form1 ON form1_course.form1_id = form1.form1_id WHERE form1.UID = ?", (UID,))
  form1_course_rows = cursor.fetchall()
  form1_courses = []
  for row in form1_course_rows:
    form1_courses.append(row['course_id'])

  # get transcript course IDs
  cursor.execute("SELECT course_id FROM transcript WHERE student_uid = ?", (UID,))
  transcript_course_rows = cursor.fetchall()
  transcript_courses = []
  for row in transcript_course_rows:
    transcript_courses.append(row['course_id'])

  #compare courses
  if len(form1_courses) != len(transcript_courses):
    audit_passed = False
    return render_template("applied.html", cleared=audit_passed, error = 'not_matching', already_applied = False)
  else:
    for course in form1_courses:
      if course not in transcript_courses:
        audit_passed = False
        return render_template("applied.html", cleared=audit_passed, error = 'not_matching', already_applied = False) # form 1 doesnt match transcript

  #check if advisor approved
  cursor.execute("SELECT status FROM form1 WHERE UID = ?", (UID,))
  form1 = cursor.fetchone()
  if form1:
    form1_submit = form1['status']
  else:
    form1_submit = None

  if form1_submit != 'Approved':
    return render_template("applied.html", cleared = False, error = 'form1_not_approved', already_applied = False) # advisor did not approve form 1

  audit_passed = True
  # check requirements
  if grad_type == 'Masters':
    req_status = ms_requirements(UID)
    if GPA < 3.00:
      audit_passed = False
    if req_status == False:
      audit_passed = False  
    
  elif grad_type == 'PhD':
    req_status = phd_requirements(UID)
    if GPA < 3.50:
      audit_passed = False
    if req_status == False:
      audit_passed = False
    if thesis_status == 'Incomplete':
      return render_template("applied.html", cleared = False, error = 'thesis_not_approved', already_applied = False) # advisor did not approve thesis

  if form1_submit != 'Approved':
    audit_passed = False

  if audit_passed:
    #add to cleared student and applied student
    cursor.execute("INSERT INTO applied_for_grad (UID, cleared) VALUES (?,?)", (UID, 'Cleared'))
  else:
    #add to applied student
    cursor.execute("INSERT INTO applied_for_grad (UID, cleared) VALUES (?,?)", (UID, 'Not Cleared'))
   
  connection.commit()
  connection.close()
  
  return render_template("applied.html", cleared = audit_passed, error = None, already_applied = False)

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
    cursor.execute("SELECT faculty.UID FROM faculty JOIN user ON faculty.UID = user.UID WHERE faculty.UID = ?",(session['UID'],))
    facultyData = cursor.fetchone()
    UID = facultyData['UID']
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
  return redirect (url_for('home')) 

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

  cursor.execute("SELECT course.course_id, course.title, course.dept, course.course_num FROM form1 JOIN form1_course ON form1.form1_id = form1_course.form1_id JOIN course on form1_course.course_id = course.course_id WHERE form1.UID = ?", (student_UID,))
  form1courses = cursor.fetchall()

  is_form1courses = True
  if form1courses == None:
    is_form1courses = False

  cursor.execute("SELECT user.firstName, user.lastName, user.email, student.UID FROM user JOIN student ON user.UID = student.UID WHERE student.UID = ?", (student_UID,))
  userdata = cursor.fetchone()
    
  connection.commit()
  connection.close()

  return render_template("form1submission.html", form1courses = form1courses, is_form1courses = is_form1courses, userdata = userdata, role = session['role'])


@app.route('/approve_thesis/<student_UID>', methods = ['GET', 'POST'])
def approve_thesis(student_UID):
  # # make sure secretary
  # if 'UID' not in session:
  #   return redirect('/')
  
  connection = sqlite3.connect('myDatabase.db')
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()

  cursor.execute("UPDATE student SET thesis_status = 'Complete' WHERE UID = ?", (student_UID,))

  connection.commit()
  connection.close()
  
  return redirect(url_for('student_information', student_UID = student_UID))  

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

app.run(host='0.0.0.0', port=8080)