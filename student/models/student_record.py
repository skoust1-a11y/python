from dataclasses import dataclass,field
import random

@dataclass
class Student:
    name : str
    course : str
    age : int = 18
    marks : int = 0
    unique_id : int = field(init=False)

    def __post_init__(self):
        self.unique_id = random.randint(1,9999)
    
    def grade_eval(self):
        if(self.marks > 85):
            return 'A+'
        elif(self.marks > 75):
            return 'A'
        elif(self.marks > 60 and self.marks <= 75):
            return 'B'
        elif(self.marks > 40 and self.marks <= 60):
            return 'C'
        elif(self.marks > 30 and self.marks <= 40):
            return 'D'
        else:
            return 'E'
    
    def view_students(self):
        print(f'Dataclass Record: {self.name}, Grade: {self.grade_eval()}, ID: STU-{self.unique_id}')

