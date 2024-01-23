import zipfile
from flask import Flask, Response, redirect, request, render_template, send_from_directory, session, url_for
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
            #original_filename, file_extension = os.path.splitext(file.filename)
            #unique_filename = f"{original_filename}_{uuid4().hex}{file_extension}"
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            # Convert the current timestamp to a string
            upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Insert file infon into the database
            mydb = connect_to_database()
            mycursor = mydb.cursor()
            sql = "INSERT INTO files (filename, upload_time) VALUES (%s, %s)"
            val = (filename, upload_time)
            mycursor.execute(sql, val)
            mydb.commit()
            mycursor.close()
            mydb.close()
            session['authenticated'] = True
            return {"message": "File uploaded successfully!"}
        else:
            return {"error": "Invalid file format."}
    except Exception as e:
        return {"error": f"Failed to upload file. Error: {e}"}

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

        mycursor.execute("SELECT filename, upload_time FROM files")
        files_info = [(row['filename'], row['upload_time']) for row in mycursor.fetchall()]

        mycursor.close()
        mydb.close()

        # Check if files_info is empty
        if not files_info:
            user_files = []
            upload_times = []
        else:
            # Sort files_info based on upload_time
            files_info.sort(key=lambda x: x[1], reverse=True)

            # Separate filenames and upload times into two lists
            user_files, upload_times = zip(*files_info)

        # Create URLs for ngrok and Flask
        ngrok_url = session.get('ngrok_url')
        ngrok_user_files = [f"{ngrok_url}/uploaded_files/{file}" for file in user_files]

        # Retrieve lastDownloadTime parameter
        last_download_time = session.get('last_download_time', None)

        # Pass the last_download_time and zipped list to the template
        return render_template('user_files.html', user_files_info=zip(user_files, upload_times), ngrok_user_files=ngrok_user_files, last_download_time=last_download_time, to_datetime=to_datetime)
    except Exception as e:
        print(f"Error in user_files: {e}")
        return {"error": "Failed to retrieve user files."}

# all file download
@app.route('/download-all')
def download_all_files():
    try:
        # Get the list of uploaded files
        mydb = connect_to_database()
        mycursor = mydb.cursor(dictionary=True)
        mycursor.execute("SELECT filename FROM files")
        files_info = [row['filename'] for row in mycursor.fetchall()]
        mycursor.close()
        mydb.close()

        if not files_info:
            # No files to download
            return "No files to download."

        # Create a ZIP file in-memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename in files_info:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                zip_file.write(file_path, os.path.basename(file_path))

        # Move the buffer's position to the beginning
        zip_buffer.seek(0)

        # Create a Flask response with the ZIP file
        response = Response(zip_buffer, content_type='application/zip')
        response.headers["Content-Disposition"] = "attachment; filename=all_files.zip"

        # Update the last download time in the session
        last_download_time = datetime.now()
        session['last_download_time'] = last_download_time

        # Delete downloaded files
        for filename in files_info:
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

        # Redirect to user_files
        return response

    except Exception as e:
        return {"error": f"Failed to download files. Error: {e}"}
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

#@app.before_request
#def before_request():
    #if 'ngrok_url' not in session:
        # Update ngrok_url to use the provided subdomain
        #session['ngrok_url'] = 'https://a5b4-66-96-214-220.ngrok-free.app'
@app.route('/')
def index():
    ngrok_url = 'https://4f42-2404-e801-2001-3e3f-f006-cc10-1bba-391e.ngrok-free.app'
    session['ngrok_url'] = ngrok_url
    session['authenticated'] = False  
    return render_template('index.html', sequence="", ngrok_url=ngrok_url)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)