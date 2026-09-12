#!/usr/bin/env python3
"""Regenerate world-110m.geojson from the Natural Earth 110m admin-0 file.

Source (public domain, Natural Earth):
  https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson

Keeps only the country name and ISO 3166-1 alpha-2 code per feature and
rounds coordinates to 3 decimals (~110 m, far below 1:110m source accuracy).
Natural Earth marks a few countries (France, Norway) with ISO_A2 "-99";
ISO_A2_EH carries the correct code for those.

Run: python3 strip_geo.py ne_110m_admin_0_countries.geojson > world-110m.geojson
"""
import json
import sys


def round_coords(coords):
    if isinstance(coords, (int, float)):
        return round(coords, 3)
    return [round_coords(c) for c in coords]


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        raw = json.load(f)
    features = []
    for feat in raw["features"]:
        props = feat["properties"]
        iso = props.get("ISO_A2")
        if not iso or iso == "-99":
            iso = props.get("ISO_A2_EH", "-99")
        features.append({
            "type": "Feature",
            "properties": {"name": props.get("NAME_EN") or props.get("NAME"), "iso_a2": iso},
            "geometry": {
                "type": feat["geometry"]["type"],
                "coordinates": round_coords(feat["geometry"]["coordinates"]),
            },
        })
    json.dump({"type": "FeatureCollection", "features": features},
              sys.stdout, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
