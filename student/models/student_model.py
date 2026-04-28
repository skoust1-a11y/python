from pydantic import BaseModel, field_validator, ValidationError
from typing import Optional


class StudentModel(BaseModel):
    name: str
    age: int
    marks: float
    guardian_number: str

    # --- Validators ---

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, value):
        if not value or not value.strip():
            raise ValueError("Name cannot be empty")
        return value

    @field_validator("age")
    @classmethod
    def age_valid(cls, value):
        if value <= 0:
            raise ValueError("Age must be greater than 0")
        if value > 120:
            raise ValueError("Age seems unrealistic")
        return value

    @field_validator("marks")
    @classmethod
    def marks_valid(cls, value):
        if value < 0 or value > 100:
            raise ValueError("Marks must be between 0 and 100")
        return value

    @field_validator("guardian_number")
    @classmethod
    def guardian_number_valid(cls, value):
        if not value.isdigit():
            raise ValueError("Guardian number must contain only digits")
        if len(value) != 10:
            raise ValueError("Guardian number must be 10 digits")
        return value