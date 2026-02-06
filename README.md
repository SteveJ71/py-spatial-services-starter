# NSW Spatial Services Python Examples

Simple Python examples showing how to access NSW Spatial Services  
(SIX Maps / Cadastre) using ArcGIS REST APIs.

These scripts are for learning and experimentation with the APIs.

Service reliability can vary. Queries may occasionally be slow,
fail, or return empty results. Re-running often succeeds.

---

## Examples

### 1. Lot / DP from Address  
`examples/01_lot_from_address.py`

- Convert an address to longitude / latitude  
- Identify Lot / DP (and Section where present)  
- Demonstrates fuzzy matches and multiple-lot results

---

### 2. Nearby Lots  
`examples/02_nearby_lots.py`

- Convert an address to a coordinate  
- Find nearby parcels within a distance

---

### 3. Lot Geometry — MGA94 vs MGA2020  
`examples/03_lot_geometry_mga94_vs_mga2020.py`

- Fetch lot boundary geometry  
- Compare MGA94 and MGA2020 outputs  
- Shows that requesting different EPSG codes can return identical coordinates

---

## Install

```bash
pip install -r requirements.txt
```

## Run
```bash
python examples/01_lot_from_address.py
python examples/02_nearby_lots.py
python examples/03_lot_geometry_mga94_vs_mga2020.py
```
