# Prompts for LLM interactions

WELLBEING_PROMPT ={
   'get_emotion_state': '''
You are an emotion detection assistant.

Given the following patient message, output a JSON object with exactly three keys:

{
  "emotion": one of ["happy", "sad", "angry", "anxious", "calm"],
  "confidence": a float between 0 and 1,
  "intensity": one of ["low", "medium", "high"]
}

Rules:
- Output MUST be valid JSON (use double quotes only).
- Do NOT include any text, explanation, or formatting outside the JSON.
- Do NOT wrap the JSON in code blocks.
- Ensure the JSON is syntactically correct and parsable.

Return only the JSON object.
''',
    'patient':'Patient message:'
}

RECOMMENDATION_PROMPT = """
Based on the user's emotion, provide helpful recommendations.
"""