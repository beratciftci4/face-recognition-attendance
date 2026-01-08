import cv2
import face_recognition
import sqlite3
import pickle
import numpy as np
from datetime import datetime
import time
import threading 
import os
import pygame
import base64
from email.message import EmailMessage

# --- HARDWARE LIBRARIES ---
#from RPLCD.i2c import CharLCD
#import RPi.GPIO as GPIO

# --- GOOGLE OAUTH LIBRARIES ---
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# --- SETTINGS ---
DB_NAME = "attendance.db"
DELAY_SECONDS = 1.0
SOUND_FOLDER = "sounds" 
CLASS_FILE = "class.txt" 
REPORT_HOUR = "17:00"    
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# --- LESSON LIST ---
LESSON_LIST = [
    "Mathematics",
    "Physics",
    "History",
    "Geography",
    "English",
    "Computer Science",
    "Biology",
    "Chemistry"
]

# --- AUDIO SETTINGS ---
pygame.mixer.init()

# --- HARDWARE SETUP ---
GPIO_PIN_SERVO = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_PIN_SERVO, GPIO.OUT)
pwm_servo = GPIO.PWM(GPIO_PIN_SERVO, 50)
pwm_servo.start(0)

LCD_I2C_ADDRESS = 0x27 
lcd = None

report_sent_today = False

