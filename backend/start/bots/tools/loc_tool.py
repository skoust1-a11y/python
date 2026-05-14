from langchain.tools import tool
import requests

@tool
def nominatim_geocode(place: str) -> list:
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

    response = requests.get(
        url,
        params=params,
        headers=headers
    )

    response.raise_for_status()

    data = response.json()

    result = [
        {
            "lat": item["lat"],
            "lon": item["lon"]
        }
        for item in data
    ]

    return result