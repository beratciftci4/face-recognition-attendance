🛡️ Smart-Attend: AI Face Recognition & Hardware Automation

Smart-Attend is a comprehensive, Raspberry Pi-based attendance solution that merges Deep Learning with IoT hardware. It doesn't just recognize faces; it manages entry via servo-controlled doors, provides real-time LCD feedback, and automates parent notifications using the Gmail API.


🌟Key Features

- Real-time Biometric Recognition: Uses state-of-the-art face encodings to identify students with high precision.
- Hardware Control Hub: * Automated Entry: Controls a 90-degree servo motor to simulate door locking/unlocking upon successful identification.
    + Visual Interface: Provides live status updates on a 16x2 I2C LCD screen.
- Smart Reporting Engine: * Automatically detects absences at a predefined "End of Day" hour.
    + Sends automated alerts to guardians via OAuth 2.0 Gmail API integration. 
- Secure Database Management: Maintains student profiles and timestamped attendance logs using an optimized SQLite schema.


🛠️ Tech Stack
Language: Python
AI/ML: face_recognition (dlib), OpenCV, NumPy
Database: SQLite3
Hardware Interface: RPi.GPIO, RPLCD
Automation: Google API Client, Threading


📁 System Architecture

main_app.py - The central brain. Handles the camera loop, face matching, and hardware signals.
register_person.py - Enrollment module. Captures face encodings and stores them as BLOBs in the database.
database_setup.py - Initializes the relational database for students and logs.
end_of_day_report.py - Independent script to audit daily records and dispatch emails.

🚀 Getting Started
1. Database Initialization 
  First, set up your local storage: python database_setup.py
2. Student Enrollment
  Run the registration script and follow the on-screen prompts to capture face data: python register_person.py
3. Running the System
  Start the main recognition and hardware loop: python main_app.py
  
🔒 Security Requirements
For the Gmail notification system to work, you must provide your own credentials.json from the Google Cloud Console.
Note: For security reasons, the token.json and credentials.json files are excluded from this repository to protect private API access.


