from pydantic import BaseModel, Field


class ProductReviewRequest(BaseModel):
    """Request model for product review analysis."""
    product: str = Field(description="Product name to analyze reviews for")


class ProductReviewResponse(BaseModel):
    """Response model for product review analysis."""
    insights: str
    status: str = "success"
    message: str = "Review analysis completed successfully"
