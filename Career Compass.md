# Career Compass – Your AI Career Growth Partner

An AI-powered career development companion that guides users in choosing the right career paths, improving skills, building portfolios, preparing for interviews, and achieving long-term professional growth.

## Problem Statement: Career Compass – Your AI Career Growth Partner

### Context

In today's rapidly evolving job market, individuals often struggle to identify suitable career options, skill requirements, and growth strategies. Traditional career guidance resources are either generic, costly, or inaccessible. As a result, learners and professionals lack direction, confidence, and actionable plans to progress effectively.

Common challenges include:

- **Unclear Career Pathways:** Users are often unsure which roles align with their interests and strengths.
- **Skill Gap Confusion:** It's difficult to determine which skills to learn and where to begin.
- **Overwhelming Learning Resources:** The abundance of online content leads to confusion and inconsistency in learning.
- **Limited Personalized Guidance:** Career recommendations are often generic and not tailored to individual aspirations, learning pace, or background.
- **Interview Preparation Barriers:** Users may lack structured guidance for mock interviews and portfolio-building.

This project introduces **Career Compass**, an **AI-powered career growth partner** that provides tailored career recommendations, skill roadmaps, interview preparation, and progress tracking.

## Problem Description

The goal of this project is to build a **Python-based Career Guidance Application** that:

- Assesses the user’s interests, skills, and personality.
- Recommends best-fit career paths and job roles.
- Generates personalized learning and skill development roadmaps.
- Provides portfolio and resume-building suggestions.
- Guides interview practice using AI-powered Q&A feedback.

# Functional Requirements

## 1. Career & Skill Detection
- Collect and analyze the user's interests, education background, skills, and career goals.  
- Detect strengths, weaknesses, and skill gaps using assessment logic.  
- Continuously refine the profile based on user interactions and progress updates.

## 2. Career Context Awareness
- Understand the user's background, learning style, and career aspirations to personalize guidance.  
- Identify industry trends relevant to the user's chosen field.  
- Adapt recommendations based on the user’s current skill level (beginner/intermediate/advanced).

## 3. Career Growth Recommendation System
Recommends personalized career development actions such as:

- Suitable job roles (e.g., Data Analyst, Web Developer, UI/UX Designer) with role-fit explanations.  
- Step-by-step skill roadmaps with curated learning resources.  
- Real-world mini-projects to help build the user’s portfolio.  
- Resume formatting tips and sample templates.  
- Mock HR and technical interview questions with improvement feedback.

Also includes:

- User feedback option: “Helpful” / “Not Helpful”.  
- Continuous feedback loop to improve future recommendations.

## 4. AI Integration

- Use **LLM models** to generate career path recommendations, learning plans, and interview coaching.
- Continuously refine suggestions based on user progress and feedback.

---

## Technical Details

**Programming Language:** Python

### Libraries & Tools

| Library/Tool | Purpose |
|-------------|---------|
| `fastapi`   | Build backend API |
| `uvicorn`   | Run FastAPI server |
| `requests`  | Communicate with Gemini / Ollama APIs |
| `dotenv`    | Manage environment variables securely |

### Environment Variables

| Variable | Purpose |
|---------|---------|
| `GEMINI_API_KEY` | Authenticate requests to Gemini API |
| `OLLAMA_MODEL_PATH` | Path to local Ollama model instance |
