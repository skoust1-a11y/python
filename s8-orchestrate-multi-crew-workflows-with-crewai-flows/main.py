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

    Pydantic validates required fields on ResumeRequest automatically.
    """
    try:
        flow, result = await process_resume(request.candidate_name, request.resume_text, request.applying_for)

        return ResumeResponse(
            candidate_name=flow.state.candidate_name,
            classified_role=flow.state.classified_role,
            feedback=flow.state.feedback,
            evaluator=flow.state.evaluator,
            success=True
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing resume: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
