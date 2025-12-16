## Study Buddy - A Personalized AI Tutor with LLM Models​

This practice is a perfect introduction to **Agentic AI** and **Cloud vs. Local LLMs**. We chain two models to achieve a superior learning outcome: one for facts, one for personalization.

### Problem Statement

Build a Python application that combines cloud (Gemini) and local (Llama 3.1 via Ollama) LLMs to deliver personalized learning. 

Use Gemini for factual explanations and Ollama to transform them into engaging analogies. Implement secure API key management and error handling.

The program must:​
- Accept a user query (e.g., “What is RAG?” or “Explain Agentic AI”)​
- Send it to the cloud model for an accurate explanation​
- Forward the same output to the local model for creative rephrasing​
- Display both responses in a clean, formatted console output​

By completing this practice, you will gain hands-on experience in multi-step agentic workflows, secure API integration, and hybrid AI model design — key skills for building scalable, privacy-aware AI solutions.

#### Context

Modern learners are turning to AI-driven platforms for quick explanations and conceptual clarity. ​

AI tutors typically rely solely on cloud models, raising privacy concerns and delivering generic responses. Build a hybrid solution that uses cloud models for accuracy and local models for personalized, private content eneration—keeping sensitive data on the user's machine.

#### Task Details

Following steps should be performed to build the solution for this practice. 

### Step 1: Prepare Your Project & Dependencies 

- Install the required libraries — `openai` for API interaction and `python-dotenv` for secure environment management.​
- Verify that your environment is properly initialized before proceeding.


### Step 2: Install and Configure Ollama for Local Model Execution

- Download and install `Ollama` from its official website.​
- Pull the required `Llama 3.1 (8B)` model using the terminal command `ollama pull llama3.1:8b`.​
- Ensure the Ollama service is running in the background to enable local model interaction.

### Step 3: Configure Cloud Model Access 

- Obtain a Gemini API key and store it securely in a `.env` file within your project folder.​
- Add the key and endpoint details.​
- Load these credentials securely into your application using the dotenv module.

### Step 4: Build and Execute the Tutor Agent 

- Develop a Python script that orchestrates both models — the cloud model (Gemini) for factual responses and the local model (Llama 3.1) for creative, private personalization.​
- Accept user queries, process them through both models, and display the results in a clear console format.​
- Run your program using `uv run main.py`.​
- Test the flow with example queries like “What is RAG?” or “Explain Agentic AI.”

**Hint:** 
- You'll need to implement the `get_cloud_explanation_streaming` and `get_local_personalization` functions, as well as the `main` function to handle the user interaction and model integration.
- **Prompt for local model:**
```
f"Rewrite this technical explanation in a highly engaging, fun, and personally relatable story or analogy for a beginner student exploring Agentic AI. Be creative and do not exceed 4 sentences. The explanation is:\n\n---\n{gemini_explanation}"

```

### 💡 Example Console Session

```
============================================================
Study Buddy - A Personalized AI Tutor with LLM Models​
============================================================
Step 1 (Cloud): Factual Explanation. Step 2 (Local): Creative Personalization.
[IMPORTANT] The Local Model (Ollama) is NOT currently connected.
... (If Ollama is not running, but the program continues to allow testing the Cloud step)

Enter an Agentic AI concept (e.g., RAG, LLM, Planning) or 'quit': **LLM**

--- [1] CLOUD MODEL (Gemini) - Factual Explanation ---
LLM stands for Large Language Model. It is a deep learning model trained on a massive amount of text data, allowing it to understand, generate, and process human language. LLMs work by predicting the next most probable word in a sequence, enabling them to write essays, translate languages, summarize documents, and generate code. They are the core engine for most modern generative AI applications.

--- [2] LOCAL MODEL (Llama 3.1) - Private Personalization ---
[ERROR: Could not complete Model Call]
Please check your setup/connection. Details: ... (Network error details)
[Error Occurred]

------------------------------------------------------------
Enter an Agentic AI concept (e.g., RAG, LLM, Planning) or 'quit': **quit**

Goodbye! Keep learning with AI.
```

-----