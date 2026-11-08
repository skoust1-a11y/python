## Practice Exercise: Student Management App​

### Problem Statement

- Design a Python application to manage student information and performance reports.​
- Implement various representations of student data using standard classes, dataclasses, and Pydantic models to demonstrate evolution from simple object structures to validated, serilizable models.​
- The application should allow the creation of student profiles, perform grade calculation, validate inputs such as age and marks, and ensure accurate, well-formatted report outputs that can easily be extended in the future.

### Context

Educational institutions increasingly rely on digital systems to manage student data efficiently. A well-structured program can simplify tracking academic performance, automate report generation, and ensure data accuracy through
validation.  ​

​Your task is to create a reliable student management system that simulates a real-world scenario where object-oriented principles, data modeling, and validation come together.

### Task Details

Following steps should be performed to build the solution for this practice. ​

#### Step 1: Define Core Classes for Student Data (`student_base.py`)
- Create a base class `Student` containing attributes like name, age, course, and marks.​
- Add a derived class `GraduateStudent` extending Student with an extra attribute like `thesis_title`.​
- Implement a `__str__()` and `__eq__()` methods for readable object display and object comparison respectively.​

#### Step 2: Automate Initialization Using Dataclasses (`student_record.py`)
- Convert the student data representation into a dataclass using `@dataclass`.​
- Use `field(init=False)` and `__post_init__()` to auto-generate unique enrollment IDs.​
- Add grade calculation logic within the dataclass for better structure and reusability.

#### Step 3: Add Validation with Pydantic​ (`student_model.py`)​
- Create a `StudentModel` using `BaseModel` to validate attributes like name, age, marks, and guardian_number.​
    - Ensure name, age and marks are not left empty​
- Add validators to ensure values fall within acceptable ranges and data types are correct.​
- Implement automatic type checking and clean error handling.

#### Step 4: Integrate and Display Reports (`main.py`)
- Instantiate student objects using both the dataclass and the Pydantic model.​
- Display student details and performance reports.​
- Serialize validated student data to a dictionary and JSON for real-world use cases like saving reports.

#### Instructions:

- Use boilerplate.
- Ensure your code is well-organized and includes comments for clarity.
- Test your code thoroughly to ensure it meets the requirements.


