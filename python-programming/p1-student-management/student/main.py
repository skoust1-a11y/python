from pydantic import ValidationError

from models.student_base import GraduateStudent, Student
from models.student_record import StudentRecord
from models.student_model import StudentModel

import json


def display_performance_report(student_record):
    print(f"Name: {student_record.name}")
    print(f"Age: {student_record.age}")
    print(f"Course: {student_record.course}")
    print(f"Marks: {student_record.marks}")
    print(f"Grade: {student_record.grade}")

    if student_record.marks >= 75:
        print("Performance: Excellent")
    elif student_record.marks >= 50:
        print("Performance: Average")
    else:
        print("Performance: Needs Improvement")


def main():
    print("=== Core Class Objects ===")

    student = Student("Asha", 20, "Data Science", 81)
    graduate_student = GraduateStudent(
        "Rohan", 24, "Computer Science", 89, "AI in Education"
    )

    print(student)
    print(graduate_student)

    print("=== Creating Student Records (Dataclass) ===")

    # Using dataclass
    student1 = StudentRecord("Jay", 21, "CS", 88)
    student2 = StudentRecord("Sam", 22, "AI", 92)

    print(student1)
    print(student2)

    print("\n=== Validating with Pydantic ===")

    student_payloads = [
        {
            "name": "Jay",
            "age": 21,
            "marks": 88,
            "guardian_number": "9876543210",
        },
        {
            "name": "",
            "age": 19,
            "marks": 74,
            "guardian_number": "12345",
        },
    ]
    validated_students = []

    for payload in student_payloads:
        try:
            validated_student = StudentModel(**payload)
            validated_students.append(validated_student)
            print("Validated Student:")
            print(validated_student)
        except ValidationError as error:
            print("Validation failed for StudentModel:")
            print(error)

    print("\n=== Performance Report ===")
    display_performance_report(student1)

    print("\n=== Performance Report ===")
    display_performance_report(student2)

    print("\n=== Serialization ===")

    if not validated_students:
        print("No validated students available for serialization.")
        return

    # Convert to dictionary
    student_dict = validated_students[0].model_dump()
    print("Dictionary format:")
    print(student_dict)

    # Convert to JSON
    student_json = json.dumps(student_dict, indent=4)
    print("\nJSON format:")
    print(student_json)

    
if __name__ == "__main__":
    main()


