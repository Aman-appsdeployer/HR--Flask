import os
import datetime
import smtplib
from collections import namedtuple
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask_bcrypt import Bcrypt 
import mysql.connector
import pandas
import bcrypt

from flask import (Flask, jsonify, redirect, render_template, request,

                   send_file, session, url_for)

from PyPDF2 import PdfFileReader, PdfFileWriter
from flask import flash

from flask_mail import Mail, Message
from flask import request, render_template_string
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

# Create a Flask web application
app = Flask(__name__)
app.secret_key = 'anything_info'  # Replace with your actual secret key

# Establish a connection to the database
db = mysql.connector.connect(
    host='localhost',
    user='root',
    password='1234@aman',
    database='registration',
    auth_plugin='mysql_native_password'
)
# Define a function to hash a password
def hash_password(password):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_password

# Function to verify a password
def verify_password(hashed_password, password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)
def get_database_connection():
    return mysql.connector.connect(**db)

def close_database_connection(connection, cursor):
    cursor.close()
    connection.close()

cursor = db.cursor()

# Define a function to create the database table
def create_onboards_table():
    cursor.execute('''
       CREATE TABLE IF NOT EXISTS regis (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255),
            last_name VARCHAR(255),
            address VARCHAR(255),
            mobile_number VARCHAR(20),
            alternate_mobile_number VARCHAR(20),
            alternate_address VARCHAR(255),
            date_of_birth DATE,
            date_of_joining DATE,
            date_of_registration DATE,
            last_working_day DATE,
            qualifications VARCHAR(255),
            experience VARCHAR(255),
            username VARCHAR(50),
            password VARCHAR(255),
            login_count INT DEFAULT 0,
            salary_pdf_path VARCHAR(255)
        )
    ''')

# Create an empty list for regularization requests
regularization_requests = []

# Define the root route
@app.route('/')
def index():
    return render_template('login.html')
# Function to fetch hashed password from the database
def fetch_hashed_password(username):
    cursor = db.cursor()
    try:
        cursor.execute('SELECT password FROM regis WHERE username = %s', (username,))
        result = cursor.fetchone()
        if result:
            hashed_password = result[0]
            return hashed_password
        else:
            return None
    except mysql.connector.Error as error:
        print("Error fetching hashed password:", error)
    finally:
        cursor.close()

