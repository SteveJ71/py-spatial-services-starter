"""
NSW Spatial Services – Cadastre utilities (personal reference)

Small wrappers around the NSW_Cadastre ArcGIS REST service for:
- finding parcels at/near a lon/lat point, and
- fetching parcel boundary geometry by Lot/Plan.

Service directory:
https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Cadastre/MapServer
https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Cadastre/MapServer/layers

Other info:
https://www.spatial.nsw.gov.au/products_and_services/web_services
https://data.nsw.gov.au/data/dataset/spatial-services-nsw-cadastre

Notes / limitations (practical):
- This is GIS cadastre (DCDB-style) geometry. Treat as indicative only.
- In testing, requesting different outSR values (e.g. MGA94 vs MGA2020) can return
  numerically identical coordinates. This module does not attempt to "fix" that.
- Inputs to the point-based functions are lon/lat (EPSG:4326).
- No address lookup here (see address.py).
"""

from __future__ import annotations
import time
import requests

CADASTRE_BASE = (
    "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Cadastre/MapServer"
)

RETRYABLE_ARCGIS_MESSAGES = (
    "error performing query operation",
    "failed to execute query",
)

def _run_arcgis_call(label: str, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except RuntimeError as ex:
        print(f"\n[ERROR] {label} failed: {ex}")
        print("        (This service is intermittent. Re-run or try again in a minute.)")
        return None


import random
import time
import requests

def _get_json(url: str, params: dict, timeout: int = 15, debug: bool = False, retries: int = 2) -> dict:
    """
    Small HTTP helper for ArcGIS REST calls.

    Notes:
    - These public endpoints can be intermittently slow or return transient
      server-side errors (e.g. "Error performing query operation").
    - A request may succeed on the next run without any code changes.
    - This helper is allowed to retry with a small backoff and will raise a
      RuntimeError with a short message so example scripts can fail cleanly.
    """
    # Use shorter connect timeout + provided read timeout
    req_timeout = (5, timeout) if isinstance(timeout, (int, float)) else timeout

    last_exc: Exception | None = None

    for attempt in range(retries + 1):
        try:
            if debug:
                print(f"DEBUG query url: {url}")
                print(f"DEBUG query params: {params}")

            r = requests.get(url, params=params, timeout=req_timeout)
            r.raise_for_status()
            js = r.json()

            if debug and "error" in js:
                print(f"DEBUG error payload: {js}")

            _raise_if_arcgis_error(js)
            return js

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as ex:
            last_exc = ex
            if attempt >= retries:
                break

            # small backoff with jitter
            sleep_s = (0.6 * (2 ** attempt)) + random.uniform(0, 0.4)
            if debug:
                print(f"DEBUG transient network error: {ex} — retrying in {sleep_s:.2f}s")
            time.sleep(sleep_s)

        except requests.exceptions.RequestException as ex:
            # other HTTP errors, etc.
            raise RuntimeError(f"HTTP error: {ex}") from ex

    # ran out of retries
    raise RuntimeError(f"Network timeout talking to {url} (read timeout={timeout}s). Try again.") from last_exc


def _raise_if_arcgis_error(js: dict) -> None:
    """ArcGIS REST sometimes returns error payloads with HTTP 200."""
    if "error" in js:
        err = js.get("error") or {}
        raise RuntimeError(f"ArcGIS error: {err.get('message')} | {err.get('details')}")


def _sql_escape(s: str) -> str:
    """Escape single quotes for ArcGIS where clauses."""
    return s.replace("'", "''")


def lots_plans_from_point(
    lon: float, lat: float
) -> list[tuple[str | None, str | None, str | None]]:
    """
    Return (lotnumber, sectionnumber, planlabel) for parcels intersecting a
    lon/lat point (EPSG:4326).
    """
    url = f"{CADASTRE_BASE}/9/query"
    params = {
        "f": "json",
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "lotnumber,sectionnumber,planlabel",
        "returnGeometry": "false",
        "outSR": 4326,
    }

    js = _get_json(url, params, timeout=30)

    features = js.get("features") or []
    out: list[tuple[str | None, str | None, str | None]] = []
    seen: set[tuple[str | None, str | None, str | None]] = set()

    for feat in features:
        attrs = feat.get("attributes") or {}
        lot = attrs.get("lotnumber")
        sec = attrs.get("sectionnumber") or attrs.get("sectionumber")
        if isinstance(sec, str) and sec.strip().lower() in ("null", ""):
            sec = None
        plan = attrs.get("planlabel")

        key = (lot, sec, plan)
        if (lot or plan) and key not in seen:
            seen.add(key)
            out.append(key)

    return out


def nearby_lots(lon: float, lat: float, distance_m: float = 50) -> list[tuple[str, str]]:
    """
    Return (lotnumber, planlabel) for parcels within distance_m of a lon/lat point
    (EPSG:4326).
    """
    url = f"{CADASTRE_BASE}/9/query"
    params = {
        "f": "json",
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "outSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "distance": distance_m,
        "units": "esriSRUnit_Meter",
        "outFields": "lotnumber,planlabel",
        "returnGeometry": "false",
    }

    js = _get_json(url, params, timeout=30)

    feats = js.get("features") or []
    results: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for f in feats:
        attrs = f.get("attributes") or {}
        lot = attrs.get("lotnumber")
        plan = attrs.get("planlabel")
        if lot and plan:
            key = (lot, plan)
            if key not in seen:
                seen.add(key)
                results.append(key)

    return results


def lot_geometry_mga_from_point(lon: float, lat: float, epsg: int) -> list[list[list[float]]]:
    """
    Return parcel boundary geometry from NSW Cadastre.

    The function requests geometry in the supplied EPSG
    (e.g. 28356 = MGA94 / Z56, 7856 = MGA2020 / Z56).

    IMPORTANT:
    - Service reliability varies. Requests can be slow,
      intermittently fail, or return empty geometry.
      Re-running often succeeds.
    - outSR may not be honoured. 28356 and 7856 can
      return identical coordinates.
    - Geometry is DCDB / GIS cadastre and NOT survey-accurate.
      Metre-level discrepancies are possible.

    Inputs:
    - lon/lat in EPSG:4326
    - epsg: requested projected EPSG (commonly 28356 or 7856)

    Returns:
    - rings: [[ [E,N], ... ], ...]
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

