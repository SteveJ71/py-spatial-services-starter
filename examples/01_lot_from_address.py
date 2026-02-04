"""
Example 01 — Lot / DP from an address (NSW Spatial Services)

What this script does:
1) Uses the NSW Address Location service to convert a street address
   into an approximate coordinate (longitude / latitude).
2) Uses the NSW Cadastre service to identify the Lot / DP at that location.

Notes for surveyors:
- Address locations are approximate and suitable for locating parcels,
  not for survey control.
- Lot / DP results come from GIS cadastre data, not survey-accurate boundaries.
"""

import sys
from pathlib import Path

# Allow example scripts to import from the project root.
# This avoids Python packaging setup and keeps the examples easy to run.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nswspatial.address import address_to_point
from nswspatial.cadastre import lots_plans_from_point


def main():
    # --- Input ---
    number = "39"
    street = "RYAN ST"
    suburb = "LILYFIELD"
    postcode = None  # optional but improves address matching

    address = f"{number} {street}"

    # 1) Address -> approximate coordinate (lon/lat)
    try:
        lon, lat, matched_address, match_count, matched_house = address_to_point(
            address,
            suburb=suburb,
            postcode=postcode
        )
    except RuntimeError as ex:
        print("\nNo address found.")
        print("Tip: check spelling and try adding suburb + postcode, or abbreviations (ST vs STREET).")
        print(f"Details: {ex}")
        return

    print(f"\nInput address:   {address}, {suburb}")
    print(f"Matched address: {matched_address}")

    if match_count > 1:
        print(f"WARNING: {match_count} possible address matches returned — fuzzy match used.")

    if matched_house and matched_house.strip() != number.strip():
        print(f"WARNING: Input house number '{number}' != matched '{matched_house}' (fuzzy match).")

    print(f"\nAddress point (lon/lat): {lon}, {lat}")

    # 2) Coordinate -> Lot / DP (possibly multiple)
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



if __name__ == "__main__":
    main()
