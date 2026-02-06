"""
Example 01 — Lot / DP from an address (NSW Spatial Services)

Prompts for an address, converts it to a coordinate using the
NSW Address Location service, then queries the NSW Cadastre
service for Lot/Plan information.

Personal reference example for working with the NSW Spatial Services APIs.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nswspatial.address import address_to_point
from nswspatial.cadastre import lots_plans_from_point


def _clean_section(sec):
    if sec is None:
        return None
    if isinstance(sec, str) and sec.strip().lower() in ("", "null"):
        return None
    return sec


def main():
    address = input("Enter street address (e.g. 39 RYAN ST): ").strip()
    suburb = input("Enter suburb: ").strip()
    postcode = input("Enter postcode (optional): ").strip() or None

    # Used only for fuzzy house-number warning
    number = address.split()[0] if address else ""

    # Address → coordinate
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

    # Coordinate → Lot/Plan
    try:
        hits = lots_plans_from_point(lon, lat)
    except RuntimeError as ex:
        print(f"\n[ERROR] Cadastre query failed: {ex}")
        print("        This is often a transient NSW ArcGIS service error.")
        print("        Try running again, or try later.")
        return

    if not hits:
        print("\nNo parcels returned.")
        return

    if len(hits) == 1:
        lot, sec, plan = hits[0]
        sec = _clean_section(sec)
        if sec:
            print(f"\nResult: Lot {lot} Sec {sec} in {plan}")
        else:
            print(f"\nResult: Lot {lot} in {plan}")
    else:
        print(f"\nResult: {len(hits)} parcels found:")
        for lot, sec, plan in hits:
            sec = _clean_section(sec)
            if sec:
                print(f"  Lot {lot} Sec {sec} in {plan}")
            else:
                print(f"  Lot {lot} in {plan}")


if __name__ == "__main__":
    main()
