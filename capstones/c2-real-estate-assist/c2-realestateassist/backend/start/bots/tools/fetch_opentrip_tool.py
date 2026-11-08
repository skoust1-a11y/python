from langchain.tools import tool
import requests
from pydantic import BaseModel,Field
from settings.env_config import config
from langchain.tools import tool
import json
from observability import observe

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


# ---------OLD TOOL------------------

# @tool(args_schema=OpenTripInput)
# def opentripmap_fetch(lat : float ,lon :float) -> dict:
#     """
#     Fetch nearby amenities from OpenTripMap API for a given place.
#     """
#     lats, lons = lat, lon
#     base = "https://api.opentripmap.com/0.1/en/places/radius"
#     categories = ["accommodations", "transport", "health", "education", "sport"]
#     results = {}
#     for cat in categories:
#         resp = requests.get(base, params={
#             "radius": 3000, "lon": lons, "lat": lats,
#             "kinds": cat, "limit": 5,
#             "apikey": api_key_open_trip
#         })
#         results[cat] = resp.json().get("features", [])
#     return {"amenities": results}

@tool(args_schema=OpenTripInput)
def opentripmap_fetch(lat: float, lon: float) -> dict:
    """
    Fetch nearby amenities from OpenTripMap API for a given place.
    """

    base = "https://api.opentripmap.com/0.1/en/places/radius"

    categories = {
        "accommodations": "other_hotels",
        "transport": "fuel,car_rentals,bus_stations",
        "health": "hospitals,pharmacy,clinics",
        "education": "schools,universities",
        "sport": "sport"
    }

    results = {}

    for label, kinds in categories.items():
        resp = requests.get(
            base,
            params={
                "radius": 3000,
                "lon": lon,
                "lat": lat,
                "kinds": kinds,
                "limit": 20,
                "apikey": api_key_open_trip
            }
        )

        data = resp.json()
        results[label] = data.get("features", [])

    return {"amenities": results}


@tool(args_schema=OpenTripInput)
def nearby_homes(lat : float , lon : float):
    """
        Fetch nearby Houses from GeoApify API for a given place.
    """

    API_KEY = "c246df0edcd6454f901ffd100079112b"

    url = "https://api.geoapify.com/v2/places"


    params = {
        "categories": "building,accommodation.apartment",
        "filter": f"circle:{lon},{lat},3000",
        "bias": f"proximity:{lon},{lat}",
        "limit": 20,
        "apiKey": API_KEY
    }

    response = requests.get(url, params=params)

    return {
        'places_geo': response.json()
    }















    