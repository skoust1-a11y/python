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

## Functional Requirements

### 1. User Profile & Skill Assessment

- Collect user interests, education, skill level, and career goals.
- Analyze strengths and gaps to identify opportunities for improvement.

### 2. Career Path Recommendation

- Suggest suitable roles (e.g., Data Analyst, Web Developer, UI/UX Designer).
- Explain why a role fits the user's profile with examples and industry context.

### 3. Personalized Skill Roadmap

- Provide step-by-step learning paths with curated resources.
- Suggest timelines for beginner, intermediate, and advanced learners.

### 4. Portfolio & Resume Guidance

- Recommend real-world mini-projects to showcase skills.
- Provide resume formatting tips and sample templates.

### 5. Interview Preparation Support

- Generate mock technical and HR interview questions.
- Provide evaluation feedback and improvement suggestions.

## AI Integration

- Use **LLM models** to generate career path recommendations, learning plans, and interview coaching.
- Continuously refine suggestions based on user progress and feedback.

## Technical Details

**Programming Language:** Python

**Libraries/Tools:**

| Tool / Library | Purpose |
|---|---|
| **FastAPI** | Backend API services |
| **Uvicorn** | Server execution |
| **Pydantic** | Request/response validation |
| **Requests** | Communication with AI model APIs |
| **python-dotenv** | Secure environment variable handling |

**Environment Variables:**

| Variable Name | Purpose |
|---|---|
| `GEMINI_API_KEY` | Authentication for Gemini AI model |
| `OLLAMA_MODEL_PATH` | Path for local Ollama model instance |
