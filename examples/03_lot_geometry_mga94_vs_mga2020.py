"""
Example 03 — Lot boundary geometry: MGA94 vs MGA2020 (demonstration)

Purpose:
This script demonstrates a common GIS issue: a service may report the requested
output spatial reference (outSR) but still return geometry coordinates that are
effectively unchanged.

What this script does:
1) Resolves an address to lon/lat (EPSG:4326).
2) Identifies the Lot / DP at that location.
3) Requests the lot geometry twice:
   - MGA94 / GDA94 Zone 56 (EPSG:28356)
   - MGA2020 / GDA2020 Zone 56 (EPSG:7856)
4) Prints coordinates from both requests and compares them.

Notes for surveyors:
- This is GIS cadastre geometry (DCDB-style), not survey-accurate boundaries.
- If MGA94 and MGA2020 outputs are identical to the mm, the service is not
  applying a datum transformation (even if it reports outSR).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nswspatial.address import address_to_point
from nswspatial.cadastre import lots_plans_from_point, lot_geometry_mga_from_point


def _print_boundary(label: str, rings: list[list[list[float]]], max_points: int = 12) -> None:
    if not rings:
        print(f"\n{label}: [no geometry returned]")
        return

    ring = rings[0]  # most lots: first boundary
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
    # --- Input ---
    number = "39"
    street = "RYAN ST"
    suburb = "LILYFIELD"
    postcode = None

    address = f"{number} {street}"

    EPSG_MGA94_56 = 28356
    EPSG_MGA2020_56 = 7856

    # 1) Address -> lon/lat
    try:
        lon, lat, matched_address, match_count, matched_house = address_to_point(
            address,
            suburb=suburb,
            postcode=postcode
        )
    except RuntimeError as ex:
        print("\nNo address found.")
        print(f"Details: {ex}")
        return

    print(f"\nInput address:   {address}, {suburb}")
    print(f"Matched address: {matched_address}")
    print(f"Address point (lon/lat): {lon}, {lat}")

    # 2) Identify Lot / DP
    hits = lots_plans_from_point(lon, lat)
    if not hits:
        print("\nNo Lot/Plan returned for this address point.")
        print("Tip: try adding suburb/postcode, or check the address match above.")
        return

    if len(hits) == 1:
        lot, sec, plan = hits[0]
        if sec:
            print(f"\nResult: Lot {lot} Sec {sec} in {plan}")
        else:
            print(f"\nResult: Lot {lot} in {plan}")
    else:
        print(f"\nResult: {len(hits)} parcels found at this location:")
        for lot, sec, plan in hits:
            if sec:
                print(f"  Lot {lot} Sec {sec} in {plan}")
            else:
                print(f"  Lot {lot} in {plan}")


    # 3) Geometry requested in two output SRs
    rings_94 = lot_geometry_mga_from_point(lon, lat, epsg=EPSG_MGA94_56)
    rings_20 = lot_geometry_mga_from_point(lon, lat, epsg=EPSG_MGA2020_56)

    _print_boundary(f"MGA94 Zone 56 (EPSG:{EPSG_MGA94_56})", rings_94)
    _print_boundary(f"MGA2020 Zone 56 (EPSG:{EPSG_MGA2020_56})", rings_20)

    # 4) Compare first point (mm-level)
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

    if same_mm:
        print("\nObservation:")
        print("  The service is reporting different outSR values but returning identical coordinates.")
        print("  This suggests the geometry is not being datum-transformed between MGA94 and MGA2020.")
    else:
        print("\nObservation:")
        print("  The service returned different coordinates for MGA94 vs MGA2020 (a datum shift is being applied).")


if __name__ == "__main__":
    main()
