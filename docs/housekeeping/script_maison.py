"""Script maison de housekeeping -- index inutilises + estimation de
bloat, sur les 3 vraies bases du projet (Postgres/entrepot, SQL Server,
MySQL). L'AS/400 n'a pas de base a auditer (simule en fichiers plats,
pas de connexion live -- cf. domaines/ventes-commerce/decisions.md), pas
inclus ici pour cette raison structurelle, pas un oubli.

Sert de point de comparaison face a pgHero (deploye reellement) et
pganalyze (compare sur documentation, outil payant) -- cf.
docs/housekeeping/comparatif.md.
"""

from __future__ import annotations

import os

import psycopg2
import pymssql
import pymysql
import pymysql.cursors


def verifier_postgres() -> None:
    conn = psycopg2.connect(
        host=os.environ.get("PGHOST", "projet19-postgres"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "projet19"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ["PGSUPERUSER_PASSWORD"],
    )
    print("=== POSTGRES (entrepôt) ===")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.schemaname, s.relname, s.indexrelname, s.idx_scan
            FROM pg_stat_user_indexes s
            JOIN pg_index i ON s.indexrelid = i.indexrelid
            WHERE s.idx_scan = 0
              AND NOT i.indisprimary  -- une PK sert a l'unicite, pas seulement aux lectures ;
                                      -- idx_scan=0 dessus ne veut pas dire "a supprimer"
              AND s.schemaname IN ('raw', 'staging', 'marts', 'raw_historise')
            ORDER BY s.schemaname, s.relname
            """
        )
        non_utilises = cur.fetchall()
        print(f"Index non-PK jamais scannés depuis la création (candidats à revue) : {len(non_utilises)}")
        for schema, table, index, scans in non_utilises[:15]:
            print(f"  - {schema}.{table}.{index}")

        cur.execute(
            """
            SELECT schemaname, relname, n_live_tup, n_dead_tup,
                   round(100.0 * n_dead_tup / nullif(n_live_tup + n_dead_tup, 0), 1) AS pct_mort
            FROM pg_stat_user_tables
            WHERE schemaname IN ('raw', 'staging', 'marts', 'raw_historise')
              AND n_dead_tup > 0
            ORDER BY pct_mort DESC NULLS LAST
            """
        )
        bloat = cur.fetchall()
        print(f"Tables avec des lignes mortes (bloat potentiel) : {len(bloat)}")
        for schema, table, live, dead, pct in bloat[:15]:
            print(f"  - {schema}.{table}: {dead} lignes mortes / {live} vivantes ({pct}%)")
    conn.close()


def verifier_sqlserver() -> None:
    conn = pymssql.connect(
        server=os.environ.get("MSSQL_HOST", "projet19-sqlserver"),
        port=int(os.environ.get("MSSQL_PORT", "1433")),
        user="sa",
        password=os.environ["MSSQL_SA_PASSWORD"],
        database="finance_compta",
    )
    print("=== SQL SERVER (Finance/Compta) ===")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT OBJECT_NAME(ips.object_id) AS table_name, i.name AS index_name,
                   ips.avg_fragmentation_in_percent
            FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') ips
            JOIN sys.indexes i ON ips.object_id = i.object_id AND ips.index_id = i.index_id
            JOIN sys.tables t ON ips.object_id = t.object_id
            WHERE t.is_ms_shipped = 0
              AND ips.avg_fragmentation_in_percent > 10 AND i.name IS NOT NULL
            ORDER BY ips.avg_fragmentation_in_percent DESC
            """
        )
        fragmentes = cur.fetchall()
        print(f"Index fragmentés (>10%) : {len(fragmentes)}")
        for table, index, frag in fragmentes:
            print(f"  - {table}.{index}: {frag:.1f}% fragmenté")

        cur.execute(
            """
            SELECT OBJECT_NAME(i.object_id) AS table_name, i.name AS index_name
            FROM sys.indexes i
            JOIN sys.tables t ON i.object_id = t.object_id
            LEFT JOIN sys.dm_db_index_usage_stats s
                ON i.object_id = s.object_id AND i.index_id = s.index_id AND s.database_id = DB_ID()
            WHERE t.is_ms_shipped = 0
              AND i.type_desc <> 'HEAP' AND i.is_primary_key = 0 AND i.name IS NOT NULL
              AND (s.user_seeks IS NULL AND s.user_scans IS NULL AND s.user_lookups IS NULL)
            """
        )
        non_utilises = cur.fetchall()
        print(f"Index secondaires jamais utilisés depuis le démarrage : {len(non_utilises)}")
        for table, index in non_utilises:
            print(f"  - {table}.{index}")
    conn.close()


def verifier_mysql() -> None:
    conn = pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "projet19-mysql"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user="root",
        password=os.environ["MYSQL_ROOT_PASSWORD"],
        database="marketing_activite",
        cursorclass=pymysql.cursors.Cursor,
    )
    print("=== MYSQL (Marketing/Activité) ===")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name, data_free, data_length
            FROM information_schema.tables
            WHERE table_schema = 'marketing_activite' AND data_free > 0
            """
        )
        fragmente = cur.fetchall()
        print(f"Tables avec de l'espace libre non récupéré (fragmentation) : {len(fragmente)}")
        for table, data_free, data_length in fragmente:
            print(f"  - {table}: {data_free} octets libres / {data_length} occupés")

        try:
            cur.execute("SELECT object_schema, object_name, index_name FROM sys.schema_unused_indexes WHERE object_schema = 'marketing_activite'")
            non_utilises = cur.fetchall()
            print(f"Index jamais utilisés (via performance_schema) : {len(non_utilises)}")
            for schema, table, index in non_utilises:
                print(f"  - {table}.{index}")
        except pymysql.err.OperationalError as exc:
            print(f"Détection des index inutilisés indisponible (performance_schema désactivé) : {exc}")
    conn.close()


if __name__ == "__main__":
    verifier_postgres()
    print()
    verifier_sqlserver()
    print()
    verifier_mysql()
