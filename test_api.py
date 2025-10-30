from fastapi import FastAPI, Path
from typing import Optional
from pydantic import BaseModel

# To run the app, use the command: uvicorn myapi:app --reload
app = FastAPI()

# Root Endpoint (index or homepage)
@app.get("/")
def index():
    return {"Name": "Vy"}

# Sample dictionnary
students = {
    1: {"name": "Vy", "age": 22},
    2: {"name": "Viviane", "age": 18},
}

class Student(BaseModel):
    name: str
    age: int
    year: Optional[int] = None

class UpdateStudent(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    year: Optional[int] = None

# Endpoint to get student details by ID (Parameterized Endpoint)
@app.get("/get-student/{student_id}")
def get_student(student_id: int = Path(..., description="The ID of the student to retrieve", gt = 0, lt = 4)): # Path parameter with validation
    return students[student_id]
    
# Endpoint to get student details by name (Query Parameter Endpoint)
@app.get("/get-student-by-name")
def get_student_by_name(*, student_name: Optional[str] = None, test: int): # Non-optional query parameter have to be placed after optional ones, but with asterisk (*) we can place them in any order
    for student_id in students:
        if students[student_id]["name"].lower() == student_name.lower():
            return students[student_id]
    return {"Error": "Student not found"}

# Endpoint to create a new student (Using Request Body)
@app.post("/create-student/{student_id}")
def create_student(student_id: int, student: Student):
    if student_id in students:
        return {"Error": "Student ID already exists"}
    students[student_id] = student
    return students[student_id]

# Endpoint to update an existing student (Using Request Body)
@app.put("/update-student/{student_id}")
def update_student(student_id: int, student: UpdateStudent):
    if student_id not in students:
        return {"Error": "Student ID does not exist"}

    if student.name:
        students[student_id]["name"] = student.name
    if student.age:
        students[student_id]["age"] = student.age
    if student.year:
        students[student_id]["year"] = student.year

    return students[student_id]

# Endpoint to delete a student by ID
@app.delete("/delete-student/{student_id}") 
def delete_student(student_id: int):
    if student_id not in students:
        return {"Error": "Student ID does not exist"}
    del students[student_id]
    return {"Message": "Student deleted successfully"}