"""Adaptateur generique -- MySQL. Un seul lecteur reutilisable."""

from __future__ import annotations

import pymysql
import pymysql.cursors


def lire_mysql(host: str, port: int, user: str, password: str, database: str, requete: str) -> list[dict]:
    conn = pymysql.connect(
        host=host, port=port, user=user, password=password, database=database,
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(requete)
            return list(cur.fetchall())
    finally:
        conn.close()
