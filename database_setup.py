import sqlite3

DB_NAME = "attendance.db"

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS Students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    guardian_phone TEXT,
    guardian_email TEXT,
    face_encoding BLOB NOT NULL
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    check_in_time TEXT,
    status TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES Students (id)
);
''')

print("Database and tables were created successfully!")

conn.commit()
conn.close()