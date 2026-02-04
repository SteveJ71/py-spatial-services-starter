"""
NSW Spatial Services – Cadastre utilities

Wraps the NSW_Cadastre ArcGIS REST service to query
cadastral parcel information from a coordinate.

Service directory:
https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Cadastre/MapServer
https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Cadastre/MapServer/layers

Other info:
https://www.spatial.nsw.gov.au/products_and_services/web_services
https://data.nsw.gov.au/data/dataset/spatial-services-nsw-cadastre


IMPORTANT LIMITATIONS (read before using):

1) DCDB / GIS cadastre
----------------------
The geometry returned by this service is GIS cadastral data
(DCDB-style). It is NOT survey-accurate and must not be used
for boundary definition, setout, or measurement.

2) MGA94 vs MGA2020
--------------------
Although the service allows requesting different output
spatial references (e.g. MGA94 vs MGA2020), testing shows
that datum transformations may not be applied.

In practice, requesting MGA2020 can return coordinates
numerically identical to MGA94.

Therefore:
Treat returned coordinates as indicative only.
Do NOT rely on them as datum-correct survey coordinates.

Functions:
- lot_plan_from_point → Lot/DP at a coordinate
- lots_plans_from_point → All parcels at a coordinate
- nearby_lots → Lots within a distance
- lot_geometry_mga_from_point → Parcel geometry (indicative only)

Input coordinates:
- Must be lon/lat (EPSG:4326)
- No address lookup is performed here (see address.py)
"""


import requests

CADASTRE_BASE = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Cadastre/MapServer"


def lots_plans_from_point(lon: float, lat: float) -> list[tuple[str | None, str | None, str | None]]:
    """
    Return a list of (lotnumber, sectionnumber, planlabel) for parcels identified
    at a lon/lat point (EPSG:4326).

    Note: A single address/location can relate to more than one lot.
    """
    url = f"{CADASTRE_BASE}/identify"
    params = {
        "f": "json",
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "sr": 4326,
        "tolerance": 3,
        "returnGeometry": "false",
        "imageDisplay": "800,600,96",
        "mapExtent": f"{lon-0.002},{lat-0.002},{lon+0.002},{lat+0.002}",
        "layers": "all:9",
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    js = r.json()

    results = js.get("results") or []
    out: list[tuple[str | None, str | None, str | None]] = []
    seen = set()

    for res in results:
        attrs = res.get("attributes") or {}
        lot = attrs.get("lotnumber")
        sec = attrs.get("sectionnumber") or attrs.get("sectionumber")  # some services vary
        plan = attrs.get("planlabel")

        key = (lot, sec, plan)
        if (lot or plan) and key not in seen:
            seen.add(key)
            out.append(key)

    return out



def nearby_lots(lon: float, lat: float, distance_m: float = 50) -> list[tuple[str, str]]:
    """
    Return list of (lotnumber, planlabel) for parcels within
    distance_m of a lon/lat point (EPSG:4326).

    Useful for finding adjoining / nearby lots.
    """
    url = f"{CADASTRE_BASE}/9/query"  # layer 9 = parcels

    params = {
        "f": "json",
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "distance": distance_m,
        "units": "esriSRUnit_Meter",
        "outFields": "lotnumber,planlabel",
        "returnGeometry": "false",
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    js = r.json()

    feats = js.get("features") or []
    results = []

    for f in feats:
        attrs = f.get("attributes") or {}
        lot = attrs.get("lotnumber")
        plan = attrs.get("planlabel")

        if lot and plan:
            results.append((lot, plan))

    return results




def lot_geometry_mga_from_point(lon: float, lat: float, epsg: int) -> list[list[list[float]]]:
    """
    Return parcel boundary geometry from NSW Cadastre.

    The function *requests* the output geometry in the provided EPSG code
    (e.g. 28356 = MGA94 Zone 56, 7856 = MGA2020 Zone 56).

    IMPORTANT:
    - The service may IGNORE the requested output coordinate system.
      Testing has shown EPSG:28356 and EPSG:7856 can return identical coordinates.
    - Geometry is DCDB / GIS cadastral data and is NOT survey-accurate.
      Positional errors can be several metres in some areas.

    Treat returned coordinates as indicative only.

    Inputs:
    - lon/lat in EPSG:4326
    - epsg: requested output projection (commonly 28356 or 7856)

    Returns:
    - rings: list of boundaries, each boundary is [[E, N], [E, N], ...]
    """

    if not (7846 <= epsg <= 7859) and not (28346 <= epsg <= 28359):
        raise ValueError("epsg must be MGA2020 projected EPSG in range 7846..7859 or 28346..28359")

    # Step 1: identify to get objectid for the lot at the point
    id_url = f"{CADASTRE_BASE}/identify"
    id_params = {
        "f": "json",
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "sr": 4326,
        "tolerance": 3,
        "returnGeometry": "false",
        "imageDisplay": "800,600,96",
        "mapExtent": f"{lon-0.002},{lat-0.002},{lon+0.002},{lat+0.002}",
        "layers": "all:9",
    }

    r = requests.get(id_url, params=id_params, timeout=30)
    r.raise_for_status()
    js = r.json()

    # DEBUG — see what spatial reference the server claims
    sr = js.get("spatialReference")
    print("DEBUG top-level SR:", js.get("spatialReference"))

    # DEBUG — check SR on first feature geometry
    feats = js.get("features") or []
    if feats:
        geom = feats[0].get("geometry") or {}
        print("DEBUG geometry SR:", geom.get("spatialReference"))


    results = js.get("results") or []
    if not results:
        return []

    attrs = results[0].get("attributes") or {}
    oid = attrs.get("objectid") or attrs.get("OBJECTID")
    if not oid:
        return []

    # Step 2: query that parcel geometry in desired projection
    q_url = f"{CADASTRE_BASE}/9/query"
    q_params = {
        "f": "json",
        "where": f"objectid={oid}",
        "outFields": "objectid",
        "returnGeometry": "true",
        "outSR": epsg,
    }

    r = requests.get(q_url, params=q_params, timeout=30)
    r.raise_for_status()
    js = r.json()
    

    # ArcGIS responses often include spatialReference at the top-level or inside geometry
    sr = js.get("spatialReference") or {}
    print("DEBUG out spatialReference:", sr)

    feats = js.get("features") or []
    if not feats:
        return []

    geom = feats[0].get("geometry") or {}
    print("DEBUG geom keys:", geom.keys())

    feats = js.get("features") or []
    if not feats:
        return []

    geom = feats[0].get("geometry") or {}
    return geom.get("rings") or []
