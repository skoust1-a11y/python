# Problem Statement: Wellbeing Coach – Your Personalized 5-Minute Mental Booster
 
## Context
 
In today’s fast-paced digital lifestyle, people experience increased stress, anxiety, and burnout due to long working hours, continuous screen exposure, and limited personal interaction. Most existing wellness solutions require extended sessions or manual input, which discourages consistent usage.
 
**Key Real World Challenges:**
Early signs of stress often go unnoticed.
Most wellness apps lack meaningful personalization.
Users need quick, convenient support—not lengthy commitments.
Overwhelming data and fragmented experiences reduce engagement.
 
## Project Goal
 
Design an AI-powered Wellbeing Coach that suggests **personalized 5-minute micro-activities** to help users improve their emotional wellbeing.
Think through what data and context your solution should consider and justify your approach.
 
---
 
## Problem Description
 
This project focuses on building a **Python-based Wellbeing Coach Application** that:
 
- Understands user inputs or context to identify their emotional state.
- Generates relevant 5-minute activities that provide instant relief or focus.
- Learns from interactions to improve future recommendations.
- Leverages **LLM-based assistanc**e** to provide intuitive, supportive responses.
 
---
 
## Functional Requirements
You are free to design how your system works—as long as your solution meets the intent of helping users feel better in 5 minutes.
 
Your solution might consider:
- Emotional or contextual cues from user input.
- Quick activities like mindfulness, movement, journaling prompts, or music.
- User feedback to refine recommendations over time.
- AI-generated personalized suggestions or interactions.
 
The technical and functional approach is up to you—ensure it aligns with the project goals and can be demonstrated in a working prototype.
 
---
 
## Technical Details
 
**Programming Language:** Python
 
**Libraries & Tools:**
 
| Library/Tool | Purpose |
|-------------|---------|
| `fastapi`   | Build backend API |
| `uvicorn`   | Run FastAPI server |
| `requests`  | Communicate with Gemini / Ollama APIs |
| `dotenv`    | Manage environment variables securely |
 
**Environment Variables:**
 
| Variable | Purpose |
|---------|---------|
| `GEMINI_API_KEY` | Authenticate requests to Gemini API |
| `OLLAMA_MODEL_PATH` | Path to local Ollama model instance |
 
**Note: You may also explore local models and experiment with cloud or private LLM deployments.**
 
---
 
