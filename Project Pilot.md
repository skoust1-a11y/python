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

### 1. Task Capture & Organization

- Allow users to add tasks with details like deadline, category, effort level, and context.
- Group tasks into projects, goals, or daily plans.

### 2. Intelligent Prioritization

- Automatically rank tasks using urgency, importance, and time constraints.
- Suggest task order for the day based on available time and focus level.

### 3. Smart Work Breakdown

- Break large tasks into smaller actionable micro steps.
- Suggest estimated time blocks for focused work sessions.

### 4. Focus & Accountability Assistance

- Provide focus session timers (e.g., Pomodoro technique).
- Send motivational nudges, break reminders, and progress prompts.

### 5. Productivity Insights

- Track completed tasks, consistency streaks, and time usage.
- Generate weekly summaries and personalized improvement tips.

## AI Integration

- Use **LLM models** to analyze user behavior, refine prioritization logic, and generate focus guidance.
- Adapt task recommendations and productivity strategies over time.

## Technical Details

**Programming Language:** Python

**Libraries/Tools:**

| Tool / Library | Purpose |
|---|---|
| **FastAPI** | Backend API development |
| **Uvicorn** | Server execution |
| **Pydantic** | Data validation & modeling |
| **Requests** | Communication with AI models |
| **python-dotenv** | Environment variable management |

**Environment Variables:**

| Variable Name | Purpose |
|---|---|
| `GEMINI_API_KEY` | Authentication for Gemini AI model |
| `OLLAMA_MODEL_PATH` | Path for local Ollama model instance |
