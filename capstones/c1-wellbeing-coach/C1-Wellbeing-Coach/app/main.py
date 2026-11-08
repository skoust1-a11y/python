from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from .exceptions.Custom_Exceptions import GibberishPromptError
from .routes.wellbeing import router as wellbeing_router
from .routes.feedback import router as feedback_router
from .config.logging_config import logger
from .config.settings import settings
from .config.database import initialize_database
import uvicorn
import os

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Wellbeing Coach",
    description="AI-powered wellbeing coaching application",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(GibberishPromptError)
async def gibberish_prompt_handler(request: Request, exc: GibberishPromptError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})

app.include_router(wellbeing_router)
app.include_router(feedback_router)

@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info(f"Starting {settings.app_name} application")
    logger.info(f"Debug mode: {settings.debug}")
    initialize_database()
    logger.info("Application startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown."""
    logger.info("Shutting down Wellbeing Coach application")

@app.get("/")
def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to Wellbeing Coach API", "version": "1.0.0"}

# @app.get("/health")
# def health_check():
#     """Health check endpoint for monitoring."""
#     logger.debug("Health check requested")
#     return {"status": "healthy", "service": "wellbeing-coach"}

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