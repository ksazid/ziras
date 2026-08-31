from __future__ import annotations

import os

import psycopg

from common import write_results


def main():
    dsn = os.environ.get("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ziras")
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute("DROP TABLE IF EXISTS interest_fixture")
            cur.execute("CREATE TABLE interest_fixture (name text primary key, embedding vector(4))")
            rows = [
                ("Indian food", "[1,0,0,0]"),
                ("Biryani", "[0.96,0.10,0,0]"),
                ("Korean food", "[0.72,0.60,0,0]"),
                ("Fashion", "[0,0,1,0]"),
                ("Cinema", "[0,0,0,1]"),
            ]
            for name, vector in rows:
                cur.execute("INSERT INTO interest_fixture(name, embedding) VALUES (%s, %s::vector)", (name, vector))
            cur.execute(
                "SELECT name, round((1 - (embedding <=> '[1,0,0,0]'::vector))::numeric, 4) AS similarity FROM interest_fixture ORDER BY embedding <=> '[1,0,0,0]'::vector LIMIT 3"
            )
            nearest = [{"name": name, "similarity": float(sim)} for name, sim in cur.fetchall()]
            ok = nearest[0]["name"] == "Indian food" and nearest[1]["name"] == "Biryani" and "Fashion" not in {x["name"] for x in nearest[:2]}
            cur.execute("SELECT extversion FROM pg_extension WHERE extname='vector'")
            version = cur.fetchone()[0]
    write_results("pgvector", [{"id": "pgvector-interest", "class": "semantic-interest-retrieval", "status": "PASS" if ok else "FAIL", "nearest": nearest, "version": version}])


if __name__ == "__main__":
    main()
