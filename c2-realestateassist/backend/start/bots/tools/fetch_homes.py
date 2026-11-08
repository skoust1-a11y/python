import requests
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class LocationPoints(BaseModel):
    """Input schema for fetching homes near a set of coordinates."""
    lat: float = Field(..., description="Latitude of the search center")
    lon: float = Field(..., description="Longitude of the search center")
    radius_meters: int = Field(3000, description="Search radius in meters (default 3000)")


@tool(args_schema=LocationPoints)
def fetch_homes(lat: float, lon: float, radius_meters: int = 3000):
    """
    Fetch nearby residential properties and apartments using coordinates via the Overpass API.
    Returns a list of property dicts with name, building type, address, and coordinates.
    """
    query = f"""
    [out:json];
    (
      way(around:{radius_meters},{lat},{lon})["building"="residential"];
      way(around:{radius_meters},{lat},{lon})["building"="apartments"];
      way(around:{radius_meters},{lat},{lon})["building"="house"];
      way(around:{radius_meters},{lat},{lon})["building"="terrace"];
      way(around:{radius_meters},{lat},{lon})["building"="bungalow"];
      node(around:{radius_meters},{lat},{lon})["building"="residential"];
      node(around:{radius_meters},{lat},{lon})["building"="apartments"];
      node(around:{radius_meters},{lat},{lon})["building"="house"];
      node(around:{radius_meters},{lat},{lon})["building"="terrace"];
      node(around:{radius_meters},{lat},{lon})["building"="bungalow"];
      node(around:{radius_meters},{lat},{lon})["name"];
    );
    out center;
    """

    url = "https://overpass-api.de/api/interpreter"

    def build_property_name(tags: dict, building: str) -> str:
        name = tags.get("name")
        if name:
            return name

        street = tags.get("addr:street")
        housenumber = tags.get("addr:housenumber")
        city = tags.get("addr:city") or tags.get("addr:suburb")

        if housenumber and street:
            return f"{housenumber} {street}"
        if street:
            return f"Residential property on {street}"
        if city:
            return f"Residential property in {city}"

        return f"Unnamed {building or 'residential'} property"

    try:
        response = requests.get(url, params={"data": query}, timeout=20)
        response.raise_for_status()
        data = response.json()

        homes_list = []
        for item in data.get("elements", []):
            tags = item.get("tags", {})
            building = tags.get("building", "residential")
            name = build_property_name(tags, building)

            homes_list.append({
                "name": name,
                "building_type": building,
                "address": tags.get("addr:street", "N/A"),
                "city": tags.get("addr:city", tags.get("addr:suburb", "N/A")),
                "lat": item.get("center", {}).get("lat", lat),
                "lon": item.get("center", {}).get("lon", lon),
            })

        return homes_list if homes_list else {"message": "No properties found in this radius. Please try a larger area or a different location."}

    except requests.exceptions.RequestException as e:
        return {"error": f"Network error fetching homes: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to fetch homes: {str(e)}"}