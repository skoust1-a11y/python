# Health Mate – Your Smart Lifestyle Optimizer

An AI-powered wellness companion that tracks daily routines, identifies lifestyle gaps, and recommends actionable micro-improvements for healthier living across sleep, nutrition, hydration, fitness, and stress balance.

## Problem Statement: Health Mate – Your Smart Lifestyle Optimizer

### Context

Modern lifestyles often lead to irregular sleep schedules, unhealthy eating patterns, prolonged inactivity, and high stress levels. While fitness apps and wellness platforms exist, they often require manual logging, lack personalization, or focus on extreme goals rather than sustainable daily habits.

Common challenges include:

- **Lack of Daily Awareness:** Users struggle to recognize unhealthy patterns in real-time.
- **Generic Recommendations:** Most wellness suggestions are not tailored to personal lifestyle, preferences, or health goals.
- **Low Accountability:** Users find it difficult to maintain consistency without reminders and progress tracking.
- **Fragmented Health Data:** Sleep, steps, calories, and mental health data are often spread across different apps.
- **Unsustainable Routines:** People need guidance for small, achievable improvements instead of drastic lifestyle changes.

This project introduces **Health Mate**, an **AI-driven lifestyle optimizer** designed to help users build and maintain healthy habits through real-time insights and personalized micro-actions.

## Problem Description

The goal of this project is to create a **Python-based Smart Lifestyle Optimization Application** that:

- Monitors routine data (manual input or device sync).
- Identifies health patterns and potential risk habits.
- Recommends small daily habit adjustments to improve overall wellbeing.
- Suggests nutrition, hydration, sleep, fitness, and mindfulness activities.
- Tracks progress and adapts guidance over time.
## Functional Requirements

### 1. Lifestyle Pattern Detection
- Accept manual or synced data (sleep hours, steps, meals, water intake, mood, etc.).  
- Store and update daily habit logs.  
- Detect patterns such as sleep deficit, dehydration, long sedentary hours, or stress buildup.  

### 2. Health Context Awareness
- Understand the user’s routine, habits, and health goals.  
- Generate daily or weekly wellbeing summaries based on tracked patterns.  
- Adapt insights based on ongoing lifestyle changes and progress.

### 3. Personalized Habit Recommendation System
Recommends achievable wellbeing actions such as:

- Drink a glass of water  
- Take a 3-minute stretch break  
- Adjust bedtime routine  
- Choose a healthier meal alternative  

Also includes:

- Adaptive suggestions based on user routines and goals.  
- Goal setting for steps, water intake, and other habits.  
- Motivational nudges and reminders.  
- Progress tracking with visual trends and “done/skip” action logging.

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
