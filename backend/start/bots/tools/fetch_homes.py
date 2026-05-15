import requests
from langchain_core.tools import tool
lat = 17.4046173
lon = 78.5610199

class LocationPoints:
    lat : float
    lon : float

@tool(args_schema=LocationPoints)
def fetch_homes(lat : float , lon : float):
    query = f"""
    [out:json];
    (
    way(around:3000,{lat},{lon})["building"="residential"];
    way(around:3000,{lat},{lon})["building"="apartments"];
    node(around:3000,{lat},{lon})["name"];
    );
    out center;
    """

    url = "https://overpass-api.de/api/interpreter"

    response = requests.get(url, params={"data": query})

    data = response.json()

    homes_list = []

    for item in data["elements"]:
        tags = item.get("tags", {})
        
        name = tags.get("name")
        building = tags.get("building")

        if name:
            print(name, building)
            homes_list.append(building)

    return homes_list