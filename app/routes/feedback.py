from fastapi import APIRouter

router = APIRouter(prefix="/feedback", tags=["feedback"])

@router.post("/")
def submit_feedback():
    return {"message": "Feedback submitted"}

@router.get("/")
def get_feedback():
    return {"feedback": []}