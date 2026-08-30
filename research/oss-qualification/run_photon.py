from __future__ import annotations

import time

import httpx

from common import UA, write_results

MALTA_BOUNDS = {"lat_min": 35.75, "lat_max": 36.10, "lon_min": 14.10, "lon_max": 14.70}
QUERIES = [
    "Sliema, Malta",
    "Birkirkara, Malta",
    "Valletta, Malta",
    "St Julian's, Malta",
    "Mellieha, Malta",
    "Mdina, Malta",
]


def in_malta(lon: float, lat: float) -> bool:
    return MALTA_BOUNDS["lat_min"] <= lat <= MALTA_BOUNDS["lat_max"] and MALTA_BOUNDS["lon_min"] <= lon <= MALTA_BOUNDS["lon_max"]


def main():
    cases = []
    with httpx.Client(headers={"User-Agent": UA}, timeout=15.0, follow_redirects=True) as client:
        for query in QUERIES:
            try:
                response = client.get(
                    "https://photon.komoot.io/api/",
                    params={"q": query, "limit": 1, "lat": 35.9, "lon": 14.5},
                )
                data = response.json()
                features = data.get("features") or []
                if not features:
                    cases.append({"query": query, "status": "NO_RESULT", "http_status": response.status_code})
                else:
                    lon, lat = features[0]["geometry"]["coordinates"]
                    props = features[0].get("properties", {})
                    cases.append({
                        "query": query,
                        "status": "PASS" if in_malta(float(lon), float(lat)) else "OUTSIDE_MALTA",
                        "http_status": response.status_code,
                        "name": props.get("name"),
                        "city": props.get("city"),
                        "country": props.get("country"),
                        "lat": float(lat),
                        "lon": float(lon),
                    })
            except Exception as exc:
                cases.append({"query": query, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"})
            time.sleep(0.8)

        reverse = client.get("https://photon.komoot.io/reverse", params={"lat": 35.8989, "lon": 14.5146, "limit": 1})
        reverse_features = reverse.json().get("features") or []
        reverse_ok = bool(reverse_features)
        reverse_case = {"query": "reverse:Valletta-coordinate", "status": "PASS" if reverse_ok else "NO_RESULT", "http_status": reverse.status_code}
        if reverse_ok:
            reverse_case["properties"] = reverse_features[0].get("properties", {})
        cases.append(reverse_case)

    forward_ok = sum(1 for case in cases[:-1] if case["status"] == "PASS")
    overall = "PASS" if forward_ok >= 5 and reverse_case["status"] == "PASS" else "FAIL"
    write_results("photon", [{"id": "photon-malta", "class": "geocoding", "status": overall, "forward_passes": forward_ok, "forward_total": len(QUERIES), "cases": cases, "production_note": "Public demo is qualification-only; self-host or approved provider is required for production scale."}])


if __name__ == "__main__":
    main()
