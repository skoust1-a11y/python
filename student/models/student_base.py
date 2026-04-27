class Student():
    def __init__(self,name,age,course,marks):
        self.name = name
        self.age = age
        self.course = course
        self.marks = marks
    
    def grade_eval(self):
        if(self.marks > 75):
            return 'A'
        elif(self.marks > 60 and self.marks <= 75):
            return 'B'
        elif(self.marks > 40 and self.marks <= 60):
            return 'C'
        elif(self.marks > 30 and self.marks <= 40):
            return 'D'
        else:
            return 'E'
    
    @classmethod
    def student_input(cls,data):
        return cls(**data)

class GraduateStudent(Student):
    def __init__(self, name, age, course, marks,thesis_title):
        super().__init__(name, age, course, marks)
        self.thesis_title = thesis_title

    def __str__(self):
        return (
            f"Graduate Student: {self.name}, Course: {self.course}\n"
            f"Thesis Topic: {self.thesis_title}\n"
            f"Grade: {self.grade_eval()}"
        )

    def __eq__(self, other):
        if not isinstance(other, GraduateStudent):
            return NotImplemented
        return self.__dict__ == other.__dict__