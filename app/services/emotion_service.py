from ..config import settings
from ..services.llm_service import call_gemini_llm,call_gemma_llm
from openai import OpenAIError
from fastapi import HTTPException
import httpx
from ..utils.prompts import WELLBEING_PROMPT
import json

class EmotionService:
    def detect_emotion(self, text: str) -> dict:
        if settings.get_env("TEST_WITH_MOCK_DATA", "false").lower() == "true":
            # Return mock data
            return {
                "emotion": "joy",  # Example mock emotion
                "confidence": 0.9,
                "intensity": "high"
            }
        
        llm_result = self.llm_detect_emotion(text)
        return llm_result
        # rule_result = self.rule_based_detection(text)

        # if self.should_use_llm(rule_result):
        #     llm_result = self.llm_detect_emotion(text)
        #     return self.choose_better_emotion(rule_result, llm_result)



        # return rule_result


    def rule_based_detection(self, text: str) -> dict:
        pass


    def llm_detect_emotion(self, text: str) -> dict:
        try:
            prompt = WELLBEING_PROMPT.get('get_emotion_state') + '\n' + WELLBEING_PROMPT.get('patient') + text
            result = call_gemini_llm(prompt=prompt)
            emotion_data = json.loads(result)
            return emotion_data
        except (RuntimeError,httpx.ConnectError,OpenAIError,Exception) as e:
             # Log or print the error if needed
            # print(f"Gemini LLM failed: {str(e)}")
             print("Gemini failed:", str(e))
        try:
            prompt = WELLBEING_PROMPT.get('get_emotion_state','') + '\n' + WELLBEING_PROMPT.get('patient','') + text
            result = call_gemma_llm(prompt=prompt)
            emotion_data = json.loads(result)
            return emotion_data
        except RuntimeError as e:
            raise HTTPException(
                status_code=404,
                detail=f'MISSING ENV KEYS FOR LLM MODELS {str(e)}'
            )
        except httpx.ConnectError as e:
            raise HTTPException(
                status_code=404,
                detail=f'MISSING ENV KEYS FOR LLM MODELS {str(e)}'
            )
        except OpenAIError as e:
             raise HTTPException(
                status_code=404,
                detail=f'MISSING ENV KEYS FOR LLM MODELS {str(e)}'
            )
        except Exception as e:
              raise HTTPException(
                status_code=404,
                detail=f'MISSING ENV KEYS FOR LLM MODELS {str(e)}'
            )

    def should_use_llm(self, rule_result: dict) -> bool:
        return rule_result["confidence"] < 0.65


    def choose_better_emotion(self, rule_result: dict, llm_result: dict) -> dict:
        return llm_result if llm_result["confidence"] > rule_result["confidence"] else rule_result