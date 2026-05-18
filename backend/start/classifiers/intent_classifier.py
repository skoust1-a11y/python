from langchain_core.prompts import ChatPromptTemplate
from llm_machine.llm_setup import llm
from langchain_core.output_parsers import StrOutputParser

# intent_prompt = ChatPromptTemplate.from_messages([
#         ("system", """You are a classification assistant. Classify the user intent into EXACTLY ONE of the following categories, and output ONLY the category string:
# location_lookup
# property_search
# amenity_search
# commute_analysis
# lifestyle_match
# general_conversation

# Do not output any other text."""),
#         ("user", "{query}")
#     ])

# intent_prompt = ChatPromptTemplate.from_messages([
#         ("system", """Classify user intent into one of:
#         - location_lookup: User mentions a city/area
#         - property_search: User asks for home recommendations
#         - amenity_search: User asks about nearby facilities
#         - commute_analysis: User asks about travel time
#         - lifestyle_match: User asks for family/professional areas
#         - general_conversation: Other queries"""),
#         ("user", "{query}")
#     ])
intent_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an intent classifier for a Real Estate Assistant.

Classify the user's query into EXACTLY one of the following intents:

---

**location_lookup**
User mentions a specific city, area, locality, or region and wants to explore it.
They are NOT asking about amenities or lifestyle — just the place itself.
Triggers: area name, city name, neighborhood, map lookup, "what is [place] like", "tell me about [area]"
Examples:
- "Tell me about Gachibowli"
- "What's the Banjara Hills area like?"
- "Show me details about Kondapur"

---

**property_search**
User wants to find, buy, rent, or explore residential properties.
Triggers: BHK, flat, apartment, villa, house, budget + property, rent/sale listings
Examples:
- "Find me a 3BHK in Hyderabad under 80 lakhs"
- "Show apartments for rent near Hitech City"
- "Any villas available in Jubilee Hills?"

---

**amenity_search**
User asks about facilities, infrastructure, or services near a location.
Triggers: nearby schools, hospitals, metro, malls, parks, connectivity, transport
Examples:
- "What are the facilities near Madhapur?"
- "Are there good hospitals in Kukatpally?"
- "How is the connectivity in Nallagandla?"

---

**lifestyle_match**
User asks for area recommendations based on personal or family lifestyle needs.
Triggers: best area for families, IT professionals, luxury living, budget zones, safe neighborhoods
Examples:
- "Which area is best for families in Hyderabad?"
- "Suggest a good zone for IT professionals"
- "Where can I find luxury residential areas near Financial District?"

---

**general_conversation**
Query does not relate to property, location, amenities, or lifestyle.
Triggers: greetings, unrelated questions, vague or off-topic inputs
Examples:
- "Hello, how are you?"
- "What is LangChain?"
- "Thanks!"

---

Return ONLY the intent label. No explanation. No extra text.
One of: location_lookup, property_search, amenity_search, lifestyle_match, general_conversation"""),
    ("user", "{query}")
])

classify_chain = intent_prompt | llm | StrOutputParser()
