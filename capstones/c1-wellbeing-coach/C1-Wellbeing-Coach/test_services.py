import json
from app.services.emotion_service import EmotionService
from app.services.recommendation_service import RecommendationService

def test_services():
    # Load dummy data
    with open('data/activities.json', 'r') as f:
        test_data = json.load(f)

    emotion_service = EmotionService()
    recommendation_service = RecommendationService()

    for i, sample in enumerate(test_data, 1):
        print(f"\n--- Testing Sample {i}: {sample['description']} ---")

        # Test Emotion Service
        user_text = sample['user_input']['text']
        print(f"User Input: {user_text}")

        # Note: Since emotion_service methods are placeholders, this will return None or placeholder
        emotion_result = emotion_service.detect_emotion(user_text)
        print(f"Emotion Service Output: {emotion_result}")

        # Expected emotion output
        expected_emotion = sample['emotion_service_output']
        print(f"Expected: {expected_emotion}")

        # Test Recommendation Service
        rec_input = sample['recommendation_service_input']
        print(f"Recommendation Input: {rec_input}")

        # This will call the LLM functions
        rec_result = recommendation_service.generate_recommendation(rec_input)
        print(f"Recommendation Service Output: {rec_result}")

        # Expected recommendation output
        expected_rec = sample['recommendation_service_output']
        print(f"Expected: {expected_rec}")

if __name__ == "__main__":
    print("Running Service Tests...")
    test_services()