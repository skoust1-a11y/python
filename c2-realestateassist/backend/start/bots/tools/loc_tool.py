from langchain.tools import tool
import requests
import json
from pydantic import BaseModel
from observability import observe



class PlaceInput(BaseModel):
    place: str

@tool(args_schema=PlaceInput)
def nominatim_geocode(place: str) -> dict:
    """
    Convert place name into latitude and longitude.
    """

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": place,
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "my-ai-agent"
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers
        )

        response.raise_for_status()

        data = response.json()

        if not data:
            return {"error": "Location not found"}

        return {
            "lat": float(data[0]["lat"]),
            "lon": float(data[0]["lon"])
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error fetching location: {e}"}

    except Exception as e:
        return {"error": f"Server error: {e}"}