from __future__ import annotations

import json
import os

import psycopg

from common import write_results


def main():
    dsn = os.environ.get("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ziras")
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
            cur.execute("DROP TABLE IF EXISTS geo_fixture")
            cur.execute("CREATE TABLE geo_fixture (name text primary key, point geography(Point,4326))")
            rows = [
                ("Birkirkara", 14.4611, 35.8972),
                ("Sliema", 14.5042, 35.9122),
                ("St Julians", 14.4883, 35.9181),
                ("Valletta", 14.5146, 35.8989),
                ("Mellieha", 14.3622, 35.9563),
            ]
            for name, lon, lat in rows:
                cur.execute(
                    "INSERT INTO geo_fixture(name, point) VALUES (%s, ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography)",
                    (name, lon, lat),
                )
            cur.execute(
                """
                SELECT name, round(ST_Distance(point, ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography)::numeric/1000, 2)
                FROM geo_fixture
                WHERE ST_DWithin(point, ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography, 5000)
                ORDER BY 2
                """,
                (14.5042, 35.9122, 14.5042, 35.9122),
            )
            nearby = [{"name": name, "km": float(km)} for name, km in cur.fetchall()]
            names = {x["name"] for x in nearby}
            ok = {"Sliema", "St Julians", "Valletta"}.issubset(names) and "Mellieha" not in names
            cur.execute("SELECT postgis_full_version()")
            version = cur.fetchone()[0]
    write_results("postgis", [{"id": "postgis-nearby", "class": "geo-radius", "status": "PASS" if ok else "FAIL", "nearby": nearby, "version": version}])


if __name__ == "__main__":
    main()
