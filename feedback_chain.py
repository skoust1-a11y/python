import os
from dotenv import load_dotenv
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel

from langchain.prompts import ChatPromptTemplate
# from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema.output_parser import StrOutputParser
# from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from llmsetup import llm

# -------------------------------
# Environment setup
# -------------------------------


# -------------------------------
# Step 1: Sentiment Classification Prompt
# -------------------------------
sentiment_classify_prompt = ChatPromptTemplate.from_messages([
    ("system","Analyze the sentiment of the customer feedback."
     "Respond with ONLY one word: POSITIVE,NEGATIVE,NEUTRAL."),
     ("user","{feedback}")
])

# -------------------------------
# Step 2: Urgency Classification Function
# -------------------------------
def classify_urgency(sentiment_result : str) -> dict:
    sentiment = sentiment_result.strip().upper()
    if sentiment == 'NEGATIVE':
        urgency = 'HIGH'
        priority = "Immediate response required"
    elif sentiment == 'POSITIVE':
        urgency = 'LOW'
        priority = "Acknowledge and thank"
    else:
        urgency = 'MEDIUM'
        priority = "Standard response timeline"
    return {
         'sentiment':sentiment,
         'urgency':urgency,
         'priority' : priority
     }

urgency_classifier = RunnableLambda(classify_urgency)   

# -------------------------------
# Step 3: Response Strategy Prompt
# -------------------------------
strategy_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a customer service manager. Based on the sentiment analysis, "
               "provide a specific response strategy.\n\n"
               "Sentiment: {sentiment}\n"
               "Urgency: {urgency}\n"
               "Priority: {priority}"),
    ("user", "Generate a 2-3 sentence response strategy for this customer.")
])


# -------------------------------
# Step 4: Full LCEL Chain
# -------------------------------
analysis_chain = (
    sentiment_classify_prompt |
    llm |
    StrOutputParser() |
    urgency_classifier |
    strategy_prompt |
    llm |
    StrOutputParser()
)

sentiment_chain = (
    sentiment_classify_prompt |
    llm |
    StrOutputParser() |
    urgency_classifier
)

# -------------------------------
# Step 5: FastAPI Setup
# -------------------------------
app = FastAPI(title="Travel Feedback Analyzer - LCEL")

class FeedbackInput(BaseModel):
    feedback: str

class AnalysisFeedBack(BaseModel):
    sentiment : str
    urgency : str
    strategy : str

@app.post('/analyze_feedback',response_model=AnalysisFeedBack)
def analysis_feedback(inputs : FeedbackInput):
   """
    Accepts JSON input: {"feedback": "..."}
    Returns sentiment, urgency, and response strategy.
    """
   try:
       strategy = analysis_chain.invoke({"feedback":inputs.feedback})
       sentiment_analysis = sentiment_chain.invoke({"feedback":inputs.feedback})

       return AnalysisFeedBack(
           sentiment=sentiment_analysis.get('sentiment'),
           urgency=sentiment_analysis.get('urgency'),
           strategy=strategy
        )  
   except Exception as e:
       raise HTTPException(
           status_code=500,
           detail=f"The Error is : {str(e)}"
       )






if __name__ == "__main__":
    import uvicorn
    uvicorn.run("feedback_chain:app", host="0.0.0.0", port=8000)
