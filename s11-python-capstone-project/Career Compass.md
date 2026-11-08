# Problem Statement: Career Compass – Your AI Career Growth Partner

An AI-powered career development companion that helps users discover career paths, build skills, prepare for interviews, and achieve long-term growth through personalized recommendations.

---

### Context

In today’s fast-changing job market, people struggle to find the right career direction, identify skills to learn, and stay confident in their growth journey. Traditional career guidance is often generic, expensive, or hard to access.

**Key Real World Challenges:**  
- Users are unsure which roles match their strengths and interests.  
- Skill gaps are unclear and difficult to prioritize.  
- Too many learning resources lead to confusion.  
- Guidance is rarely personalized to background or goals.  
- Interview preparation and portfolio-building are unstructured.  

## Project Goal

Design an AI-powered Career Growth Partner that provides **personalized career-path suggestions, skill roadmaps, interview coaching, and growth tracking** to help users progress effectively.

Think through what data and context your solution should consider and justify your approach.

---

## Problem Description

This project focuses on building a **Python-based Career Guidance Application** that:

- Assesses the user’s interests, education, skills, and aspirations.  
- Recommends career paths and suitable job roles.  
- Generates personalized learning and skill development plans.  
- Suggests portfolio-building tasks and resume tips.  
- Supports interview preparation through AI-driven Q&A feedback.

---

## Functional Requirements

You are free to design how your system works—as long as your solution meaningfully supports career growth.

Your solution might consider:  

- Collecting user background, skills, and goals.  
- Detecting strengths, weaknesses, and skill gaps.  
- Personalized career recommendations and role-fit insights.  
- Step-by-step skill roadmaps and curated learning resources.  
- Portfolio project ideas and resume improvement suggestions.  
- Mock interview practice with AI feedback.  
- User feedback to refine future recommendations.  

The technical and functional approach is up to you—ensure it aligns with project goals and can be demonstrated in a working prototype.

---

## Technical Details

**Programming Language:** Python

**Libraries & Tools:**

| Library/Tool | Purpose |
|--------------|---------|
| fastapi | Build backend API |
| uvicorn | Run FastAPI server |
| requests | Communicate with Gemini / Ollama APIs |
| dotenv | Manage environment variables |

**Environment Variables:**

| Variable | Purpose |
|----------|---------|
| GEMINI_API_KEY | Authenticate requests to Gemini API |
| OLLAMA_MODEL_PATH | Path to local Ollama model instance |

**Note: You may also explore local models and experiment with cloud or private LLM deployments.**

---
