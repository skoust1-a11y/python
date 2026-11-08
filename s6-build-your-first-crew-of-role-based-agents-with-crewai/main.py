from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from models import ProductReviewRequest, ProductReviewResponse
import uvicorn
from services import create_review_analysis_crew
app = FastAPI(
    title="Product Review Analysis API",
    description="API for analyzing product reviews and generating actionable insights using CrewAI",
    version="1.0.0"
)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Product Review Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "POST /analyze": "Analyze product reviews and generate insights",
            "GET /health": "Health check endpoint"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/analyze", response_model=ProductReviewResponse)
async def analyze_product_reviews(request: ProductReviewRequest):
    """
    Analyze product reviews and generate actionable insights.

    Args:
        request: ProductReviewRequest containing the product name

    Returns:
        ProductReviewResponse with generated insights report
    """
    try:
        if not request.product or not request.product.strip():
            raise HTTPException(
                status_code=400,
                detail="Product name must not be empty or whitespace-only"
            )

        result = create_review_analysis_crew(product=request.product)

        return ProductReviewResponse(
            insights=result.raw,
            status='success',
            message='Review analysis completed successfully'
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing product reviews: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

