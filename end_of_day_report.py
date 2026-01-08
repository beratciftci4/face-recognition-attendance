import sqlite3
from datetime import datetime
import os.path
import base64
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

DB_NAME = "attendance.db"

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def send_absence_notification(student_name, guardian_email, date_str):
    """Belirtilen veli e-postasına Gmail API (OAuth 2.0) kullanarak bildirim gönderir."""
    if not guardian_email:
        print(f"Skipping email for {student_name}: no guardian email found.")
        return

    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        message = EmailMessage()
        message.set_content(
             f"Dear Parent/Guardian,\n\n"
             f"This is to inform you that your student, {student_name}, was absent from school on {date_str}.\n\n"
             f"Sincerely,\n"
             f"School Administration"
        )
        message["To"] = guardian_email
        message["From"] = "me" 
        message["Subject"] = f"Absence Notification: {student_name}"

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": encoded_message}

        send_message = (
            service.users().messages().send(userId="me", body=create_message).execute()
        )
        print(f"Successfully sent email to {guardian_email} for {student_name}. Message ID: {send_message['id']}")

    except HttpError as error:
        print(f"An error occurred while sending email: {error}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def generate_daily_report():
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"--- Generating report for {today_str} ---")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT id, first_name, last_name, guardian_email FROM Students")
    all_students = {row[0]: {'full_name': f"{row[1]} {row[2]}", 'email': row[3]} for row in cursor.fetchall()}

    cursor.execute("SELECT student_id FROM Attendance WHERE date = ? AND status = 'PRESENT'", (today_str,))
    present_student_ids = {row[0] for row in cursor.fetchall()}
    
    absent_count = 0
    for student_id, student_info in all_students.items():
        if student_id not in present_student_ids:
            absent_count += 1
            student_name = student_info['full_name']
            guardian_email = student_info['email']
            print(f"ABSENT: {student_name}")

            cursor.execute("INSERT INTO Attendance (student_id, date, status) VALUES (?, ?, 'ABSENT')", (student_id, today_str))
            send_absence_notification(student_name, guardian_email, today_str)
    
    if absent_count == 0:
        print("Everybody was present today. No emails sent.")

    conn.commit()
    conn.close()
    print("--- Report generation complete. ---")

if __name__ == "__main__":
    generate_daily_report()