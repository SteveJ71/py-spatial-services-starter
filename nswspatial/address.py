"""
NSW Spatial Services – Address utilities

Wraps the Address Location web service to convert a street address
into a coordinate (lon/lat, EPSG:4326).

Official docs:
https://maps.six.nsw.gov.au/sws/AddressLocation.html

Notes:
- This module only resolves addresses to points.
- It does NOT perform any cadastre lookup.
- Use cadastre.py to get Lot/DP from a coordinate.
"""

import requests

ADDR_LOC_URL = "https://mapsq.six.nsw.gov.au/services/public/Address_Location"

def parse_simple_address(addr: str):
    parts = addr.strip().upper().split()
    return parts[0], " ".join(parts[1:-1]), parts[-1]


def address_to_point(
    address: str,
    suburb: str | None = None,
    postcode: int | None = None
) -> tuple[float, float, str, int, str | None]:
    """
    Resolve an address to an approximate coordinate using
    NSW Spatial Services Address Location service.

    Returns:
        lon, lat, matched_address, match_count, matched_house
    """

    house, roadname, roadtype = parse_simple_address(address)

    params = {
        "houseNumber": house,
        "roadName": roadname,
        "roadType": roadtype,
        "projection": "EPSG:4326",
    }

    if suburb:
        params["suburb"] = suburb
    if postcode:
        params["postCode"] = postcode

    r = requests.get(ADDR_LOC_URL, params=params, timeout=30)
    r.raise_for_status()
    js = r.json()

    result = js.get("addressResult") or {}
    addrs = result.get("addresses") or []

    if not addrs:
        raise RuntimeError("No address found")

    a = addrs[0]
    ap = a["addressPoint"]

    matched_address = _extract_display_address(a)
    match_count = len(addrs)

    # matched house number from SIX
    matched_house = a.get("houseNumberString")

    lon = ap["centreX"]
    lat = ap["centreY"]

    return lon, lat, matched_address, match_count, matched_house



def _extract_display_address(a: dict) -> str:
    """
    Try a few common keys used by Address_Location for a readable address string.
    Returns "" if none found.
    """
    for k in ("address", "fullAddress", "displayAddress", "formattedAddress", "addressString"):
        v = a.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    # Sometimes it's nested
    addr = a.get("addressDetails") or a.get("address_detail") or {}
    if isinstance(addr, dict):
        for k in ("address", "fullAddress", "displayAddress", "formattedAddress", "addressString"):
            v = addr.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()

    # Last resort: build something from parts if present
    parts = []
    for k in ("houseNumber", "roadName", "roadType", "suburb", "postCode", "state"):
        v = a.get(k)
        if v:
            parts.append(str(v).strip())
    return " ".join(parts).strip()

