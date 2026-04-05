from ..config import settings


class EmotionService:
    def detect_emotion(self, text: str) -> dict:
        if settings.get_env("TEST_WITH_MOCK_DATA", "false").lower() == "true":
            # Return mock data
            return {
                "emotion": "joy",  # Example mock emotion
                "confidence": 0.9,
                "intensity": "high"
            }
        
        rule_result = self.rule_based_detection(text)

        if self.should_use_llm(rule_result):
            llm_result = self.llm_detect_emotion(text)
            return self.choose_better_emotion(rule_result, llm_result)

        return rule_result


    def rule_based_detection(self, text: str) -> dict:
        pass


    def llm_detect_emotion(self, text: str) -> dict:
        pass


    def should_use_llm(self, rule_result: dict) -> bool:
        return rule_result["confidence"] < 0.65


    def choose_better_emotion(self, rule_result: dict, llm_result: dict) -> dict:
        return llm_result if llm_result["confidence"] > rule_result["confidence"] else rule_result