"""Functions exposed to agents in the Hong Kong domain."""

from __future__ import annotations

import requests

from settings import settings

REQUEST_TIMEOUT_S = 10
_HK_BOUNDS = {
    "low": {"latitude": 22.1193, "longitude": 113.8196},
    "high": {"latitude": 22.5597, "longitude": 114.4345},
}


def search_hk_location(address: str) -> dict:
    """
    Search the location of the address in Hong Kong using Google Places API.
    If the user's query contains an address, use the search_hk_location to search for the latitude and longitude of the address. You can use the latitude and longitude to search for geographic data in the database.
    Args:
        address (str): The address to search for.
    Returns:
        dict: The latitude and longitude of the address.
        example:
        {
            "latitude": 22.3193,
            "longitude": 114.1696
        }
    """  # noqa: E501 — the docstring is the tool description agents see; kept verbatim.
    api_key = settings.require("google_places_api_key")
    places = requests.post(
        "https://places.googleapis.com/v1/places:searchText",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName",
        },
        json={
            "textQuery": address,
            "regionCode": "HK",
            "locationRestriction": {"rectangle": _HK_BOUNDS},
        },
        timeout=REQUEST_TIMEOUT_S,
    )
    places.raise_for_status()
    found = places.json().get("places") or []
    if not found:
        raise LookupError(f"No Hong Kong place found for address {address!r}")

    geocode = requests.get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={
            "address": found[0]["displayName"]["text"],
            "components": "country:HK",
            "key": api_key,
        },
        timeout=REQUEST_TIMEOUT_S,
    )
    geocode.raise_for_status()
    results = geocode.json().get("results") or []
    if not results:
        raise LookupError(f"No geocoding result found for address {address!r}")
    location = results[0]["geometry"]["location"]
    return {"latitude": location["lat"], "longitude": location["lng"]}


FUNCTIONS = {"search_hk_location": search_hk_location}
