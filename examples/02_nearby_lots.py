"""
Example 02 — Find nearby lots from an address

What this script does:
1) Converts a street address to an approximate coordinate (lon/lat).
2) Searches the NSW cadastre for lots near that point.
3) Prints nearby Lot / DP references.

Notes for surveyors:
- Address positions are approximate.
- Distance search is GIS-based, not survey-accurate adjacency.
- Useful for quick context checks around a property.
"""

import sys
from pathlib import Path

# Allow example scripts to import from the project root.
# This avoids Python packaging setup and keeps the examples easy to run.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nswspatial.address import address_to_point
from nswspatial.cadastre import nearby_lots


def main():
    # --- Input ---
    number = "22"
    street = "EASTBOURNE AVE"
    suburb = "CLOVELLY"
    postcode = None
    search_distance_m = 30  # metres

    address = f"{number} {street}"

   # 1) Address -> coordinate (lon/lat)
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

    # Address services may ignore invalid house numbers and snap to a nearby address
    if matched_house:
        if matched_house.strip() != number.strip():
            print(
                f"WARNING: Input house number '{number}' "
                f"does not match returned '{matched_house}'."
            )
    else:
        print("WARNING: No house number returned by address service.")

    # 2) Search nearby parcels
    lots = nearby_lots(lon, lat, search_distance_m)

    if not lots:
        print(f"\nNo lots found within {search_distance_m} m.")
        return

    print(f"\nLots within {search_distance_m} m:")
    for lot, plan in lots:
        print(f"Lot {lot} {plan}")


if __name__ == "__main__":
    main()
