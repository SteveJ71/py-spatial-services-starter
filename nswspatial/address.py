"""
NSW Spatial Services – Address utilities (personal reference)

Wraps the Address Location service to convert a street address into a point
(lon/lat, EPSG:4326).

Docs:
https://maps.six.nsw.gov.au/sws/AddressLocation.html

Notes:
- This module resolves addresses to points only (approximate).
- It does not perform cadastre lookup; see cadastre.py for Lot/Plan queries.
"""

from __future__ import annotations

import re
import requests

ADDR_LOC_URL = "https://mapsq.six.nsw.gov.au/services/public/Address_Location"


_ROADTYPE_RE = re.compile(r"^[A-Z]{2,5}$")  # ST, RD, AVE, PDE, CCT etc (loose)


def _coerce_postcode(postcode) -> int | None:
    if postcode is None:
        return None
    s = str(postcode).strip()
    if not s:
        return None
    # keep digits only
    s = "".join(ch for ch in s if ch.isdigit())
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def parse_simple_address(addr: str) -> tuple[str, str, str]:
    """
    Best-effort splitter for inputs like:
        "87A BUNARBA RD"
        "87A BUNARBA ROAD"
        "1/87A BUNARBA RD"

    Returns:
        houseNumberString, roadName, roadType

    Notes:
    - This is intentionally simple; the service can still fuzzy-match.
    - If road type isn't obvious, we pass the last token as roadType anyway.
    """
    s = " ".join((addr or "").strip().split())
    if not s:
        return "", "", ""

    tokens = s.upper().split()
    if len(tokens) == 1:
        return tokens[0], "", ""

    house = tokens[0]
    last = tokens[-1]

    # If the last token looks like a short road type (RD/ST/AVE/etc), treat as roadType.
    # Otherwise still treat last as roadType (service accepts full words like "ROAD").
    road_type = last
    road_name_tokens = tokens[1:-1]

    # If we only have house + one token, that token is probably road name, not road type.
    # Example: "87A BUNARBA" (user forgot RD)
    if not road_name_tokens:
        return house, tokens[1], ""

    road_name = " ".join(road_name_tokens)
    return house, road_name, road_type


def address_to_point(
    address: str,
    suburb: str | None = None,
    postcode: int | str | None = None,
) -> tuple[float, float, str, int, str | None]:
    """
    Resolve an address to an approximate coordinate using the Address Location service.

    Returns:
        lon, lat, matched_address, match_count, matched_house
    """
    house, roadname, roadtype = parse_simple_address(address)
    pc = _coerce_postcode(postcode)

    params = {
        "houseNumber": house,
        "roadName": roadname,
        "roadType": roadtype,
        "projection": "EPSG:4326",
    }

    if suburb and str(suburb).strip():
        params["suburb"] = str(suburb).strip()

    if pc is not None:
        params["postCode"] = pc

    r = requests.get(ADDR_LOC_URL, params=params, timeout=30)
    r.raise_for_status()
    js = r.json()

    result = js.get("addressResult") or {}
    addrs = result.get("addresses") or []

    if not addrs:
        raise RuntimeError(
            f"No address found (input='{address}', suburb='{suburb or ''}', postcode='{postcode or ''}')"
        )

    a = addrs[0]
    ap = a.get("addressPoint") or {}
    if "centreX" not in ap or "centreY" not in ap:
        raise RuntimeError("Address found but no addressPoint returned")

    matched_address = _extract_display_address(a)
    match_count = len(addrs)
    matched_house = a.get("houseNumberString")

    lon = ap["centreX"]
    lat = ap["centreY"]

    return float(lon), float(lat), matched_address, int(match_count), matched_house


def _extract_display_address(a: dict) -> str:
    for k in ("address", "fullAddress", "displayAddress", "formattedAddress", "addressString"):
        v = a.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    addr = a.get("addressDetails") or a.get("address_detail") or {}
    if isinstance(addr, dict):
        for k in ("address", "fullAddress", "displayAddress", "formattedAddress", "addressString"):
            v = addr.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()

    parts = []
    for k in ("houseNumberString", "roadName", "roadType", "suburb", "postCode", "state"):
        v = a.get(k)
        if v:
            parts.append(str(v).strip())
    return " ".join(parts).strip()
