
from mailbox import Mailbox, Message
from flask_mail import Mail, Message
import zipfile
from flask import Flask, Response, jsonify, redirect, request, render_template, send_file, send_from_directory, session, url_for
import smtplib
import ssl
import os
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from werkzeug.utils import secure_filename
import mysql.connector
from datetime import datetime, timezone
from io import BytesIO
db_config: dict = {
    'host': 'localhost',
    'user': 'root',
    'password': 'divya',
    'database': 'mydb'
}
def connect_to_database():
    return mysql.connector.connect(**db_config)
# Specify the upload folder
UPLOAD_FOLDER = r"C:\Users\Murugesan\Downloads\static\static"
ALLOWED_EXTENSIONS = {'pdb'}
app = Flask(__name__)

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'testdivya368@gmail.com'
app.config['MAIL_PASSWORD'] = 'brcq gkuv uwri dcwk'

# Initialize Flask-Mail
mail = Mail(app)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'key'
def to_datetime(value, format='%Y-%m-%d %H:%M:%S'):
    dt = datetime.strptime(value, format)
    return dt.replace(tzinfo=timezone.utc)
def allowed_file(filename):
    return '.' in filename and filename.lower().rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
@app.route('/receive-file', methods=['POST'])
def receive_file():
    try:
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            email = request.form.get('email')  # Get the email address from the form

            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Convert timestamp to a string
            upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Inserting file info into the database
            mydb = connect_to_database()
            mycursor = mydb.cursor()
            sql = "INSERT INTO files (filename, upload_time) VALUES (%s, %s)"
            session['last_uploaded_file'] = {'filename': filename, 'upload_time': upload_time}
            val = (filename, upload_time)
            mycursor.execute(sql, val)
            # Notify the recipient and fixed email address
            email = request.form.get('email')
            send_email_notification(email)
            #send_email_notification('testdivya368@gmail.com')
            mydb.commit()
            mycursor.close()
            mydb.close()

            session['authenticated'] = True

            # If email is provided, send an email
            if email:
                send_to_user(file_path, email)

            return {"message": "File uploaded successfully!"}
        else:
            return {"error": "Invalid file format."}
    except Exception as e:
        return {"error": f"Failed to upload file. Error: {e}"}
def send_to_user(file_path, recipient_email):
    try:
        # Check if the recipient's email is the fixed email address
        if recipient_email != 'testdivya368@gmail.com':
            return "Email not sent to recipient."

        email_sender = 'testdivya368@gmail.com'
        email_password = 'brcq gkuv uwri dcwk'
        subject = 'Your Sequence Number'

        # Create the email message
        message = MIMEMultipart()
        message['Subject'] = subject
        message['From'] = email_sender
        message['To'] = recipient_email

        # Attach the file
        with open(file_path, 'rb') as f:
            attachment = MIMEApplication(f.read(), _subtype="pdb")
            attachment.add_header('Content-Disposition', f'attachment; filename={os.path.basename(file_path)}')
            message.attach(attachment)

        # Do not add any additional text to the email

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.login(email_sender, email_password)
            server.send_message(message)

        return "Email sent successfully!"
    except Exception as e:
        app.logger.error(f"An error occurred. Error: {e}")
        return f"Failed to send the email. Please try again or contact support."
    
def send_email_notification(to_email):
    try:
        # Send email to fixed email address only
        msg_fixed = Message("File Uploaded Notification",
                            sender="testdivya368@gmail.com",
                            recipients=["testdivya368@gmail.com"])
        msg_fixed.body = f"User ({to_email}) has uploaded a file."
        mail.send(msg_fixed)

        return True
    except Exception as e:
        print(f"Error sending email notification: {e}")
        return False
    
@app.route('/send-email', methods=['POST'])
def send_email():
    try:
        sequence = request.form.get('sequence')
        recipient_email = request.form.get('email')
        send_email_checkbox = 'sendEmail' in request.form
        ngrok_url = session['ngrok_url']
        
        if send_email_checkbox:
            # Handle file upload
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
# email_sender to be changed later,  currently using gmail account for testing purposes
# ampm.group2021@gmail.com
# gmail password is 2 step verification password NOT gmail password, to find: Enter manage your accounts ; security ; 2-step verfication; App passwords
                
        email_sender = 'testdivya368@gmail.com'
        email_password = 'brcq gkuv uwri dcwk'
        subject = 'Your Sequence Number'
        # Create the email message
        message = MIMEMultipart()
        message['Subject'] = subject
        message['From'] = email_sender
        message['To'] = recipient_email
        # Attach the file if checkbox is selected
        if send_email_checkbox:
            with open(file_path, 'rb') as f:
                attachment = MIMEApplication(f.read(), _subtype="pdb")
                attachment.add_header('Content-Disposition', f'attachment; filename={filename}')
                message.attach(attachment)
        # Add any additional text to the email if needed
        body = f'<p>Your sequence number is: {sequence}</p>'
        message.attach(MIMEText(body, 'html'))
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.login(email_sender, email_password)
            server.send_message(message)
        return "Email sent successfully!"
    except Exception as e:
        app.logger.error(f"An error occurred. Error: {e}")
        return f"Failed to send the email. Please try again or contact support."

