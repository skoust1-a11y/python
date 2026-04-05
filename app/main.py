from fastapi import FastAPI
from .routes.wellbeing import router as wellbeing_router
from .routes.feedback import router as feedback_router
import uvicorn
import os

app = FastAPI(title="Wellbeing Coach", description="AI-powered wellbeing coaching application")

app.include_router(wellbeing_router)
app.include_router(feedback_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Wellbeing Coach API"}

# def main():
#     """Main entry point for the application."""
#     host = os.getenv("HOST", "0.0.0.0")
#     port = int(os.getenv("PORT", 0000))
#     debug = os.getenv("DEBUG", "False").lower() == "true"

#     uvicorn.run(
#         "app.main:app",
#         host=host,
#         port=port,
#         reload=debug,
#         log_level="info",
#     )


# if __name__ == "__main__":
#     main()