from pydantic import BaseModel, Field, field_validator
from typing import List

class StudentModel(BaseModel):
    name: str = Field(..., min_length=1)
    age: int = Field(..., gt=0, lt=120)
    marks: float = Field(..., ge=0, le=100)
    guardian_number: str

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty or just whitespace')
        return v

    @field_validator('guardian_number')
    @classmethod
    def validate_phone(cls, v):
        if len(v) < 10:
            raise ValueError('Guardian number must be at least 10 digits')
        return v