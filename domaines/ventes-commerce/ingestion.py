"""Orchestration d'ingestion du domaine Ventes/Commerce -- brique
specifique au domaine (quel spec, quelles tables raw), s'appuie sur les
adaptateurs generiques de `ingestion/adaptateurs/` (pas reecrits ici).

Clients (fichier clients AS/400) -> remplace (etat courant complet a
chaque export).
Commandes (fichier commandes AS/400) -> ajoute (nouveaux enregistrements
chaque mois, pas de dedoublonnage silencieux -- decision documentee dans
decisions.md).
Remises (Excel v3 + v4_FINAL) -> ajoute les DEUX fichiers tels quels, y
compris leurs divergences -- la reconciliation est une regle de nettoyage
documentee (regles-transformation.md), pas une decision prise ici.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg2

# Les adaptateurs vivent dans ingestion/adaptateurs/ (image Docker
# projet19-ingestion, WORKDIR /app) -- lance avec PYTHONPATH=/app.
from adaptateurs.excel import lire_excel
from adaptateurs.fichier_plat import lire_fichier_plat
from adaptateurs.postgres_writer import ajouter_lignes, remplacer_table

SOURCE_DIR = Path(__file__).parent / "source" / "exports"

CLIENTS_SPEC = [
    ("CLICOD", 8),
    ("CLINOM", 30),
    ("CLIVIL", 20),
    ("CLICP", 5),
]
CMDES_SPEC = [
    ("CLICOD", 8),
    ("CMDNUM", 10),
    ("CMDDAT", 8),
    ("ARTCOD", 6),
    ("QTECMD", 5),
    ("PRIXUN", 10),
    ("MTTHT", 12),
    ("STCMD", 6),
]


def connecter():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "projet19-postgres"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "projet19"),
        user=os.environ.get("PGUSER", "ingestion"),
        password=os.environ["PGPASSWORD"],
    )


def ingerer(conn) -> dict[str, int]:
    resultats: dict[str, int] = {}

    fichiers_clients = sorted(SOURCE_DIR.glob("CLIENTS_AS400_*.txt"))
    if fichiers_clients:
        dernier = fichiers_clients[-1]
        lignes = lire_fichier_plat(dernier, CLIENTS_SPEC)
        resultats["ventes_clients"] = remplacer_table(
            conn, "raw", "ventes_clients", lignes, dernier.name
        )

    total_commandes = 0
    for f in sorted(SOURCE_DIR.glob("CMDES_AS400_*.txt")):
        lignes = lire_fichier_plat(f, CMDES_SPEC)
        total_commandes += ajouter_lignes(conn, "raw", "ventes_commandes", lignes, f.name)
    resultats["ventes_commandes"] = total_commandes

    total_remises = 0
    for f in sorted(SOURCE_DIR.glob("remises_ventes_*.xlsx")):
        lignes = lire_excel(f, sheet_name="Remises", header_row=2)
        total_remises += ajouter_lignes(conn, "raw", "ventes_remises", lignes, f.name)
    resultats["ventes_remises"] = total_remises

    return resultats


def main() -> None:
    conn = connecter()
    try:
        resultats = ingerer(conn)
    finally:
        conn.close()

    for table, n in resultats.items():
        print(f"raw.{table}: {n} lignes chargees")

    assert resultats.get("ventes_clients", 0) > 0, "aucun client charge"
    assert resultats.get("ventes_commandes", 0) > 0, "aucune commande chargee"
    assert resultats.get("ventes_remises", 0) > 0, "aucune remise chargee"
    print("self-check OK")


if __name__ == "__main__":
    main()
