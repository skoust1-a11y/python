from dataclasses import dataclass, field
import uuid

@dataclass
class StudentRecord:
    name: str
    age: int
    course: str
    marks: float
    enrollment_id: str = field(init=False)

    def __post_init__(self):
        # Generate a unique ID after the object is initialized
        self.enrollment_id = f"STU-{uuid.uuid4().hex[:6].upper()}"

    def calculate_grade(self):
        if self.marks >= 90: return "A"
        elif self.marks >= 75: return "B"
        elif self.marks >= 50: return "C"
        else: return "F"