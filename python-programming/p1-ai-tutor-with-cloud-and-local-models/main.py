from openai import OpenAI, OpenAIError
from dotenv import load_dotenv
import os
import logging, httpx
from pathlib import Path


def setup_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        file_handler = logging.FileHandler(log_dir / "AI_MODELS.log")

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%d-%m-%Y %H:%M:%S",
        )

        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# ---------------- CLOUD MODEL ---------------- #

def get_cloud_explanation_streaming(firstChat, logger):
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    base_url = os.getenv("GEMINI_BASE_URL")
    ai_model = os.getenv("GEMINI_MODEL")

    if not api_key:
        raise ValueError("API KEY FOR VENDOR NOT FOUND")
    if not base_url:
        raise ValueError("BASE VENDOR URL NOT FOUND")
    if not ai_model:
        raise ValueError("AI VENDOR MODEL NOT FOUND")

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)

        response = client.chat.completions.create(
            model=ai_model,
            messages=[{"role": "user", "content": firstChat}],
            stream=True,
            temperature=0.2,
        )

        chunkList = []

        for chunk in response:
            if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content"):
                    content = delta.content
                    if isinstance(content, str):
                        print(content, end="", flush=True)
                        chunkList.append(content)

        totalResponse = "".join(chunkList)
        logger.info(f"Gemini Response: {totalResponse}")

        return totalResponse

    except httpx.ConnectError:
        raise ConnectionError("Unable to connect to Gemini API")

    except OpenAIError as e:
        raise OpenAIError(f"Vendor model API error: {e}")

    except Exception as e:
        raise Exception(f"Unexpected error: {e}")


def get_local_personalization(gemini_explanation, logger):
    load_dotenv()

    base_url_local = os.getenv("BASE_URL_LOCAL")
    api_key_local = os.getenv("API_KEY_FOR_LOCAL")
    ai_model = os.getenv("LOCAL_MODEL")

    if not api_key_local:
        raise ValueError("API KEY FOR LOCAL ollama NOT FOUND")
    if not base_url_local:
        raise ValueError("BASE URL NOT FOUND")
    if not ai_model:
        raise ValueError("AI MODEL NOT FOUND")

    try:
        client = OpenAI(api_key=api_key_local, base_url=base_url_local)

        messages = [
            {
                "role": "user",
                "content": f"""Rewrite this technical explanation in a highly engaging, fun, and personally relatable story or analogy for a beginner student exploring Agentic AI. Be creative and do not exceed 4 sentences.

The explanation is:
---
{gemini_explanation}
""",
            }
        ]

        response = client.chat.completions.create(
            model=ai_model,
            messages=messages,
            stream=True,
        )

        chunkList = []

        for chunk in response:
            if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content"):
                    content = delta.content
                    if isinstance(content, str):
                        print(content, end="", flush=True)
                        chunkList.append(content)

        totalResponse = "".join(chunkList)

        logger.info(f"Ollama Response: {totalResponse}")

        return totalResponse

    except httpx.ConnectError:
        raise ConnectionError("Ollama server is not running")

    except OpenAIError as e:
        raise OpenAIError(f"Local model API error: {e}")

    except Exception as e:
        raise Exception(f"Unexpected error: {e}")




def mainWithQuery(query, logger):

    print("\n------------------------------------------------------------")
    print(f"User Query: {query}")
    print("------------------------------------------------------------")

    logger.info(f"User Query: {query}")


    print("\n--- [1] CLOUD MODEL (Gemini) - Factual Explanation ---")

    try:
        responseFromGemini = get_cloud_explanation_streaming(query, logger)

    except Exception as e:
        print("\n[ERROR: Could not complete Gemini Model Call]")
        print(f"Details: {e}")
        logger.error(e)
        return


    print("\n\n--- [2] LOCAL MODEL (Llama 3.1) - Private Personalization ---")

    try:
        responseFromOllama = get_local_personalization(
            gemini_explanation=responseFromGemini,
            logger=logger,
        )

    except Exception as e:
        print("\n[ERROR: Could not complete Model Call]")
        print("Please check your setup/connection.")
        print(f"Details: {e}")
        logger.warning(e)

    print("\n------------------------------------------------------------")




def main():

    print(
"""
============================================================
Study Buddy - A Personalized AI Tutor with LLM Models
============================================================
Step 1 (Cloud): Factual Explanation.
Step 2 (Local): Creative Personalization.
"""
)

    logger = setup_logger()

    while True:

        query = input(
            "\nEnter an Agentic AI concept (e.g., RAG, LLM, Planning) or 'quit': "
        )

        if query.lower() == "quit":
            break

        mainWithQuery(query, logger)

    print("\nGoodbye! Keep learning with AI.")
    logger.info("Program Ended")


if __name__ == "__main__":
    main()