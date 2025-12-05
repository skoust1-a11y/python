## Project Context

In earlier practice, your **Travel & Trip Planner Agent** learned how to use tools — it could fetch your current location and provide destination details.  
However, the agent still followed a **fixed, one-size-fits-all process**. Every query — whether it was feedback, a booking request, or a cancellation — was handled in the same linear way.

In real-world applications, intelligent systems must **adapt their workflow** based on what the user says and how urgent it sounds. For example, booking requests should trigger a booking workflow, cancellations should follow a cancellation path, and general questions can be answered through a knowledge flow.

In this practice, you will make your agent **smarter and context-aware** using **LangChain Expression Language (LCEL)**. You'll learn how to build multi-step LLM pipelines that analyze customer feedback and implement router chains that conditionally direct travel queries to different response flows.

---

## Problem Statement

Enable intelligent routing and multi-step workflows for your **Travel & Trip Planner Agent** using LangChain Expression Language (LCEL). Your agent will analyze, decide, and respond intelligently based on query type and context.  
You will complete **two main tasks**:

---

### **Task 1 — Build a Multi-Step LCEL Chain for Travel Feedback Analysis**

#### Goal  
Create a multi-step LCEL pipeline that analyzes customer feedback, identifies its sentiment and urgency, and generates a professional response strategy.

#### Requirements  
1. Implement a multi-step LCEL chain using the pipe (`|`) syntax that combines sentiment classification, urgency assignment, and response strategy generation.

2. Create a sentiment classification step that categorizes feedback as POSITIVE, NEGATIVE, or NEUTRAL.

3. Implement a function that assigns urgency levels based on sentiment (e.g., NEGATIVE → HIGH, NEUTRAL → MEDIUM, POSITIVE → LOW).

4. Add a response strategy generation step that uses sentiment and urgency to create appropriate response strategies.

5. Create a FastAPI POST endpoint `/analyze_feedback` that accepts feedback input, invokes the chain, and returns sentiment, urgency, and strategy as a JSON response.

---

### **Task 2 — Intelligent Routing for Booking, Cancellation, and General Travel Queries**

#### Goal  
Build a router chain that classifies user queries into categories (e.g., BOOKING, CANCELLATION, GENERAL) and routes them to appropriate response chains.

#### Requirements  
1. Create an intent classification chain that categorizes user queries into BOOKING, CANCELLATION, or GENERAL based on the query content.

2. Implement three separate response chains:
   - **Booking Chain**: Handles booking requests and confirms details or guides users on next steps.
   - **Cancellation Chain**: Handles cancellation requests with appropriate messaging about refunds and confirmations.
   - **General Chain**: Provides helpful travel answers and suggestions for general inquiries.

3. Create condition functions that determine which chain to route to based on the classified intent.

4. Build a `RunnableBranch` router that routes queries to the appropriate chain based on the condition functions, with a default fallback to the general chain.

5. Create a FastAPI POST endpoint `/route_query` that accepts user queries, invokes the router, and returns the appropriate response based on the query type.

---

## Evaluation Criteria

Ensure you evaluate your solution against the below criteria:

1. Multi-step LCEL chain correctly analyzes feedback and returns sentiment, urgency, and response strategy.
2. Sentiment classification accurately categorizes feedback as POSITIVE, NEGATIVE, or NEUTRAL.
3. Urgency assignment function correctly maps sentiment to urgency levels.
4. Intent classification chain accurately categorizes queries into BOOKING, CANCELLATION, or GENERAL.
5. Router correctly routes queries to the appropriate response chain based on intent classification.
6. Booking, cancellation, and general chains generate appropriate responses for their respective query types.
7. Both endpoints (`/analyze_feedback` and `/route_query`) correctly invoke their respective chains and return appropriate JSON responses.
