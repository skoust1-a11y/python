from student.models.student_base import GraduateStudent,Student
from student.models.student_record import Student
from student.models.student_model import StudentModel

def main():
    my_dict = {
        'name': 'Kiran',
        'course' : 'Msc Data Science',
        'thesis_title': 'AI in HealthCare',
        'marks': 67,
        'age' : 24
    }
    grad_student = GraduateStudent(**my_dict)

    print(grad_student.__str__())

    print()

    my_dict_data_class = {
        'name': 'Mohit',
        'course' : 'Msc Data Science',
        'marks': 67,
        'age' : 24,
    }

    student_using_dataclass = Student(**my_dict_data_class)

    student_using_dataclass.view_students()

    print()

    my_dict_for_pydantic = {
        'name': 'Mohit',
        'guardian_number' : 5678987656,
        'marks': 78.0,
        'age' : 24,
    }

    student_model = StudentModel(**my_dict_for_pydantic)

    print('Validated Model data(as dict):')
    print(student_model.model_dump())

    print('Validated Model Data (as JSON):')
    print(student_model.model_dump_json(indent=4))

if __name__ == "__main__":
    main()
