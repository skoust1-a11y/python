# Wellbeing Coach - Your Personalized 5-Minute Mental Booster

An AI-driven mental wellness API that detects user mood and suggests 5-minute activities like breathing exercises, stretching, journaling, or music therapy.

---

## Problem Statement: Wellbeing Coach – Your Personalized 5-Minute Mental Booster

### Context

In today’s fast-paced digital lifestyle, people experience increased stress, anxiety, and burnout due to long working hours, continuous screen exposure, and limited personal interaction. Most existing wellness solutions require extended sessions or manual input, which discourages consistent usage.

**Common Challenges:**

- **Lack of Real-Time Emotional Awareness:** Users often struggle to recognize early signs of stress or mental fatigue.
- **Limited Personalization:** Generic wellness recommendations fail to consider mood, environment, or time.
- **Low Engagement:** Many wellbeing apps require long sessions, causing users to skip them.
- **Fragmented Data:** Emotional and wellbeing data spread across platforms makes insight difficult.
- **Absence of Quick Support:** Users need immediate relief, not long programs.

### Project Goal

Develop an **AI-powered Wellbeing Coach** that analyzes the user’s **mood and location (city)** to recommend a **personalized 5-minute micro-activity** that improves mental wellbeing instantly.

---

## Problem Description

This project focuses on building a **Python-based Wellbeing Coach Application** that:

- Detects user mood through emotion recognition or manual input.
- Recommends **short, effective 5-minute activities** such as breathing, stretching, journaling, or music therapy.
- Learns and personalizes recommendations based on past interactions and feedback.
- Integrates **LLM APIs** to provide context-aware and human-like responses.

---

## Functional Requirements

### 1. Mood Detection

- Analyze user text input to detect mood using AI models.
- Provide manual mood selection (e.g., Stressed, Anxious, Happy).
- Store mood history for user-based personalization.

### 2. Context Awareness

- Detect user’s **location (city)** to personalize activity suitability.
- Example: Suggest **stretching** at home, **deep breathing** in an office setting.

### 3. Activity Recommendation System

Recommends short mental wellbeing activities such as:

- 5-minute breathing or mindfulness sessions
- Light stretching or body-mobility exercises
- Listening to calming music or ambient sounds
- Gratitude journaling prompts
- Calling or messaging a loved one

Also includes:

- User feedback option: “Helpful” / “Not Helpful”
- Feedback loop to improve suggestions over time

### 6. AI Integration

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
