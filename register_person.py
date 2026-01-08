import cv2
import face_recognition
import sqlite3
import pickle

DB_NAME = "attendance.db"

def save_encoding_to_db(first_name, last_name, encoding):
    """
    Saves the person's name and face encoding to the database.
    """
    try:
        pickled_encoding = pickle.dumps(encoding)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Students (first_name, last_name, face_encoding)
            VALUES (?, ?, ?)
        """, (first_name, last_name, pickled_encoding))

        conn.commit()
        print(f"SUCCESS: {first_name} {last_name} has been registered to the database.")

    except sqlite3.Error as e:
        print(f"DATABASE ERROR: {e}")
    finally:
        if conn:
            conn.close()    

def register_new_person():
    """
    Opens the camera to capture and register a new person's face.
    """
    first_name = input("Enter the person's first name: ")
    last_name = input("Enter the person's last name: ")

    if not first_name or not last_name:
        print("Error: First name and last name cannot be empty.")
        return

    video_capture = cv2.VideoCapture(0)

    print("\nCamera is opening...")
    print("Please look directly at the camera.")
    print("Press 's' to save the face. Press 'q' to quit without saving.")

    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Failed to grab frame from camera. Exiting.")
            break
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        
        for (top, right, bottom, left) in face_locations:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

        cv2.putText(frame, "Look at camera and press 's' to save", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, "Press 'q' to quit", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow('Register New Person', frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            print("Registration cancelled.")
            break
        elif key == ord('s'):
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

            if len(face_encodings) == 0:
                print("WARNING: No face detected! Please try again.")
                continue
            elif len(face_encodings) > 1:
                print("WARNING: Multiple faces detected! Please ensure only one person is in the frame.")
                continue
            
            print("Face detected successfully! Saving to database...")
            new_encoding = face_encodings[0]
            save_encoding_to_db(first_name, last_name, new_encoding)
            break

    video_capture.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    register_new_person()