from langchain.tools import tool
import requests
from pydantic import BaseModel,Field
from settings.env_config import config
from langchain.tools import tool
import json

api_key_open_trip = config.require_env('OPEN_TRIP_API',None)

if not api_key_open_trip:
    raise ValueError('OPENTRIP_API_KEY_NOT FOUND')


class Coordinate(BaseModel):
    lat : float
    lon : float
    radius : int = 5000

@tool(args_schema=Coordinate)
def fetch_tool(lat: float, lon: float, radius: int = 5000):
    """
    Fetch nearby places using coordinates.
    """

    base_url = "https://api.opentripmap.com/0.1/en/places/radius"

    response = requests.get(
        base_url,
        params={
            "radius": radius,
            "lat": lat,
            "lon": lon,
            "apikey": api_key_open_trip
        },
        headers={"User-Agent": "my-ai-agent"}
    )

    response.raise_for_status()

    return response.json()


class OpenTripInput(BaseModel):
    lat: float
    lon: float

@tool(args_schema=OpenTripInput)
def opentripmap_fetch(lat : float ,lon :float) -> dict:
    """
    Fetch nearby amenities from OpenTripMap API for a given place.
    """
    lats, lons = lat, lon
    base = "https://api.opentripmap.com/0.1/en/places/radius"
    categories = ["accomodations", "transport", "health", "education", "sport"]
    results = {}
    for cat in categories:
        resp = requests.get(base, params={
            "radius": 3000, "lon": lons, "lat": lats,
            "kinds": cat, "limit": 5,
            "apikey": api_key_open_trip
        })
        results[cat] = resp.json().get("features", [])
    return {"amenities": results}













    