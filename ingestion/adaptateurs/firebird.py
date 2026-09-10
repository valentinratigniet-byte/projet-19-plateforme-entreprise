"""Adaptateur Firebird -- un seul lecteur reutilisable, meme principe que
les autres adaptateurs SQL. Contrairement a pymssql/PyMySQL/psycopg2-binary
(auto-suffisants), firebird-driver est un wrapper autour de la bibliotheque
cliente native (`libfbclient2`) -- absente d'une image Python standard,
ajoutee explicitement dans ingestion/Dockerfile."""

from __future__ import annotations

import firebird.driver as fdb


def lire_firebird(host: str, port: int, password: str, database: str, requete: str) -> list[dict]:
    con = fdb.connect(database=f"{host}/{port}:{database}", user="SYSDBA", password=password)
    try:
        cur = con.cursor()
        cur.execute(requete)
        colonnes = [d[0] for d in cur.description]
        return [dict(zip(colonnes, row)) for row in cur.fetchall()]
    finally:
        con.close()
