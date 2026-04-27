from pydantic import BaseModel,field_validator

class StudentModel(BaseModel):
    name : str
    marks : float
    age : int
    guardian_number : int

    @field_validator('name')
    def name_validator(cls,value):
        if not value.strip():
            raise ValueError('Empty Name is given')
        return value
    
    @field_validator('age')
    def age_validator(cls,value):
        if value <= 0:
            raise ValueError('Invalid Age')
        return value
    
    @field_validator('marks')
    def marks_validator(cls,value):
        if value < 0 or value > 100:
            raise ValueError('Inavlid marks')
        return value
    
    @field_validator('guardian_number')
    def phone_validator(cls,value):
        format_str = str(value)
        if len(format_str) != 10:
            raise ValueError('Invalid Guardian Phone Number')
        return value