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

### 1. Lifestyle Data Tracking

- Accept manual input or synced data (sleep hours, steps, meals, water intake, mood, etc.).
- Store and update daily habit logs.

### 2. Pattern Detection & Health Insights

- Identify patterns such as sleep deficit, dehydration, long sedentary hours, or stress buildup.
- Generate daily or weekly wellbeing summaries.

### 3. Personalized Habit Recommendations

- Provide small, achievable actions such as:
  - Drink a glass of water
  - Take a 3-minute stretch break
  - Adjust bedtime routine
  - Choose a healthier meal alternative
- Adapt suggestions based on user routines and goals.

### 4. Goal Setting & Motivation

- Allow users to set health goals (e.g., steps/day, water intake).
- Provide motivational nudges and reminders.

### 5. Progress Tracking

- Display visual progress trends over time.
- Allow users to mark actions as “done” or “skip”.

## AI Integration

- Use **LLM models** to generate personalized recommendations and lifestyle coaching messages.
- Learn from user engagement patterns to refine future suggestions.

## Technical Details

**Programming Language:** Python

**Libraries/Tools:**

| Tool / Library | Purpose |
|---|---|
| **FastAPI** | Backend API development |
| **Uvicorn** | Running FastAPI server |
| **Pydantic** | Data validation & models |
| **Requests** | API communication (AI services) |
| **python-dotenv** | Secure environment variable management |

**Environment Variables:**

| Variable Name | Purpose |
|---|---|
| `GEMINI_API_KEY` | Authentication for Gemini AI model |
| `OLLAMA_MODEL_PATH` | Path to local Ollama model instance |
