from dataclasses import dataclass, field

@dataclass
class StudentRecord:
    name: str
    age: int
    course: str
    marks: float

    # Auto-generated fields
    enrollment_id: int = field(init=False)
    grade: str = field(init=False)

    # Class variable to keep track of IDs
    _id_counter: int = 1000

    def __post_init__(self):
        # Generate unique enrollment ID
        self.enrollment_id = StudentRecord._id_counter
        StudentRecord._id_counter += 1

        # Assign grade
        self.grade = self.calculate_grade()

    def calculate_grade(self):
        if self.marks >= 90:
            return "A+"
        elif self.marks >= 75:
            return "A"
        elif self.marks >= 60:
            return "B"
        elif self.marks >= 50:
            return "C"
        else:
            return "F"

    def __str__(self):
        return (f"ID: {self.enrollment_id}, Name: {self.name}, "
                f"Course: {self.course}, Marks: {self.marks}, Grade: {self.grade}")