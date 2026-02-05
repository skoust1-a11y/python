from fastapi import FastAPI, HTTPException
from models import ResumeRequest, ResumeResponse
from services import process_resume

app = FastAPI(
    title="Resume Screening API",
    description="API for screening resumes using CrewAI Flows",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {"message": "Resume Screening API Boilerplate is running"}

@app.post("/screen", response_model=ResumeResponse)
async def screen_resume(request: ResumeRequest):
    """
    Screen a resume and provide AI-based feedback.
    
    TODOs:
    1. Validate required fields (optional if Pydantic handles it, but good practice).
    2. Call the process_resume service function.
    3. Map the flow state to the ResumeResponse model.
    4. Handle errors with HTTPException.
    """
    # TODO: Step 1 - Call Service
    # Hint: await process_resume(request.candidate_name, request.resume_text, request.applying_for)
    
    # TODO: Step 2 - Create Response
    # Hint: Return ResumeResponse with data from the flow state (flow.state.candidate_name, etc.)
    
    # TODO: Step 3 - Handle Errors
    
    raise NotImplementedError("This route is not yet implemented. Please complete the TODO steps above.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
