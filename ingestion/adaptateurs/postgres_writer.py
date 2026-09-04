"""Ecriture generique dans le schema `raw` -- toutes les colonnes en
TEXT (le brut n'est pas type, le typage arrive en staging dbt), plus
`_ingested_at`/`_source_file` pour la tracabilite. Reutilise par tous les
domaines, pas reecrit a chaque fois."""

from __future__ import annotations

import re

import psycopg2
import psycopg2.extras


def _sanitize_ident(nom: object) -> str:
    """Les en-tetes saisis a la main (ex. 'Remise (%)') ne sont pas des
    identifiants SQL valides -- normalise le NOM de colonne uniquement,
    jamais la valeur : c'est rendre le brut stockable, pas le nettoyer."""
    return re.sub(r"[^A-Za-z0-9_]", "_", str(nom)).strip("_") or "col"


def _ensure_table(conn, schema: str, table: str, colonnes_sql: list[str]) -> None:
    # Le schema lui-meme est cree par l'entrepot (init SQL), pas ici --
    # le role d'ingestion n'a le droit de creer que des tables dans un
    # schema qui existe deja (privilege minimal, cf. entrepot/init/).
    cols_sql = ", ".join(f'"{c}" TEXT' for c in colonnes_sql)
    with conn.cursor() as cur:
        cur.execute(
            f'CREATE TABLE IF NOT EXISTS "{schema}"."{table}" '
            f"(_row_id BIGSERIAL PRIMARY KEY, {cols_sql}, "
            f"_source_file TEXT, _ingested_at TIMESTAMPTZ DEFAULT now())"
        )
    conn.commit()


def _ensure_manifeste(conn, schema: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f'CREATE TABLE IF NOT EXISTS "{schema}"."_fichiers_ingeres" '
            f'("table_cible" TEXT, "source_file" TEXT, "ingere_le" TIMESTAMPTZ DEFAULT now(), '
            f'PRIMARY KEY ("table_cible", "source_file"))'
        )
    conn.commit()


def deja_ingere(conn, schema: str, table: str, source_file: str) -> bool:
    """Idempotence au niveau fichier : un meme fichier source ne doit pas
    etre ajoute deux fois si le workflow (n8n, cron) est rejoue sur des
    fichiers deja traites -- distinct du "pas de dedoublonnage" de
    ajouter_lignes, qui concerne les doublons DEJA presents DANS un
    fichier recu, pas des relances du meme fichier."""
    _ensure_manifeste(conn, schema)
    with conn.cursor() as cur:
        cur.execute(
            f'SELECT 1 FROM "{schema}"."_fichiers_ingeres" '
            f'WHERE "table_cible" = %s AND "source_file" = %s',
            (table, source_file),
        )
        return cur.fetchone() is not None


def _marquer_ingere(conn, schema: str, table: str, source_file: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f'INSERT INTO "{schema}"."_fichiers_ingeres" ("table_cible", "source_file") '
            f"VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (table, source_file),
        )
    conn.commit()


def _preparer(lignes: list[dict], source_file: str):
    colonnes_orig = list(lignes[0].keys())
    colonnes_sql = [_sanitize_ident(c) for c in colonnes_orig]
    rows = [
        tuple(str(ligne[c]) if ligne[c] is not None else None for c in colonnes_orig) + (source_file,)
        for ligne in lignes
    ]
    return colonnes_sql, rows


def remplacer_table(
    conn, schema: str, table: str, lignes: list[dict], source_file: str
) -> int:
    """Truncate + reload -- pour une source qui exporte l'etat courant
    complet a chaque fois (ex. fichier clients AS/400)."""
    if not lignes:
        return 0
    colonnes_sql, rows = _preparer(lignes, source_file)
    _ensure_table(conn, schema, table, colonnes_sql)
    with conn.cursor() as cur:
        cur.execute(f'TRUNCATE "{schema}"."{table}"')
        cols_sql = ", ".join(f'"{c}"' for c in colonnes_sql)
        psycopg2.extras.execute_values(
            cur,
            f'INSERT INTO "{schema}"."{table}" ({cols_sql}, _source_file) VALUES %s',
            rows,
        )
    conn.commit()
    return len(lignes)


def ajouter_lignes(
    conn, schema: str, table: str, lignes: list[dict], source_file: str
) -> int:
    """Append -- pour une source qui exporte des nouveaux enregistrements
    a chaque run (ex. commandes du mois). Idempotent au niveau fichier
    (un `source_file` deja marque ingere est saute -- sinon rejouer le
    workflow n8n dupliquerait tout a chaque execution). Pas de
    dedoublonnage EN REVANCHE sur les lignes a l'interieur d'un fichier :
    le brut garde tout ce qui a ete recu tel quel -- le dedoublonnage
    intra-fichier est une regle de nettoyage documentee, pas une decision
    prise silencieusement a l'ingestion."""
    if not lignes:
        return 0
    if deja_ingere(conn, schema, table, source_file):
        return 0
    colonnes_sql, rows = _preparer(lignes, source_file)
    _ensure_table(conn, schema, table, colonnes_sql)
    with conn.cursor() as cur:
        cols_sql = ", ".join(f'"{c}"' for c in colonnes_sql)
        psycopg2.extras.execute_values(
            cur,
            f'INSERT INTO "{schema}"."{table}" ({cols_sql}, _source_file) VALUES %s',
            rows,
        )
    conn.commit()
    _marquer_ingere(conn, schema, table, source_file)
    return len(lignes)
