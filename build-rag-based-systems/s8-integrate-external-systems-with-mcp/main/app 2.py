import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from main.routes.routes import router, set_agent_service
from main.services.agent_service import AgentService

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

agent_service = AgentService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize agent on startup"""
    logger.info("Initializing Product Review Sentiment Analysis Agent...")
    try:
        await agent_service.initialize()
        set_agent_service(agent_service)
        logger.info("✓ Agent ready for product review analysis")
    except Exception as e:
        logger.error(f"✗ Agent init failed: {e}")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Product Review Sentiment Analysis API",
    description="MCP-powered sentiment analysis for product reviews using Hugging Face models",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router)


@app.get("/")
async def root():
    return {
        "service": "Product Review Sentiment Analysis",
        "status": "running",
        "endpoints": {
            "analyze": "/api/reviews/analyze",
            "docs": "/docs"
        }
    }
