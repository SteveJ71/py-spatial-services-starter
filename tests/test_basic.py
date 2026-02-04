
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nswspatial.address import address_to_point
from nswspatial.cadastre import lot_geometry_mga_from_point, lots_plans_from_point


def test_address_resolves():
    lon, lat, *_ = address_to_point(
        "24 EASTBOURNE AVE",
        suburb="CLOVELLY"
    )

    assert -34 < lat < -33
    assert 151 < lon < 152


def test_lot_lookup():
    lon, lat, *_ = address_to_point(
        "24 EASTBOURNE AVE",
        suburb="CLOVELLY"
    )

    hits = lots_plans_from_point(lon, lat)

    assert len(hits) > 0
    lot, sec, plan = hits[0]
    assert lot is not None
    assert plan is not None


def test_geometry():
    lon, lat, *_ = address_to_point(
        "24 EASTBOURNE AVE",
        suburb="CLOVELLY"
    )

    rings = lot_geometry_mga_from_point(lon, lat, epsg=7856)

    assert len(rings) > 0
    assert len(rings[0]) > 3
