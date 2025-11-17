# Project Pilot – Your AI Productivity Manager

An AI-driven productivity companion that helps users plan tasks, prioritize work, track progress, and maintain focus through personalized productivity strategies and real-time guidance.

## Problem Statement: Project Pilot – Your AI Productivity Manager

### Context

With the increasing complexity of daily professional and academic workloads, individuals often struggle to plan, prioritize, and complete tasks efficiently. Existing productivity tools are often rigid, require manual setup, or lack personalized guidance that adapts to changing work patterns and energy levels.

Common challenges include:

- **Overwhelming Task Lists:** Users have too many tasks without clear prioritization.
- **Poor Time Management:** Difficulty estimating effort and allocating time effectively.
- **Inconsistent Productivity:** Peaks and dips in focus lead to unfinished tasks.
- **Lack of Personalization:** Productivity systems rarely adapt to individual work habits.
- **No Real-Time Support:** Users need guidance during work, not just static task lists.

This project introduces **Project Pilot**, an **AI-powered productivity manager** that optimizes planning, breaks work into achievable steps, and provides real-time support to help users stay consistent and focused.

## Problem Description

The goal of this project is to develop a **Python-based Productivity Management Application** that:

- Captures and organizes user tasks and work context.
- Prioritizes tasks based on urgency, importance, and energy levels.
- Breaks goals into manageable micro tasks and timelines.
- Provides real-time focus guidance and accountability check-ins.
- Tracks productivity patterns and recommends improvements.

## Functional Requirements

### 1. Task & Workload Detection
- Allow users to add tasks with details such as deadlines, categories, effort levels, and context.  
- Capture projects, goals, and daily plans for structured organization.  
- Detect task size and identify tasks that require breakdown into smaller steps.

### 2. Productivity Context Awareness
- Analyze urgency, importance, time constraints, and user focus levels.  
- Understand available time in the user’s day to tailor prioritization.  
- Interpret user habits, consistency streaks, and time usage patterns to generate insights.

### 3. Smart Productivity Recommendation System
Recommends productivity actions such as:

- Automatically prioritized task order for the day.  
- Suggested micro-steps for large tasks and estimated time blocks.  
- Focus session timers (e.g., Pomodoro) and break reminders.  
- Motivational nudges and progress prompts.  
- Weekly summaries and personalized improvement tips.  

Also includes:

- Tracking completed tasks and productivity streaks.  
- Continuous feedback loop to refine recommendations based on user behavior.
- User feedback option: “Helpful” / “Not Helpful”
- Feedback loop to improve suggestions over time

### 4. AI Integration

- Use **LLM Models** for dynamic and personalized well-being activity generation.

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

---
