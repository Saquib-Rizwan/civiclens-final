from flask import Flask, request, jsonify, render_template_string, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import json
import csv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from keras.models import load_model
from keras.preprocessing import image
import numpy as np
from flask import render_template, request
from flask import send_from_directory
from datetime import datetime
from flask import Response
from pymongo import MongoClient

load_dotenv()

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
MODEL_PATH = "ai_model/model.h5"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

client = MongoClient(os.getenv("MONGO_URI"))
db = client["civiclens"]
collection = db["reports"]
collection = db["submissions"]
email_logs = db["email_logs"]

model = load_model(MODEL_PATH)
class_labels = ['Garbage', 'Pothole', 'StreetlightDamage', 'WaterLeakage']

EMAIL_MAP = {
    "Garbage": {"email": "user.report.submission@gmail.com", "subject": "New Garbage Issue Reported"},
    "Pothole": {"email": "user.report.submission@gmail.com", "subject": "Pothole Alert Received"},
    "StreetlightDamage": {"email": "user.report.submission@gmail.com", "subject": "Streetlight Issue Logged"},
    "WaterLeakage": {"email": "user.report.submission@gmail.com", "subject": "Water Leakage Detected"}
}

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)

@app.route("/report", methods=["POST"])
def report():
    try:
        desc = request.form.get("description")
        location_name = request.form.get("location")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        details = request.form.get("details")
        user_name = request.form.get("name")
        user_email = request.form.get("email")
        file = request.files["image"]

        if not file or file.filename == '':
            return jsonify({"error": "No image uploaded"}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Predict
        img = image.load_img(filepath, target_size=(224, 224))
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array /= 255.0

        prediction = model.predict(img_array)
        predicted_class = class_labels[np.argmax(prediction)]

        report_data = {
            "description": desc,
            "location": {
                "name": location_name,
                "latitude": latitude,
                "longitude": longitude
            },
            "details": details,
            "filename": filename,
            "prediction": predicted_class,
            "timestamp": datetime.utcnow(),
            "user": {
                "name": user_name,
                "email": user_email
            }
        }

        result = collection.insert_one(report_data)
        report_id = str(result.inserted_id)

        # Send email
        if predicted_class in EMAIL_MAP:
            target_email = EMAIL_MAP[predicted_class]["email"]
            subject = EMAIL_MAP[predicted_class]["subject"]
            message = f"Reported by: {user_name} ({user_email})\nIssue: {predicted_class}\nLocation: {location_name} ({latitude}, {longitude})\nDescription: {desc}\nDetails: {details}"

            send_status = send_email(target_email, subject, message)
            print("✔️ Logging email to DB:", subject)
            if send_status == "Sent":
                email_logs.insert_one({
                    "to": target_email,
                    "subject": subject,
                    "timestamp": datetime.utcnow(),
                    "report_id": report_id,
                    "issue_type": predicted_class
                })

        return jsonify({
    "filename": filename,
    "prediction": predicted_class
})

<<<<<<< HEAD
    except Exception as e:
        app.logger.error("Prediction failed", exc_info=e)
        return jsonify({"error": "Prediction failed"}), 500

def send_email(to_email, subject, body):
    try:
        from_email = os.getenv("SMTP_FROM")
        password = os.getenv("SMTP_PASS")
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT"))

        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(from_email, password)
        server.send_message(msg)
        server.quit()
        return "Sent"
    except Exception as e:
        print("Mail failed:", e)
        return "Failed"

# CSV download routes
@app.route("/download-submissions")
def download_submissions_csv():
    try:
        data = list(collection.find())
        if not data:
            return Response("No data available.", mimetype='text/plain')

        def generate():
            yield 'ID,Name,Email,Description,Location,Latitude,Longitude,Prediction,Time,Image\n'
            for item in data:
                row = [
                    str(item.get("_id", "")),
                    item.get("user", {}).get("name", "").replace(',', ' '),
                    item.get("user", {}).get("email", "").replace(',', ' '),
                    item.get("description", "").replace(',', ' '),
                    item.get("location", {}).get("name", "").replace(',', ' '),
                    item.get("location", {}).get("latitude", ""),
                    item.get("location", {}).get("longitude", ""),
                    item.get("prediction", ""),
                    item.get("timestamp", ""),
                    item.get("filename", "")
                ]
                yield ','.join(map(str, row)) + '\n'

        return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=submissions.csv"})

    except Exception as e:
        return f"<p>Error: {str(e)}</p>", 500

@app.route("/download-email-logs")
def download_email_logs_csv():
    try:
        logs = list(email_logs.find())
        def generate():
            yield 'ID,To,Subject,Time,Report ID,Issue Type\n'
            for log in logs:
                row = [
                    str(log.get("_id", "")),
                    log.get("to", ""),
                    log.get("subject", "").replace(',', ' '),
                    log.get("timestamp", ""),
                    log.get("report_id", ""),
                    log.get("issue_type", "")
                ]
                yield ','.join(map(str, row)) + '\n'

        return Response(generate(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=email_logs.csv"})
    except Exception as e:
        return f"<p>Error: {str(e)}</p>", 500
@app.route("/")
def index():
    return render_template("report.html")
@app.route("/thankyou.html")
def thankyou():
    prediction = request.args.get("prediction")
    filename = request.args.get("filename")
    return render_template("thankyou.html", prediction=prediction, filename=filename)
from datetime import datetime

@app.route("/submissions")
def view_submissions():
    reports = list(collection.find().sort("timestamp", -1))
    for report in reports:
        if isinstance(report.get("timestamp"), str):
            try:
                report["timestamp"] = datetime.fromisoformat(report["timestamp"])
            except ValueError:
                pass  # leave as-is if it can't be parsed
    return render_template("submissions.html", reports=reports)

@app.route("/email-logs")
def email_logs_view():
    logs = list(email_logs.find().sort("timestamp", -1))
    for log in logs:
        if isinstance(log.get("timestamp"), str):
            try:
                log["timestamp"] = datetime.fromisoformat(log["timestamp"])
            except ValueError:
                pass
    return render_template("email_logs.html", logs=logs)





if __name__ == "__main__":
    app.run(debug=True, port=10000)
=======
# Run server
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)

>>>>>>> 5c74f2519e818f93ab7bf12fbcc6d0dad0330f72

