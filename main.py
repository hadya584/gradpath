import random
import sqlite3
import uuid
from flask import Flask, render_template, request, session, redirect, url_for, flash
from datetime import datetime
app = Flask('app')
app.secret_key = "BLOPRH"
app.debug = True

""" STUDENT ROUTES """

# Defines the home page for applicants/students
@app.route('/home', methods=['GET', 'POST'])
def home():
  # Stores role in session
  role = session.get('role')
  if not role:
    flash("You must be logged in to access this page", "error")
    return redirect('/')
  
  # Redirects to appropriate home page based on role if not applicant
  if role == 'Admin':
    return redirect(url_for('adminDashboard'))
  elif role == 'Faculty' or role == 'CAC' or role == 'GS':
    return redirect(url_for('facultyHome'))

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
              cursor.execute('UPDATE academicInformation set degree = ?, GRE_Verbal = ?, GRE_Quant = ?, GRE_Year = ?, GRE_Advanced = ?, GRE_Subject = ?, TOEFL_Score = ?, TOEFL_Date = ?, AreasOfInterest = ?, priorWorkExp = ?  WHERE UID = ?',(degree, GRE_Verbal, GRE_Quant, GRE_Year, GRE_Advanced, GRE_Subject, TOEFL_Score, TOEFL_Date, Interests, priorWorkExp, UID))
          
            # If we need to make a new table
            else:
              cursor.execute('INSERT INTO academicInformation (UID, degree, GRE_Verbal, GRE_Quant, GRE_Year, GRE_Advanced, GRE_Subject, TOEFL_Score, TOEFL_Date, areasOfInterest, priorWorkExp, transcripts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (UID, degree, GRE_Verbal, GRE_Quant, GRE_Year, GRE_Advanced, GRE_Subject, TOEFL_Score, TOEFL_Date, Interests, priorWorkExp, 1))

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
    return render_template('home.html', error=error, pastInfo=pastInfo, persInfo=persInfo, UID=UID, condition=condition, priors=priors, app=app, recLets=recLets)
    
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
        return redirect(url_for('home'))
    
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
        return redirect(url_for('home')) 

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
    if session.get('role') != 'Student':
      flash('Access denied. Student privileges required.', 'danger')
      return redirect(url_for('home'))
    
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
      session['role'] = 'Student'
      
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
      else:
        return redirect(url_for('home'))
        
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
          if role == 'Student':
            return redirect(url_for('home'))
          elif role == 'Admin':
            return redirect(url_for('adminDashboard'))
          else:
            return redirect(url_for('facultyHome'))
          
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
      
    # Get the reviewer's UID, date of review, and decision for the application from the session for documentation purposes
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
    if val not in valid_decisions:
      flash("Invalid decision value", "error")
      return redirect(f'/reviewForm/{UID}')

    # Set the score based on the decision
    if (val == 'Reject'):
      score = 0
    elif (val == 'Borderline Admit'):
      score = 1
    elif (val == 'Admit without Aid'):
      score = 2
    elif (val == 'Admit with Aid'):
      score = 3

    # Get the comments, deficiency courses, reject reason, and recommended advisor from the form
    comments = request.form.get('GAS')
    deficiency = request.form.get('Deficiency')
    rejectReason = request.form.get('rejectReason') if val == 'Reject' else None
    recommendedAdvisor = request.form.get('recommendedAdvisor')

    connection = sqlite3.connect("myDatabase.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    
    # First get all recommendation letters for this applicant
    cursor.execute("SELECT id FROM recommendationLetter WHERE UID = ?", (UID,))
    letters = cursor.fetchall()
    
    # Process and save ratings for each recommendation letter
    for letter in letters:
      letter_id = letter[0]
      rating_key = f"rating_{letter_id}"
      generic_key = f"generic_{letter_id}"
      credible_key = f"credible_{letter_id}"

      print(rating_key)
      
      rating = request.form.get(rating_key)
      
      # Validate rating if provided
      if rating and not rating.isdigit():
        flash(f"Invalid rating format for letter {letter_id}", "error")
        connection.close()
        return redirect(f'/reviewForm/{UID}')
        
      # Checkboxes will only be in request.form if checked
      is_generic = 1 if request.form.get(generic_key) else 0
      is_credible = 1 if request.form.get(credible_key) else 0
      
      print(rating)
      if rating:  # Only update if rating was provided
        print(is_generic, is_credible, letter_id)
        cursor.execute("""
          UPDATE recommendationLetter 
          SET rating = ?, isGeneric = ?, isCredible = ?
          WHERE id = ?
        """, (rating, is_generic, is_credible, letter_id))
    
    # Then insert the review form
    cursor.execute("INSERT INTO reviewForm (id, UID, reviewerUID, reviewDate, GAS_Rating, comments) VALUES (?, ?, ?, ?, ?, ?)", (None, UID, reviewerID, reviewerDate, score, comments))
    
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
    if 'connection' in locals() and 'connection' in locals():
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

  print('rows')
  for row in rows:
    print(dict(row))

  # Get all application information of the applicant
  cursor.execute("SELECT * FROM application WHERE UID = ?", (UID,))
  application = cursor.fetchone()
  
  # Fetch recommendation letters for this applicant
  cursor.execute("SELECT * FROM recommendationLetter WHERE UID = ?", (UID,))
  recommendation_letters = cursor.fetchall()

  print('reclets')
  for reclet in recommendation_letters:
    print(dict(reclet))
  
  
  connection.commit()
  connection.close()
  if (rows):
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
    return redirect(url_for('home'))
  
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

  # Build once, make it re‑iterable
  rows = list(zip(rows_taken, codes))

  connection.commit()
  connection.close()
  return render_template('facultyHome.html', rows = rows, session = session) # For faculty, we want to put some if statements here

# Defines a route for faculties to view a specific applicant's reviews and write a new review
@app.route('/reviewForm/<UID>', methods=['GET', 'POST'])
def reviewForm(UID):
  if session.get('role') != 'Faculty' and session.get('role') != 'GS' and session.get('role') != 'CAC':
    flash('Access denied. Faculty privileges required.', 'danger')
    return redirect(url_for('home'))
  
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

  connection.commit()
  connection.close()

  if request.method == 'POST':
    connection = sqlite3.connect("myDatabase.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    decision = request.form.get('decision')
    if (decision == 'Admit without Aid' or decision == 'Admit with Aid'):
      cursor.execute("UPDATE application SET applicationStatus = ?, decisionType = ? WHERE UID = ?", ('Admitted', decision, UID))
    elif (decision == 'Reject'):
      cursor.execute("UPDATE application SET applicationStatus = ?, decisionType = ? WHERE UID = ?", ('Rejected', decision, UID))
    
    for reclet in recommendationLetters:
      letter_id = reclet['id']  # Extract the letter ID
      rating_key = f"rating_{letter_id}"  # Dynamically generate the key
      generic_key = f"generic_{letter_id}"
      credible_key = f"credible_{letter_id}"

        # Retrieve values from the form
      rating = request.form.get(rating_key)
      isgeneric = 1 if request.form.get(generic_key) else 0
      iscredible = 1 if request.form.get(credible_key) else 0
      
      cursor.execute("UPDATE recommendationLetter SET rating = ?, isGeneric = ?, isCredible = ? WHERE id = ?", (rating, isgeneric, iscredible, letter_id))


    connection.commit()
    connection.close()
    flash("Review submitted successfully", "success")
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
    return redirect('/home') #You should not be here...

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
    return redirect(url_for('home'))
  
  # Get all applicants, faculties, GS, and CAC
  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()
  cursor.execute("SELECT * FROM user WHERE role = 'Student'")
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

# Defines a route for admins to create a new user
@app.route('/create-user', methods=['POST'])
def create_user():
  # Check if user is admin
  if session.get('role') != 'Admin':
    flash('Access denied. Admin privileges required.', 'danger')
    return redirect(url_for('home'))
    
  connection = sqlite3.connect("myDatabase.db")
  connection.row_factory = sqlite3.Row
  cursor = connection.cursor()
  
  # Get form data
  uid = request.form.get('newUID')
  password = request.form.get('newPassword')
  role = request.form.get('newRole')
  
  # Generate UID if not provided
  if not uid:
    # Generate a unique UID using uuid
    while True:
      # Generate a random UUID and use the first 8 digits
      uid = str(uuid.uuid4().int)[:8]
      cursor.execute("SELECT * FROM user WHERE UID = ?", (uid,))
      if not cursor.fetchone():
        break
  
  try:
    # Insert new user
    cursor.execute("INSERT INTO user (UID, role, password) VALUES (?, ?, ?)", 
                  (uid, role, password))
    connection.commit()
    flash(f"User created successfully with UID: {uid}", "success")
  except sqlite3.Error as e:
    connection.rollback()
    flash(f"Error creating user: {str(e)}", "danger")
  finally:
    connection.close()
  
  return redirect(url_for('adminDashboard'))

# Defines a route for admins to edit an existing user
@app.route('/edit-user/<uid>', methods=['GET', 'POST'])
def edit_user(uid):
  # Check if user is admin
  if session.get('role') != 'Admin':
    flash('Access denied. Admin privileges required.', 'danger')
    return redirect(url_for('home'))
    
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
    return redirect(url_for('home'))
  
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
    return redirect(url_for('home'))
    
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
# - Applicants: There must be two applicants entered into the system with the student numbers and other
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
  cursor.execute("INSERT INTO user (UID, role, password, firstName, lastName, ssn, email, phone, address, address2) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ('12312312', 'Student', 'pass', 'John', 'Lennon', '111-11-1111', 'lennon@gmail.com', '111-867-5309', 'Address #1', 'Address #2')) #John Lennon
  cursor.execute("INSERT INTO academicInformation (UID, degree, GRE_Verbal, GRE_Quant, GRE_Year, GRE_Advanced, GRE_Subject, TOEFL_Score, TOEFL_Date, areasOfInterest, priorWorkExp, transcripts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ('12312312', 'MS', '140', '150', '1969', None, None, '115', '1969-04-12', 'some cool interest', 'He worked here', 'transcripts'))
  cursor.execute("INSERT INTO application (UID, applicationStatus, applySemester, applyYear, decisionType, recommendedAdvisor, deficiencyCourses, rejectReason, finalDecisionDate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", ('12312312', 'Complete and Under Review', 'Spring', '2024', None, None, None, None, None))
  cursor.execute("INSERT INTO priorDegree (id, UID, degreeName, institution, major, GPA, year) VALUES (?, ?, ?, ?, ?, ?, ?)", (None, '12312312', 'BS', 'University A', 'Math', 3.8, '1968'))
  cursor.execute("INSERT INTO recommendationLetter (id, UID, writerName, writerEmail, writerAffiliation, letter, submissionDate, token, status, rating, isGeneric, isCredible) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (None, '12312312', 'Professor Bleepy', 'Bleepy@gwu.edu', 'BLEEP', 'HERE IS A LETTER', '1968-10-15','token1', 'Pending', 1, 1, 1))
  
  #Ringo Starr's incomplete application
  cursor.execute("INSERT INTO user (UID, role, password, firstName, lastName, ssn, email, phone, address, address2) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ('66666666', 'Student', 'pass', 'Ringo', 'Starr', '222-11-1111', 'starr@gmail.com', '101-010-1010', 'Address #1', 'Address #2')) 

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

if __name__ == "__main__":
  app.run(debug=True)