# Define a route for user registration
@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register_post():
    # Retrieve form data
    name = request.form['name']
    last_name = request.form['last_name']
    username = request.form['username']
    password = request.form['password']
    mobile = request.form['mobile']
    alternate_mobile = request.form['alternate_mobile']
    address = request.form['address']
    alternate_address = request.form['alternate_address']
    dob = request.form['dob']
    qualifications = request.form['qualifications']
    experience = request.form['experience']
    doj = request.form['doj']
    dor = request.form['dor']
    last_working_day = request.form['last_working_day']

    # Hash the password before storing it
    hashed_password = hash_password(password)

    cursor = db.cursor()
    try:
        cursor.execute('INSERT INTO regis (name, last_name, address, mobile_number, alternate_mobile_number, alternate_address, date_of_birth, date_of_joining, date_of_registration, last_working_day, qualifications, experience, username, password) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                       (name, last_name, address, mobile, alternate_mobile, alternate_address, dob, doj, dor, last_working_day, qualifications, experience, username, hashed_password))
        db.commit()
        cursor.close()
        return render_template('login.html', success_msg="Registration successful! Please log in.")
    except mysql.connector.Error as error:
        print("Error registering user:", error)
        return render_template('login.html', error_msg="An error occurred while registering user.")

# Define a route for user login
@app.route('/login', methods=['POST'])
def login_post():
    username = request.form['username']
    password = request.form['password']

    # Fetch hashed password from the database
    hashed_password_str = fetch_hashed_password(username)

    if hashed_password_str:
        # Convert the hashed password string to bytes
        hashed_password_bytes = hashed_password_str.encode('utf-8')

        # Verify the entered password against the hashed password
        if verify_password(hashed_password_bytes, password):
            # Password is correct, login successful
            cursor = db.cursor()
            cursor.execute('SELECT * FROM regis WHERE username = %s AND password = %s', (username, hashed_password_str))
            user = cursor.fetchone()
            cursor.close()

            if user:
                session['user_id'] = user[0]

                cursor = db.cursor()
                cursor.execute('UPDATE regis SET login_count = login_count + 1 WHERE id = %s', (user[0],))
                db.commit()
                cursor.close()

                return redirect('/dashboard')
        else:
            error_msg = 'Invalid username or password. Please try again.'
            return render_template('login.html', error_msg=error_msg)
    else:
        error_msg = "User not found. Please register if you haven't already."
        return render_template('login.html', error_msg=error_msg)
    

# Define the dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user_id = session['user_id']
        cursor = db.cursor()
        cursor.execute('SELECT username, login_count FROM regis WHERE id = %s', (user_id,))
        user = cursor.fetchone()

        if user:
            username = user[0]
            login_count = user[1]
            
            if user_id == 12 or user_id == 13:
                # Fetch registration details 
                df = pandas.read_sql_query('SELECT * FROM regis', db)
                pandas.set_option('colheader_justify', 'center')   # For creating table headers
                
                return render_template('dashboard.html', admin_access=True, user_table=df.to_html(classes='mystyle'))

            # Fetch registration details of the logged-in user
            cursor.execute('SELECT name, last_name, address, mobile_number, alternate_mobile_number, alternate_address, date_of_birth, date_of_joining, date_of_registration, last_working_day, qualifications, experience FROM regis WHERE id = %s', (user_id,))
            registration_details = cursor.fetchone()
            cursor.close()

            return render_template('dashboard_user.html', username=username, login_count=login_count, registration_details=registration_details)

    return redirect('/')



# -----salary slips start  ------- #
# def generate_salary_slip(user_id, user_name, user_last_name):
#     cursor.execute('SELECT name, last_name, qualifications, experience FROM regis WHERE id = %s', (user_id,))
#     user_data = cursor.fetchone()

#     # Calculate salary (replace with your logic)
#     basic_salary = 5000
#     housing_allowance = 1000
#     transportation_allowance = 500
#     gross_salary = basic_salary + housing_allowance + transportation_allowance
#     tax_deduction = 200
#     insurance_deduction = 50
#     net_salary = gross_salary - tax_deduction - insurance_deduction

#     pdf_filename = f'{user_name}_{user_last_name}_salary_slip.pdf'
#     pdf_dir = 'path/to/salary_slips'  # Update to actual directory path
#     pdf_path = os.path.join(pdf_dir, pdf_filename)

#     os.makedirs(pdf_dir, exist_ok=True)

#     doc = SimpleDocTemplate(pdf_path, pagesize=letter)

#     # Create a list to store the data for the table
#     data = [
#         ["Description", "Amount"],
#         ["Basic Salary", basic_salary],
#         ["Housing Allowance", housing_allowance],
#         ["Transportation Allowance", transportation_allowance],
#         ["Gross Salary", gross_salary],
#         ["Tax Deduction", tax_deduction],
#         ["Insurance Deduction", insurance_deduction],
#         ["Net Salary", net_salary]
#     ]

#     # Create a table and style it
#     table = Table(data, colWidths=[200, 100])
#     style = TableStyle([
#         ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
#         ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#         ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#         ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
#         ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
#         ('GRID', (0, 0), (-1, -1), 1, colors.black)
#     ])
#     table.setStyle(style)

#     # Build the PDF document
#     elements = []
#     elements.append(table)
#     doc.build(elements)

#     return pdf_path, pdf_filename
def generate_salary_slip(user_id, user_name, user_last_name):
    try:
        cursor.execute('SELECT name, last_name, qualifications, experience FROM regis WHERE id = %s', (user_id,))
        user_data = cursor.fetchone()

        # Calculate salary (replace with your logic)
        basic_salary = 5000
        housing_allowance = 1000
        transportation_allowance = 500
        gross_salary = basic_salary + housing_allowance + transportation_allowance
        tax_deduction = 200
        insurance_deduction = 50
        net_salary = gross_salary - tax_deduction - insurance_deduction

        pdf_filename = f'{user_name}_{user_last_name}_salary_slip.pdf'
        pdf_dir = 'path/to/salary_slips'  # Update to actual directory path
        pdf_path = os.path.join(pdf_dir, pdf_filename)

        os.makedirs(pdf_dir, exist_ok=True)

        doc = SimpleDocTemplate(pdf_path, pagesize=letter)

        # Create a list to store the data for the table
        data = [
            ["Description", "Amount"],
            ["Basic Salary", basic_salary],
            ["Housing Allowance", housing_allowance],
            ["Transportation Allowance", transportation_allowance],
            ["Gross Salary", gross_salary],
            ["Tax Deduction", tax_deduction],
            ["Insurance Deduction", insurance_deduction],
            ["Net Salary", net_salary]
        ]

        # Create a table and style it
        table = Table(data, colWidths=[200, 100])
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
        table.setStyle(style)

        # Build the PDF document
        elements = []
        elements.append(table)
        doc.build(elements)

        return pdf_path, pdf_filename
    except Exception as e:
        print("Error generating salary slip:", e)
        return None, None

# Define a route to download salary slips
@app.route('/download')

def download():
    # Retrieve user data from the database 
    cursor.execute('SELECT id, name, salary_pdf_path FROM regis')
    users_data = cursor.fetchall()

    # Convert the data into a named tuple
    User = namedtuple('User', ['id', 'name', 'salary_pdf_path'])
    users = [User(*record) for record in users_data]

    return render_template('download.html', users=users)
# Define a route to generate salary slips
# @app.route('/generate_salary', methods=['POST'])
# def generate_salary():
#     if 'user_id' in session:
#         cursor.execute('SELECT id, name, last_name FROM regis')
#         all_user_data = cursor.fetchall()

#         for user_data in all_user_data:
#             user_id = user_data[0]
#             user_name = user_data[1]
#             user_last_name = user_data[2]

#             pdf_path, pdf_filename = generate_salary_slip(user_id, user_name, user_last_name)
#             cursor.execute('UPDATE regis SET salary_pdf_path = %s WHERE id = %s', (pdf_filename, user_id))
#             db.commit()

#         return jsonify(success=True)
#     else:
#         return jsonify(success=False, error='User not logged in')

@app.route('/generate_salary', methods=['POST'])
def generate_salary():
    try:
        if 'user_id' in session:
            cursor.execute('SELECT id, name, last_name FROM regis')
            all_user_data = cursor.fetchall()

            for user_data in all_user_data:
                user_id = user_data[0]
                user_name = user_data[1]
                user_last_name = user_data[2]

                pdf_path, pdf_filename = generate_salary_slip(user_id, user_name, user_last_name)
                if pdf_path and pdf_filename:
                    cursor.execute('UPDATE regis SET salary_pdf_path = %s WHERE id = %s', (pdf_filename, user_id))
                    db.commit()

            return jsonify(success=True)
        else:
            return jsonify(success=False, error='User not logged in')
    except Exception as e:
        print("Error generating salary slips:", e)
        return jsonify(success=False, error='An error occurred while generating salary slips')


# Define a route to download salary slip
# @app.route('/download_salary_slip/<int:user_id>')
# def download_salary_slip(user_id):
#     cursor.execute('SELECT salary_pdf_path FROM regis WHERE id = %s', (user_id,))
#     result = cursor.fetchone()

#     if result and result[0]:
#         pdf_file_path = os.path.join('path/to/salary_slips/', result[0])
#         return send_file(pdf_file_path, as_attachment=True)
#     else:
#         return "File not found"

@app.route('/download_salary_slip/<int:user_id>')
def download_salary_slip(user_id):
    try:
        cursor.execute('SELECT salary_pdf_path FROM regis WHERE id = %s', (user_id,))
        result = cursor.fetchone()

        if result and result[0]:
            pdf_file_path = os.path.join('path/to/salary_slips/', result[0])
            return send_file(pdf_file_path, as_attachment=True)
        else:
            return "File not found"
    except Exception as e:
        print("Error downloading salary slip:", e)
        return "An error occurred while downloading salary slip"



# ----------   Salary slip end ------- #

# Define a route to submit regularization requests
@app.route('/submit_regularization', methods=['POST'])
def submit_regularization():
    if request.method == 'POST':
        date = request.form['date']
        login_time = request.form['login_time']
        logout_time = request.form['logout_time']
        reason = request.form['reason']

        # Store the regularization request (you would save this to your database)
        regularization_requests.append({
            'date': date,
            'login_time': login_time,
            'logout_time': logout_time,
            'reason': reason,
        })

        return "Request submitted for approval"
# Define a route to log out the user
@app.route('/logout', methods=['POST'])
def logout():
    if 'user_id' in session:
        session.pop('user_id', None)
        return render_template('logout.html', username='Unknown')
    else:
        return redirect('/')

# Your Gmail account credentials
gmail_user = 'amangt9526@gmail.com'
gmail_password = 'qilr lbxa aqdf lqpi'

# Define a route to report an issue via email

@app.route('/issue', methods=['GET', 'POST'])
def issue():
    if request.method == 'POST':
        your_name = request.form['your_name']
        to_email = request.form['to_email']
        subject = request.form['subject']
        body = request.form['body']

        try:
            smtp_server = 'smtp.gmail.com'
            smtp_port = 587
            smtp_connection = smtplib.SMTP(smtp_server, smtp_port)
            smtp_connection.starttls()
            smtp_connection.login(gmail_user, gmail_password)

            message = MIMEMultipart()
            message['From'] = gmail_user
            message['To'] = to_email
            message['Subject'] = subject
            message.attach(MIMEText(f'Hello {your_name},\n\n{body}', 'plain'))

            smtp_connection.sendmail(gmail_user, to_email, message.as_string())
            smtp_connection.quit()

            return "Email sent successfully!"
        except Exception as e:
            return f"An error occurred: {str(e)}"
    return render_template('issue.html')

# Define a function to create the attendance regularization table
def create_attendance_regularization_table():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance_regularization (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            regularization_date DATE,
            FOREIGN KEY (user_id) REFERENCES regis(id)
        )
    ''')

# Call the function to create the table
admin_ids = [12]
# Your Team Leader/HR IDs
team_leader_hr_ids = [13]

# Define a route for leave approval list

from flask import session, render_template, redirect
from collections import namedtuple

@app.route('/leave_approval_list')
def leave_approval_list():
    if 'user_id' in session and session['user_id'] in team_leader_hr_ids:
        # Initialize database cursor
        cursor = db.cursor()
        
        # Fetch leave requests from the database
        cursor.execute('SELECT id, employee_name, leave_type, start_date, end_date, email FROM leaves')
        leave_requests_data = cursor.fetchall()
        
        # Convert the data into a named tuple
        LeaveRequest = namedtuple('LeaveRequest', ['id', 'employee_name', 'leave_type', 'start_date', 'end_date', 'email'])
        leave_requests = [LeaveRequest(*record) for record in leave_requests_data]

        # Close cursor after use
        cursor.close()

        return render_template('leave_approval_list.html', leave_requests=leave_requests)
    else:
        return redirect('/')

#     return render_template('attendance_regularization.html')
# ------------- Assets pannel start ----------#
@app.route('/Assets_Mangement')
def Assets_Mangement():
    return render_template('Assets_Mangement.html') 
# ------------- Assets pannel end  ----------#

# ------------- On Boarding pannel start ----------#
@app.route('/on_boarding')
def on_boarding():
    return render_template('on_boarding.html') 

#---attendance_regularization ---- #
@app.route('/attendance_regularization')
def attendance_regularization():
    return render_template('attendance_regularization.html') 

# ------------- On Boarding pannel end  ----------#

# ------------- OF Boarding pannel start ----------#
@app.route('/offboarding')
def OF_boarding():
    return render_template('offboarding.html') 

@app.route('/joining', methods=['GET','POST'])
def joining():
    try:
        # Create a cursor to execute queries
        cursor = db.cursor(dictionary=True)

        # Fetch resignation details from the database
        cursor.execute("SELECT * FROM resignations")
        resignation_details = cursor.fetchall()

        # Close the cursor (do not close the connection here)
        cursor.close()

        return render_template('joining.html', resignations=resignation_details)
    except mysql.connector.Error as error:
        # Handle database errors
        print("Error fetching resignation details:", error)
        return "An error occurred while fetching resignation details", 500
# ------------- OF Boarding pannel end  ----------#

# ------------- Insurances start ----------#
@app.route('/on_Insurance')
def insurance():
    return render_template('insurance.html') 
# ------------- Insurance end  ----------#


#------ Assets Life Cycle------#
@app.route('/asset-life')
def assets_life():
    return render_template('assets_life.html')

# ------------Assets Assining------- #

@app.route('/assing_assets')
def assing_assets():
    return render_template('assing_assets.html')


#------  Latter    ------#
@app.route('/On_latter')
def On_latter():
    return render_template('On_latter.html')


@app.route('/users_del')
def users():
    try:
        # Create a cursor to execute queries
        cursor = db.cursor(dictionary=True)

        # Fetch resignation details from the database
        cursor.execute("SELECT * FROM regis")
        users = cursor.fetchall()

        # Close the cursor (do not close the connection here)
        cursor.close()

        return render_template('users_del.html', user_details=users)
    except mysql.connector.Error as error:
        # Handle database errors
        print("Error fetching resignation details:", error)
        return "An error occurred while fetching resignation details", 500
    
@app.route('/accept_form', methods=['POST'])
def accept_form():
    try:
        email = request.form['email']  # Assuming 'email' is the name attribute of the input field in your form

        # Email configuration
        sender_email = 'amangt9526@gmail.com'
        receiver_email = email
        password = 'qilr lbxa aqdf lqpi'
        
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = receiver_email
        message['Subject'] = 'Form Accepetd'

        body = 'Your form request has been accepted. Please send your documnnt on this link - https://docs.google.com/forms/d/11U-QOx5t8yupvTmzyxyMB0vgnCFb8ByK1gBB3n62Zz4/edit?usp=drivesdk'
        message.attach(MIMEText(body, 'plain'))

        # Send the email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:  # Replace 'smtp.example.com' with your SMTP server
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())

        return 'Email sent successfully'
    except Exception as e:
        return 'Error sending email: ' + str(e)

#---- resign -----#
@app.route('/resignation_form')
def resignation_form():
    return render_template('resign_on.html')

# Route to handle form submission

@app.route('/submit_resignation', methods=['POST'])
def submit_resignation():
    # Extract form data
    name = request.form['name']
    email = request.form['email']
    position = request.form['position']
    reason = request.form['reason']
    assets_taken = request.form['assets_taken']
    assets_list = request.form.get('assets_list', '')  # Optional field, default to empty string

    try:
        # Use the existing database connection object
        cursor = db.cursor()

        # Insert resignation details into the database
        sql = "INSERT INTO resignations (name, email, position, reason, assets_taken, assets_list) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, (name, email, position, reason, assets_taken, assets_list))
        db.commit()

        # Close cursor (connection remains open for future use)
        cursor.close()

        # Redirect to user dashboard or any other page
        return redirect('/dashboard_user')
    except mysql.connector.Error as error:
        # Handle database errors
        print("Error inserting into MySQL table:", error)
        return "An error occurred while processing your request", 500

#HR OFFBOARD PAGE
    
@app.route('/F_boarding')
def offboarding_page():
    try:
        # Create a cursor to execute queries
        cursor = db.cursor(dictionary=True)

        # Fetch resignation details from the database
        cursor.execute("SELECT * FROM resignations")
        resignation_details = cursor.fetchall()

        # Close the cursor (do not close the connection here)
        cursor.close()

        return render_template('F_boarding.html', resignations=resignation_details)
    except mysql.connector.Error as error:
        # Handle database errors
        print("Error fetching resignation details:", error)
        return "An error occurred while fetching resignation details", 500

 # MAIL
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Replace with your SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'amangt9526@gmail.com'
app.config['MAIL_PASSWORD'] = 'qilr lbxa aqdf lqpi'
app.config['MAIL_DEFAULT_SENDER'] = 'amangt9526@gmail.com'
mail = Mail(app)

@app.route('/accept_resignation', methods=['POST'])
def accept_resignation():
    resignation_id = request.form.get('resignation_id')
    email = request.form.get('email')

    try:
        # Re-establish the connection and create a new cursor
        cursor = db.cursor()

        # Update the status of the resignation in the database to "accepted"
        cursor.execute("UPDATE resignations SET status = 'accepted' WHERE id = %s", (resignation_id,))
        db.commit()

        # Close the cursor
        cursor.close()

        # Send an email notification to the employee
        subject = "Your resignation has been accepted"
        message = "Dear Employee,\n\nYour resignation has been accepted. We wish you the best in your future endeavors."
        send_email(email, subject, message)

        return redirect(url_for('offboarding_page'))
    except mysql.connector.Error as error:
        # Handle database errors
        print("Error accepting resignation:", error)
        return "An error occurred while accepting resignation", 500


def send_email(to_email, subject, message):
    # Configure SMTP server details
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    SMTP_USERNAME = 'amangt9526@gmail.com'
    SMTP_PASSWORD = 'qilr lbxa aqdf lqpi'

    try:
        # Create a connection to the SMTP server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)

        # Construct the email message
        email_message = f"Subject: {subject}\n\n{message}"

        # Send the email
        server.sendmail(SMTP_USERNAME, to_email, email_message)

        # Close the connection
        server.quit()
    except smtplib.SMTPAuthenticationError as auth_error:
        # Handle authentication errors
        print("SMTP Authentication Error:", auth_error)
    except Exception as e:
        # Handle other email sending errors
        print("Error sending email:", e)

#---- Leave --- #
# Route to render the leave request form
@app.route('/leave_request_form')
def leave_request_form():
    return render_template('leave_request_form.html')

# Route to handle form submission
@app.route('/submit_leave', methods=['POST'])
def submit_leave():
    try:
        # Extract form data
        employee_name = request.form['employeeName']
        employee_email = request.form['employeeMail']
        leave_type = request.form['leaveType']
        start_date = request.form['startDate']
        end_date = request.form['endDate']
        
        # Insert the form data into the leaves table
        cursor = db.cursor()
        insert_query = "INSERT INTO leaves (employee_name, email, leave_type, start_date, end_date) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(insert_query, (employee_name, employee_email, leave_type, start_date, end_date))
        db.commit()
        cursor.close()

        return 'Leave request submitted successfully!'
    except Exception as e:
        return f"An error occurred: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)

