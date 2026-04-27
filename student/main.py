from student_base import Student, GraduateStudent
from student_record import StudentRecord
from student_model import StudentModel
import json

def main():
    print("--- Step 1: Standard OOP ---")
    s1 = Student("Alice", 20, "CS", 85)
    s2 = Student("Alice", 20, "CS", 85)
    print(s1)
    print(f"Are s1 and s2 equal? {s1 == s2}")

    print("\n--- Step 2: Dataclasses ---")
    rec = StudentRecord("Bob", 22, "Math", 92)
    print(f"Record: {rec.name}, ID: {rec.enrollment_id}, Grade: {rec.calculate_grade()}")

    print("\n--- Step 3 & 4: Pydantic Validation & Serialization ---")
    try:
        # Valid Data
        student_data = {
            "name": "Charlie",
            "age": 19,
            "marks": 78.5,
            "guardian_number": "9876543210"
        }
        m1 = StudentModel(**student_data)
        
        # Serialization
        print("Dictionary output:", m1.model_dump())
        print("JSON output:", m1.model_dump_json())

        # Testing Validation Error (Empty Name)
        print("\nTesting validation error...")
        StudentModel(name="", age=20, marks=50, guardian_number="123")
    except Exception as e:
        print(f"Validation Error Caught: {e}")

if __name__ == "__main__":
    main()