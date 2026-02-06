"""
Example 02 — Nearby lots from an address (personal reference)

- Address → lon/lat (EPSG:4326)
- Search parcels within a distance of that point (GIS proximity)

Notes:
- Address match can be fuzzy. Check warnings + matched address.
- Cadastre queries sometimes throw transient ArcGIS 500 errors. This script prints a
  friendly message instead of a traceback.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nswspatial.address import address_to_point
from nswspatial.cadastre import nearby_lots


def _prompt_float(prompt: str, default: float) -> float:
    raw = input(prompt).strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        print(f"Invalid number — using default {default:g}.")
        return default


def main():
    address = input("Enter street address (e.g. 39 RYAN ST): ").strip()
    suburb = input("Enter suburb: ").strip()
    postcode = input("Enter postcode (optional): ").strip() or None

    # Used only for a warning if the address service "fixes" the house number
    number = address.split()[0] if address else ""

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

    print(f"\nInput:   {address}, {suburb}")
    print(f"Matched: {matched_address}")

    if match_count > 1:
        print(f"WARNING: {match_count} possible address matches returned — fuzzy match used.")

    if matched_house and matched_house.strip().upper() != number.strip().upper():
        print(f"WARNING: Input house number '{number}' != matched '{matched_house}' (fuzzy match).")

    print(f"\nAddress point (lon/lat): {lon}, {lat}")

    search_distance_m = _prompt_float("\nEnter search distance in metres (default 50): ", 50.0)

    try:
        lots = nearby_lots(lon, lat, search_distance_m)
    except RuntimeError as ex:
        print(f"\n[ERROR] Cadastre query failed: {ex}")
        print("        This is often a transient NSW ArcGIS service error.")
        print("        Try running again, or try later.")
        return

    if not lots:
        print(f"\nNo lots found within {search_distance_m:g} m.")
        return

    print(f"\nLots within {search_distance_m:g} m:")
    for lot, plan in lots:
        print(f"  Lot {lot} {plan}")


if __name__ == "__main__":
    main()
