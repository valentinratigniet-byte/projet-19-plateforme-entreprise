"""Adaptateur SQL Server -- Change Data Capture (CDC) natif, pas un diff
applicatif. Contrairement a `sqlserver.lire_sqlserver` (relit toute la
table a chaque appel), celui-ci ne lit que ce qui a reellement change
depuis le dernier LSN traite -- le filtrage se fait cote source, dans le
journal de transactions, pas en comparant deux extractions completes.

Prerequis cote SQL Server (fait par le simulateur, pas ici -- ce module
ne fait que LIRE) :
  EXEC sys.sp_cdc_enable_db;
  EXEC sys.sp_cdc_enable_table @source_schema=N'dbo', @source_name=N'<table>',
       @role_name=NULL, @supports_net_changes=1;
Necessite SQL Server Agent actif (MSSQL_AGENT_ENABLED=true) : c'est le
job de capture qu'il lance qui deverse le journal de transactions dans
les tables de changement -- sans lui, aucune erreur, juste des tables de
changement qui restent vides indefiniment.

Codes `__$operation` (constantes CDC officielles, pas inventees) :
  1 = delete, 2 = insert, 3 = update (image avant), 4 = update (image apres).
L'image "avant" (3) n'est jamais utile pour reconstruire l'etat courant
-- seule l'image "apres" (4) l'est, elle est filtree ici.
"""

from __future__ import annotations

import pymssql

_OPERATION_LABELS = {1: "delete", 2: "insert", 3: "update_before", 4: "update_after"}


def _connecter(host: str, port: int, user: str, password: str, database: str):
    return pymssql.connect(server=host, port=port, user=user, password=password, database=database)


def lsn_actuel_max(host: str, port: int, user: str, password: str, database: str) -> str:
    """LSN le plus recent disponible dans le journal -- utilise pour fixer
    la borne haute d'une lecture, et pour initialiser le filigrane (watermark)
    au moment ou CDC est active, sans rejouer un historique qui n'existe pas."""
    conn = _connecter(host, port, user, password, database)
    try:
        with conn.cursor(as_dict=True) as cur:
            cur.execute("SELECT sys.fn_cdc_get_max_lsn() AS lsn")
            lsn = cur.fetchone()["lsn"]
            return lsn.hex() if lsn else None
    finally:
        conn.close()


def lire_changements(
    host: str,
    port: int,
    user: str,
    password: str,
    database: str,
    capture_instance: str,
    depuis_lsn: str | None,
) -> tuple[list[dict], str | None]:
    """Renvoie (lignes_changees, nouveau_lsn). `depuis_lsn` = None -> lit
    depuis le LSN minimal disponible (tout l'historique de capture, pas
    l'historique de la table -- CDC ne voit rien d'avant son activation).
    Chaque ligne porte `_cdc_operation` (insert/update_after/delete) et
    `_cdc_lsn` -- conservees dans le brut, pas des artefacts internes
    jetes : elles prouvent que la donnee vient reellement du CDC."""
    conn = _connecter(host, port, user, password, database)
    try:
        with conn.cursor(as_dict=True) as cur:
            if depuis_lsn:
                cur.execute(
                    "SELECT sys.fn_cdc_increment_lsn(%s) AS lsn", (bytes.fromhex(depuis_lsn),)
                )
                from_lsn = cur.fetchone()["lsn"]
            else:
                cur.execute(
                    "SELECT sys.fn_cdc_get_min_lsn(%s) AS lsn", (capture_instance,)
                )
                from_lsn = cur.fetchone()["lsn"]

            cur.execute("SELECT sys.fn_cdc_get_max_lsn() AS lsn")
            to_lsn = cur.fetchone()["lsn"]

            if from_lsn is None or to_lsn is None or from_lsn > to_lsn:
                return [], depuis_lsn  # rien de nouveau depuis le dernier appel

            cur.execute(
                f"SELECT * FROM cdc.fn_cdc_get_all_changes_{capture_instance}(%s, %s, 'all')",
                (from_lsn, to_lsn),
            )
            brutes = list(cur)
    finally:
        conn.close()

    lignes = []
    dernier_lsn = depuis_lsn
    for r in brutes:
        operation = _OPERATION_LABELS[r.pop("__$operation")]
        lsn_hex = r.pop("__$start_lsn").hex()
        r.pop("__$seqval", None)
        r.pop("__$update_mask", None)
        if operation == "update_before":
            continue  # image avant : jamais utile pour l'etat courant
        r["_cdc_operation"] = operation
        r["_cdc_lsn"] = lsn_hex
        lignes.append(r)
        if dernier_lsn is None or lsn_hex > dernier_lsn:
            dernier_lsn = lsn_hex

    return lignes, dernier_lsn
