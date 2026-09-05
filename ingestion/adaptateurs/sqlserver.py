"""Adaptateur generique -- SQL Server. Un seul lecteur reutilisable,
pas un par domaine."""

from __future__ import annotations

import pymssql


def lire_sqlserver(
    host: str, port: int, user: str, password: str, database: str, requete: str
) -> list[dict]:
    conn = pymssql.connect(
        server=host, port=port, user=user, password=password, database=database
    )
    try:
        with conn.cursor(as_dict=True) as cur:
            cur.execute(requete)
            return list(cur)
    finally:
        conn.close()