@app.route('/user_files', methods=['GET'])
def user_files():
    try:
        # Retrieve the list of uploaded files and their upload times from the database
        mydb = connect_to_database()
        mycursor = mydb.cursor(dictionary=True)
        mycursor.execute("SELECT filename, upload_time, downloaded_time FROM files")
        files_info = [(row['filename'], row['upload_time'], row['downloaded_time']) for row in mycursor.fetchall()]
        mycursor.close()
        mydb.close()
        # Check if files_info is empty
        if not files_info:
            user_files = []
            upload_times = []
        else:
            # Sort files_info based on upload_time
            files_info.sort(key=lambda x: (not x[2], x[1]), reverse=True)
            # Separate filenames, upload times, and downloaded times into three lists
            user_files, upload_times, downloaded_times = zip(*files_info)
        # Create URLs for ngrok and Flask
        ngrok_url = session.get('ngrok_url')
        ngrok_user_files = [f"{ngrok_url}/uploaded_files/{file}" for file in user_files]
        # Retrieve lastDownloadTime parameter
        last_download_time = session.get('last_download_time', None)
        # Pass the last_download_time and zipped list to the template
        return render_template('user_files.html', user_files_info=zip(user_files, upload_times, downloaded_times), ngrok_user_files=ngrok_user_files, last_download_time=last_download_time, to_datetime=to_datetime)
    except Exception as e:
        print(f"Error in user_files: {e}")
        return {"error": f"Failed to retrieve user files. Error: {e}"}

# all file download
@app.route('/download-selected-files', methods=['POST'])
def download_selected_files():
    try:
        selected_files = request.form.getlist('selected_files[]')
        if not selected_files:
            return "No files selected for download."

        # Create a ZIP file in-memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename in selected_files:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(file_path):
                    # Add the file to the ZIP archive with its original filename
                    zip_file.write(file_path, os.path.basename(file_path))
                else:
                    return f"File not found: {filename}"

        # Move the buffer's position to the beginning
        zip_buffer.seek(0)

        # Update the downloaded_time in the database for each selected file
        mydb = connect_to_database()
        mycursor = mydb.cursor()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for filename in selected_files:
            # Update the downloaded_time for each selected file
            sql_update = "UPDATE files SET downloaded_time = %s WHERE filename = %s"
            val_update = (current_time, filename)
            mycursor.execute(sql_update, val_update)
            mydb.commit()

        mycursor.close()
        mydb.close()

        # Send the ZIP file as a response
        return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='selected_files.zip')

    except Exception as e:
        return {"error": f"Failed to download files. Error: {e}"}
    
@app.route('/delete-selected-files', methods=['POST'])
def delete_selected_files():
    try:
        selected_files = request.form.getlist('selected_files[]')
        for filename in selected_files:
            # Delete file from the server
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                # Delete the file info from the db
                mydb = connect_to_database()
                mycursor = mydb.cursor()
                sql = "DELETE FROM files WHERE filename = %s"
                val = (filename,)
                mycursor.execute(sql, val)
                mydb.commit()
                mycursor.close()
                mydb.close()
        return redirect(url_for('user_files'))
    except Exception as e:
        return {"error": f"Failed to delete selected files. Error: {e}"}
    
@app.route('/uploaded_files/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
# single file download
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
@app.route('/delete-file/<filename>', methods=['POST'])
def delete_file(filename):
    try:
        # Delete file from the server
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            # Delete the file info from the db
            mydb = connect_to_database()
            mycursor = mydb.cursor()
            sql = "DELETE FROM files WHERE filename = %s"
            val = (filename,)
            mycursor.execute(sql, val)
            mydb.commit()
            mycursor.close()
            mydb.close()
            return redirect(url_for('user_files'))
        else:
            return {"error": "File not found."}
    except Exception as e:
        return {"error": f"Failed to delete file. Error: {e}"}

@app.route('/')
def index():
    ngrok_url = 'https://4f42-2404-e801-2001-3e3f-f006-cc10-1bba-391e.ngrok-free.app'
    session['ngrok_url'] = ngrok_url
    session['authenticated'] = False  
    return render_template('index.html', sequence="", ngrok_url=ngrok_url)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
