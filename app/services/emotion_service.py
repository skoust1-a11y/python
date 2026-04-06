import logging

from ..config.settings import settings
from ..services.llm_service import call_gemini_llm,call_gemma_llm
from openai import OpenAIError
from fastapi import HTTPException
import httpx
from ..utils.prompts import WELLBEING_PROMPT
import json



logger = logging.getLogger(__name__)


class EmotionService:
    def __init__(self):
        logger.info("EmotionService initialized")

    def detect_emotion(self, text: str) -> dict:
        logger.debug(f"Detecting emotion for text: '{text[:50]}...'")

        if settings.get_env("TEST_WITH_MOCK_DATA", "false").lower() == "true":
            logger.debug("Using mock emotion data for testing")
            # Return mock data
            result = {
                "emotion": "joy",  # Example mock emotion
                "confidence": 0.9,
                "intensity": "high"
            }
            logger.debug(f"Mock emotion result: {result}")
            return result
        
        logger.debug("Using LLM for emotion detection")
        llm_result = self.llm_detect_emotion(text)
        logger.debug(f"LLM emotion result: {llm_result}")
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
        confidence = rule_result.get("confidence", 0)
        use_llm = confidence < 0.65
        logger.debug(f"Rule-based confidence: {confidence}, using LLM: {use_llm}")
        return use_llm


    def choose_better_emotion(self, rule_result: dict, llm_result: dict) -> dict:
        rule_conf = rule_result.get("confidence", 0)
        llm_conf = llm_result.get("confidence", 0)
        chosen = llm_result if llm_conf > rule_conf else rule_result
        logger.debug(f"Chose {'LLM' if llm_conf > rule_conf else 'rule-based'} result (LLM: {llm_conf}, Rule: {rule_conf})")
        return chosen