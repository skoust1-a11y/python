from langchain_core.prompts import ChatPromptTemplate
from llm_machine.llm_setup import llm
from langchain_core.output_parsers import StrOutputParser
from langfuse import Langfuse
import os




LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")

if not LANGFUSE_BASE_URL:
    raise ValueError('The LangFuse Base Url Not Found in .env file')
if not LANGFUSE_PUBLIC_KEY:
    raise ValueError('The LangFuse Public Key Not Found in .env file')
if not LANGFUSE_SECRET_KEY:
    raise ValueError('The LangFuse Secre Key Not Found in .env file')
    


langfuse_client = Langfuse(
    base_url=LANGFUSE_BASE_URL,
    public_key=LANGFUSE_PUBLIC_KEY,
    secret_key=LANGFUSE_SECRET_KEY
)


prompt = langfuse_client.get_prompt(
        name='classifier_prompt',
        label='production'
        )

if not prompt:
    raise ValueError('PROMPT NOT FOUND.....')



newPrompt = prompt.prompt



intent_prompt = ChatPromptTemplate.from_messages([
    ("system", newPrompt),
     ("user", "{query}")
])


# intent_prompt = ChatPromptTemplate.from_messages([
#     ("system", """You are an intent classifier for a Real Estate Assistant.

# Classify the user's query into EXACTLY one of the following intents:

# ---

# **location_lookup**
# User mentions a specific city, area, locality, or region and wants to explore it.
# They are NOT asking about amenities or lifestyle — just the place itself.
# Triggers: area name, city name, neighborhood, map lookup, "what is [place] like", "tell me about [area]"
# Examples:
# - "Tell me about Gachibowli"
# - "What's the Banjara Hills area like?"
# - "Show me details about Kondapur"

# ---

# **property_search**
# User wants to find, buy, rent, or explore residential properties.
# Triggers: BHK, flat, apartment, villa, house, budget + property, rent/sale listings
# Examples:
# - "Find me a 3BHK in Hyderabad under 80 lakhs"
# - "Show apartments for rent near Hitech City"
# - "Any villas available in Jubilee Hills?"

# ---

# **amenity_search**
# User asks about facilities, infrastructure, or services near a location.
# Triggers: nearby schools, hospitals, metro, malls, parks, connectivity, transport
# Examples:
# - "What are the facilities near Madhapur?"
# - "Are there good hospitals in Kukatpally?"
# - "How is the connectivity in Nallagandla?"

# ---

# **lifestyle_match**
# User asks for area recommendations based on personal or family lifestyle needs.
# Triggers: best area for families, IT professionals, luxury living, budget zones, safe neighborhoods
# Examples:
# - "Which area is best for families in Hyderabad?"
# - "Suggest a good zone for IT professionals"
# - "Where can I find luxury residential areas near Financial District?"

# ---

# **general_conversation**
# Query does not relate to property, location, amenities, or lifestyle.
# Triggers: greetings, unrelated questions, vague or off-topic inputs
# Examples:
# - "Hello, how are you?"
# - "What is LangChain?"
# - "Thanks!"

# ---

# Return ONLY the intent label. No explanation. No extra text.
# One of: location_lookup, property_search, amenity_search, lifestyle_match, general_conversation"""),
#     ("user", "{query}")
# ])

classify_chain = intent_prompt | llm | StrOutputParser()
