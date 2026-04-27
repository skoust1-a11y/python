class Student:
    def __init__(self, name, age, course, marks):
        self.name = name
        self.age = age
        self.course = course
        self.marks = marks

    def __str__(self):
        return f"Student: {self.name}, Age: {self.age}, Course: {self.course}"

    def __eq__(self, other):
        if not isinstance(other, Student):
            return False
        return self.name == other.name and self.course == other.course

class GraduateStudent(Student):
    def __init__(self, name, age, course, marks, thesis_title):
        super().__init__(name, age, course, marks)
        self.thesis_title = thesis_title

    def __str__(self):
        return super().__str__() + f", Thesis: {self.thesis_title}"