# --- DATABASE CHECK (ORIGINAL SIMPLE VERSION) ---
def check_database():
    """Creates the simple table without extra columns."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            check_in_time TEXT,
            status TEXT NOT NULL
        );
    ''')
    conn.commit()
    conn.close()

# --- SELECTION FUNCTIONS ---

def get_classroom_from_file():
    """Reads fixed classroom name for display."""
    if not os.path.exists(CLASS_FILE):
        return "Unknown Room"
    try:
        with open(CLASS_FILE, 'r') as f:
            return f.read().strip()
    except:
        return "Unknown Room"

def get_lesson_choice(current_classroom):
    """Displays menu and asks for lesson selection (For Display Only)."""
    while True:
        print("\n" * 5)
        print("="*30)
        print(f" ROOM: {current_classroom}")
        print("="*30)
        print(" SELECT CURRENT LESSON (For Display):")
        
        for i, lesson in enumerate(LESSON_LIST):
            print(f" {i+1}. {lesson}")
        
        print("="*30)
        
        try:
            choice = input(f"Enter Number (1-{len(LESSON_LIST)}): ")
            choice_int = int(choice)
            
            if 1 <= choice_int <= len(LESSON_LIST):
                selected = LESSON_LIST[choice_int - 1]
                print(f"\n✅ SELECTED: {selected}")
                print("Starting Camera...\n")
                return selected
            else:
                print("Invalid number. Try again.")
        except:
            print("Please enter a valid number.")

# --- HARDWARE FUNCTIONS ---

def setup_hardware():
    global lcd
    try:
        lcd = CharLCD('PCF8574', LCD_I2C_ADDRESS, auto_linebreaks=True)
        lcd.backlight_enabled = True
        lcd.clear()
        lcd.write_string("System Loading...")
    except:
        lcd = None

def play_audio(name):
    clean_name = name.lower().replace(" ", "")
    filename = f"{clean_name}.mp3"
    
    def worker(fname):
        path = os.path.join(SOUND_FOLDER, fname)
        if not os.path.exists(path):
            path = os.path.join(SOUND_FOLDER, "default.mp3")
        
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            except: pass
    t = threading.Thread(target=worker, args=(filename,))
    t.start()

def open_door():
    print("DOOR: Opening...")
    pwm_servo.ChangeDutyCycle(7) # 90 Deg
    time.sleep(0.5)
    pwm_servo.ChangeDutyCycle(0)
    
    time.sleep(5) 
    
    print("DOOR: Closing...")
    pwm_servo.ChangeDutyCycle(2) # 0 Deg
    time.sleep(0.5)
    pwm_servo.ChangeDutyCycle(0)

def write_to_screen(line1, line2):
    if lcd is None: return
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string(line1[:16]) 
    lcd.cursor_pos = (1, 0)
    lcd.write_string(line2[:16])

def draw_overlay(frame, name, location, status_text):
    if location is None: 
        cv2.rectangle(frame, (0, 0), (640, 40), (0, 0, 0), -1)
        cv2.putText(frame, f"STATUS: {status_text}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        return

    top, right, bottom, left = location
    top *= 4; right *= 4; bottom *= 4; left *= 4
    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
    cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
    cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)
    
    cv2.rectangle(frame, (0, 0), (640, 40), (0, 0, 0), -1)
    cv2.putText(frame, f"STATUS: {status_text}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

# --- DATABASE OPERATIONS ---

def load_known_faces():
    known_encodings, known_ids, known_names = [], [], []
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, first_name, last_name, face_encoding FROM Students")
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            encoding = pickle.loads(row[3])
            known_ids.append(row[0])
            known_names.append(f"{row[1]} {row[2]}")
            known_encodings.append(encoding)
    except: return [], [], []
    print(f"Database: {len(known_ids)} faces loaded.")
    return known_encodings, known_ids, known_names

def mark_attendance(student_id):
    """Saves ONLY ID, Date, Time, Status."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_str = datetime.now().strftime("%H:%M:%S")
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Attendance (student_id, date, check_in_time, status)
            VALUES (?, ?, ?, 'PRESENT')
        """, (student_id, today_str, now_str))
        conn.commit()
        print(f"LOG: Attendance saved.")
    except sqlite3.Error as e:
        print(f"DB Error: {e}")
    finally:
        if conn: conn.close()

# --- EMAIL REPORTING ---

def send_email_via_gmail(student_name, guardian_email, date_str):
    if not guardian_email: return
    
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        message = EmailMessage()
        message.set_content(f"Dear Guardian,\n\nStudent {student_name} was marked ABSENT on {date_str}.\n\nRegards,\nUniversity Center Management")
        message["To"] = guardian_email
        message["From"] = "me"
        message["Subject"] = f"Absence Alert: {student_name}"

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": encoded_message}
        service.users().messages().send(userId="me", body=create_message).execute()
        print(f"EMAIL SENT: {guardian_email}")
    except: pass

def check_and_run_end_of_day_report():
    global report_sent_today
    now = datetime.now()
    current_time_str = now.strftime("%H:%M")
    
    if current_time_str == "00:00": report_sent_today = False

    if current_time_str == REPORT_HOUR and not report_sent_today:
        print("REPORT: Generating end of day report...")
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            today_str = now.strftime("%Y-%m-%d")
            
            cursor.execute("SELECT id, first_name, last_name, guardian_email FROM Students")
            all_students = cursor.fetchall()
            
            cursor.execute("SELECT student_id FROM Attendance WHERE date = ?", (today_str,))
            present_ids = [row[0] for row in cursor.fetchall()]
            
            for stu in all_students:
                s_id, f_name, l_name, email = stu
                if s_id not in present_ids:
                    full_name = f"{f_name} {l_name}"
                    print(f"ABSENT: {full_name}")
                    cursor.execute("INSERT INTO Attendance (student_id, date, status) VALUES (?, ?, 'ABSENT')", (s_id, today_str))
                    t = threading.Thread(target=send_email_via_gmail, args=(full_name, email, today_str))
                    t.start()
            conn.commit()
            conn.close()
            report_sent_today = True
            print("REPORT: Completed.")
        except: pass

# --- MAIN LOOP ---
def main_loop():
    check_database()
    setup_hardware()
    
    current_classroom = get_classroom_from_file()
    
    known_encodings, known_ids, known_names = load_known_faces()
    last_report_check = time.time()
    
    while True:
        # Ask for lesson (Just for Display)
        if lcd: 
            lcd.clear()
            lcd.write_string("Select Lesson...")
            
        current_lesson = get_lesson_choice(current_classroom)
        
        # Setup Camera
        video_capture = cv2.VideoCapture(0)
        video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        video_capture.set(cv2.CAP_PROP_FPS, 30)
        
        todays_attendance_ids = set()
        detection_timers = {}
        current_status = "SCANNING..."
        process_this_frame = True 
        
        # Show on LCD
        if lcd:
            lcd.clear()
            lcd.write_string(current_lesson[:16])
            lcd.cursor_pos = (1, 0)
            lcd.write_string("Scanning...")

        print(f"--- LESSON STARTED: {current_lesson} ---")
        print("Press 'q' to end this lesson.")

        while True:
            if time.time() - last_report_check > 60:
                check_and_run_end_of_day_report()
                last_report_check = time.time()

            ret, frame = video_capture.read()
            if not ret: break

            if process_this_frame:
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                
                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                
                face_names = []
                current_status = "SCANNING..."

                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.5)
                    name = "Unknown"
                    student_id = None
                    
                    if True in matches:
                        first_match_index = matches.index(True)
                        student_id = known_ids[first_match_index]
                        name = known_names[first_match_index]
                        
                        if student_id not in todays_attendance_ids:
                            if student_id not in detection_timers:
                                detection_timers[student_id] = time.time()
                                current_status = f"FOUND: {name}"
                            else:
                                elapsed = time.time() - detection_timers[student_id]
                                if elapsed >= DELAY_SECONDS:
                                    current_status = f"ENTER: {name}"
                                    draw_overlay(frame, name, face_locations[0], current_status)
                                    cv2.imshow('Attendance System', frame)
                                    cv2.waitKey(1)
                                    
                                    # --- ACTIONS ---
                                    write_to_screen("Welcome:", name)
                                    play_audio(name)
                                    open_door()
                                    
                                    # SAVE: ID Only
                                    mark_attendance(student_id)
                                    
                                    todays_attendance_ids.add(student_id)
                                    del detection_timers[student_id]
                                    
                                    if lcd: 
                                        lcd.clear()
                                        lcd.write_string(current_lesson[:16])
                                        lcd.cursor_pos = (1, 0)
                                        lcd.write_string("Scanning...")
                    
                    face_names.append(name)

            process_this_frame = not process_this_frame

            if face_locations:
                for (top, right, bottom, left), name in zip(face_locations, face_names):
                    draw_overlay(frame, name, (top, right, bottom, left), current_status)
            else:
                 draw_overlay(frame, "", None, current_status)

            cv2.imshow('Attendance System', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        video_capture.release()
        cv2.destroyAllWindows()

    pwm_servo.stop()
    GPIO.cleanup()
    if lcd: lcd.clear()

if __name__ == "__main__":
    main_loop()