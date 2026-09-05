"""Simule un CRM/stack web sur MySQL -- comme le domaine Finance/Compta,
la base EST la source de production (pas un fichier a generer). Consomme
les evenements canoniques de `generer_evenements.py` (contacts/campagnes/
envois partages avec le flux JSON, pour un funnel envoi->clic->visite
reel, meme discipline que Finance).

Defauts propres a ce canal (distincts d'AS/400 et SQL Server) :
  - emails a la casse incoherente (~10%)
  - mojibake reel sur certains noms (colonne mal configuree en latin1 --
    encode utf-8 puis stocke/relu en latin1, comme un vrai bug de charset)
  - ~5% de contacts en double (re-inscription, email identique, ID different)
  - statuts d'envoi en anglais ET francais, casse variable (stack web
    typique, melange d'origines)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pymysql

EVENEMENTS_PATH = Path(__file__).parent / "exports" / "_evenements_communs_marketing.json"


def connecter():
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "projet19-mysql"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user="root",
        password=os.environ["MYSQL_ROOT_PASSWORD"],
        database="marketing_activite",
        charset="utf8mb4",
    )


def creer_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS envois")
        cur.execute("DROP TABLE IF EXISTS contacts")
        cur.execute("DROP TABLE IF EXISTS campagnes")
        cur.execute(
            """
            CREATE TABLE contacts (
                id INT PRIMARY KEY,
                email VARCHAR(255),
                prenom VARCHAR(100),
                nom VARCHAR(100),
                date_creation DATE
            ) CHARACTER SET utf8mb4
            """
        )
        cur.execute(
            """
            CREATE TABLE campagnes (
                id INT PRIMARY KEY,
                nom VARCHAR(200),
                type VARCHAR(20),
                date_envoi DATE,
                utm_campaign VARCHAR(100)
            ) CHARACTER SET utf8mb4
            """
        )
        cur.execute(
            """
            CREATE TABLE envois (
                id INT AUTO_INCREMENT PRIMARY KEY,
                contact_id INT,
                campagne_id INT,
                date_envoi DATE,
                statut VARCHAR(20)
            ) CHARACTER SET utf8mb4
            """
        )
    conn.commit()


def inserer(conn, contacts: list[dict], campagnes: list[dict], envois: list[dict]) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO contacts (id, email, prenom, nom, date_creation) VALUES (%s, %s, %s, %s, %s)",
            [(c["id"], c["email"], c["prenom"], c["nom"], c["date_creation"]) for c in contacts],
        )
        cur.executemany(
            "INSERT INTO campagnes (id, nom, type, date_envoi, utm_campaign) VALUES (%s, %s, %s, %s, %s)",
            [(c["id"], c["nom"], c["type"], c["date_envoi"], c["utm_campaign"]) for c in campagnes],
        )
        cur.executemany(
            "INSERT INTO envois (contact_id, campagne_id, date_envoi, statut) VALUES (%s, %s, %s, %s)",
            [(e["contact_id"], e["campagne_id"], e["date_envoi"], e["statut"]) for e in envois],
        )
    conn.commit()


def main() -> None:
    with EVENEMENTS_PATH.open(encoding="utf-8") as f:
        donnees = json.load(f)

    conn = connecter()
    creer_tables(conn)
    inserer(conn, donnees["contacts"], donnees["campagnes"], donnees["envois"])
    conn.close()

    print(f"{len(donnees['contacts'])} contacts, {len(donnees['campagnes'])} campagnes, {len(donnees['envois'])} envois")


def _self_check() -> None:
    conn = connecter()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM contacts")
        (n_contacts,) = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM envois")
        (n_envois,) = cur.fetchone()
    conn.close()
    assert n_contacts > 0, "aucun contact"
    assert n_envois > 0, "aucun envoi"
    print(f"self-check OK: {n_contacts} contacts, {n_envois} envois en base")


if __name__ == "__main__":
    main()
    _self_check()
