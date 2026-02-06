"""
Example 03 — Compare lot geometry output SR (MGA94 vs MGA2020)

Purpose:
Quick diagnostic for how the NSW Cadastre service behaves when different
output spatial references (outSR) are requested for the *same* parcel geometry.

What this script does:
1) Resolve an address to a lon/lat test point.
2) Find the Lot/Plan at that point.
3) Request the parcel geometry twice using different outSR values:
   - EPSG:28356 (MGA94 / Zone 56)
   - EPSG:7856  (MGA2020 / Zone 56)
4) Print sample vertices and compare coordinates.

Notes (important):
- Service reliability: requests can be slow or intermittently fail.
  You may see ArcGIS "query operation" errors, timeouts, or empty geometry.
  If that happens, re-run the script (it often succeeds on the next attempt).
- Partial results are common: one outSR request may return geometry while the
  other returns none. In that case the comparison is skipped.
- Datum behaviour: with this query method, the returned coordinates for
  EPSG:28356 and EPSG:7856 are often identical to the displayed precision.
  This suggests outSR may not be changing the returned coordinates here.
  Treat this as an observation from this approach (not a definitive statement
  about the service overall).
"""


import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nswspatial.address import address_to_point
from nswspatial.cadastre import lots_plans_from_point, lot_geometry_mga_from_point, _run_arcgis_call


def _clean_section(sec):
    if sec is None:
        return None
    if isinstance(sec, str) and sec.strip().lower() in ("", "null"):
        return None
    return sec


def _print_boundary(label: str, rings: list[list[list[float]]], max_points: int = 12) -> None:
    if not rings:
        print(f"\n{label}: [no geometry returned]")
        return

    ring = rings[0]
    print(f"\n{label} (showing up to {max_points} points):")
    for i, (e, n) in enumerate(ring[:max_points], start=1):
        print(f"  {i:02d}: {e:.3f}, {n:.3f}")

    if len(ring) > max_points:
        print(f"  ... ({len(ring)} points total in first boundary)")


def _first_point(rings: list[list[list[float]]]) -> tuple[float, float] | None:
    if not rings or not rings[0]:
        return None
    e, n = rings[0][0]
    return float(e), float(n)


def main():
    address = input("Enter street address (e.g. 39 RYAN ST): ").strip()
    suburb = input("Enter suburb: ").strip()
    postcode = input("Enter postcode (optional): ").strip() or None

    # Light normalisation (reduces input variance)
    address_norm = " ".join(address.split())
    suburb_norm = " ".join(suburb.split())

    number = address_norm.split()[0] if address_norm else ""

    try:
        lon, lat, matched_address, match_count, matched_house = address_to_point(
            address_norm,
            suburb=suburb_norm,
            postcode=postcode
        )
    except RuntimeError as ex:
        print("\nNo address found.")
        print(f"Details: {ex}")
        return

    print(f"\nInput:   {address_norm}, {suburb_norm}")
    print(f"Matched: {matched_address}")

    if match_count > 1:
        print(f"WARNING: {match_count} possible address matches returned — fuzzy match used.")

    if matched_house and matched_house.strip().upper() != number.strip().upper():
        print(f"WARNING: Input house number '{number}' != matched '{matched_house}' (fuzzy match).")

    print(f"\nAddress point (lon/lat): {lon}, {lat}")

    EPSG_MGA94_56 = 28356
    EPSG_MGA2020_56 = 7856

    # Geometry from point (identify-based) — more robust on this service
    rings_94 = _run_arcgis_call(
        f"Geometry (identify) EPSG:{EPSG_MGA94_56}",
        lot_geometry_mga_from_point,
        lon, lat,
        epsg=EPSG_MGA94_56
    )
    rings_20 = _run_arcgis_call(
        f"Geometry (identify) EPSG:{EPSG_MGA2020_56}",
        lot_geometry_mga_from_point,
        lon, lat,
        epsg=EPSG_MGA2020_56
    )

    if not rings_94:
        print(f"\n[WARN] No geometry returned for MGA94 (EPSG:{EPSG_MGA94_56}).")
    if not rings_20:
        print(f"\n[WARN] No geometry returned for MGA2020 (EPSG:{EPSG_MGA2020_56}).")

    # If only one came back, still print what we got (useful for diagnosing outages)
    if rings_94:
        _print_boundary(f"MGA94 Zone 56 (EPSG:{EPSG_MGA94_56})", rings_94)
    if rings_20:
        _print_boundary(f"MGA2020 Zone 56 (EPSG:{EPSG_MGA2020_56})", rings_20)

    if not rings_94 or not rings_20:
        print("\nComparison skipped (need both geometries). Try running again.")
        return


    p94 = _first_point(rings_94)
    p20 = _first_point(rings_20)

    if not p94 or not p20:
        print("\nComparison: not possible (missing geometry).")
        return

    same_mm = (round(p94[0], 3), round(p94[1], 3)) == (round(p20[0], 3), round(p20[1], 3))

    print("\nComparison:")
    print(f"  First point MGA94  : {p94[0]:.3f}, {p94[1]:.3f}")
    print(f"  First point MGA2020: {p20[0]:.3f}, {p20[1]:.3f}")
    print(f"  Identical to 0.001m?: {'YES' if same_mm else 'NO'}")

    print("\nObservation:")
    if same_mm:
        print("  MGA94 and MGA2020 outputs are identical to 0.001 m (with this method).")
    else:
        print("  MGA94 and MGA2020 outputs differ (datum shift appears to be applied).")

                                                  
if __name__ == "__main__":
    main()
