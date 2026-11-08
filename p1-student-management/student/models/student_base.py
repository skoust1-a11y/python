class Student:
    def __init__(self, name, age, course, marks):
        self.name = name
        self.age = age
        self.course = course
        self.marks = marks

    def __str__(self):
        return (f"Student(Name: {self.name}, Age: {self.age}, "
                f"Course: {self.course}, Marks: {self.marks})")

    def __eq__(self, other):
        if not isinstance(other, Student):
            return False
        return (self.name == other.name and
                self.age == other.age and
                self.course == other.course and
                self.marks == other.marks)


class GraduateStudent(Student):
    def __init__(self, name, age, course, marks, thesis_title):
        super().__init__(name, age, course, marks)
        self.thesis_title = thesis_title

    def __str__(self):
        return (f"GraduateStudent(Name: {self.name}, Age: {self.age}, "
                f"Course: {self.course}, Marks: {self.marks}, "
                f"Thesis: {self.thesis_title})")

    def __eq__(self, other):
        if not isinstance(other, GraduateStudent):
            return False
        return (super().__eq__(other) and
                self.thesis_title == other.thesis_title)