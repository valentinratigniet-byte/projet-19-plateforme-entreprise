"""Simule un ERP comptable sur SQL Server -- pas un fichier a generer,
directement les tables de la source de production (comme un vrai ETL
lirait une vraie base SQL Server en place).

Consomme les evenements canoniques de `generer_evenements.py` (montants
reels partages avec Factur-X, pour que le rapprochement facture/ecriture
mesure un vrai taux de couverture) -- lancer generer_evenements.py avant
ce script. Defauts propres a CE canal, differents de ceux du domaine
Ventes/Commerce :

  - montants stockes en texte, format FR (virgule + espace) sur ~15% des
    lignes -- import legacy mal configure
  - ~2% des ecritures avec un FournisseurID orphelin (saisie manuelle
    erronee, pas dans le meme referentiel que les evenements)
  - ~1.5% de doublons de saisie comptable exacts (double-clic reel)
"""

from __future__ import annotations

import json
import os
import random
from datetime import date
from pathlib import Path

import pymssql

EVENEMENTS_PATH = Path(__file__).parent / "exports" / "_evenements_communs.json"


def connecter():
    return pymssql.connect(
        server=os.environ.get("MSSQL_HOST", "projet19-sqlserver"),
        port=int(os.environ.get("MSSQL_PORT", "1433")),
        user="sa",
        password=os.environ["MSSQL_SA_PASSWORD"],
        database="master",
        autocommit=True,
    )


def creer_schema(conn):
    with conn.cursor() as cur:
        cur.execute("IF DB_ID('finance_compta') IS NULL CREATE DATABASE finance_compta")


def creer_tables(conn):
    with conn.cursor() as cur:
        cur.execute("USE finance_compta")
        cur.execute(
            """
            IF OBJECT_ID('dbo.Fournisseurs', 'U') IS NOT NULL DROP TABLE dbo.Fournisseurs;
            CREATE TABLE dbo.Fournisseurs (
                FournisseurID INT PRIMARY KEY,
                RaisonSociale NVARCHAR(100),
                SIREN VARCHAR(20),
                IBAN VARCHAR(34)
            )
            """
        )
        cur.execute(
            """
            IF OBJECT_ID('dbo.EcrituresComptables', 'U') IS NOT NULL DROP TABLE dbo.EcrituresComptables;
            CREATE TABLE dbo.EcrituresComptables (
                EcritureID INT IDENTITY PRIMARY KEY,
                FournisseurID INT NULL,
                NumeroFacture VARCHAR(30),
                DateEcriture DATE,
                MontantHT VARCHAR(20),
                TauxTVA VARCHAR(10),
                MontantTTC VARCHAR(20),
                CompteComptable VARCHAR(10),
                StatutPaiement VARCHAR(20)
            )
            """
        )


def inserer_fournisseurs(conn, fournisseurs: list[dict]) -> None:
    with conn.cursor() as cur:
        cur.execute("USE finance_compta")
        cur.executemany(
            "INSERT INTO dbo.Fournisseurs (FournisseurID, RaisonSociale, SIREN, IBAN) VALUES (%d, %s, %s, %s)",
            [(f["id"], f["raison_sociale"], f["siren"], None) for f in fournisseurs],
        )
        # IBAN genere separement (pas dans les evenements communs, pas pertinent au rapprochement)
        from faker import Faker

        fake = Faker("fr_FR")
        Faker.seed(19)
        ibans = [fake.iban() for _ in fournisseurs]
        cur.executemany(
            "UPDATE dbo.Fournisseurs SET IBAN = %s WHERE FournisseurID = %d",
            [(iban, f["id"]) for iban, f in zip(ibans, fournisseurs)],
        )


def construire_ecritures(evenements: list[dict], rng: random.Random) -> list[dict]:
    ecritures = []
    for e in evenements:
        if not e["a_ecriture"]:
            continue

        montant_ht, montant_ttc = e["montant_ht"], e["montant_ttc"]
        if rng.random() < 0.15:
            montant_ht_str = f"{montant_ht:,.2f}".replace(",", " ").replace(".", ",")
            montant_ttc_str = f"{montant_ttc:,.2f}".replace(",", " ").replace(".", ",")
        else:
            montant_ht_str = f"{montant_ht:.2f}"
            montant_ttc_str = f"{montant_ttc:.2f}"

        fournisseur_id = e["fournisseur_id"] if rng.random() > 0.02 else None
        numero_facture = f"FA{e['annee_mois']}{e['index']:04d}"

        ecritures.append(
            {
                "fournisseur_id": fournisseur_id,
                "numero_facture": numero_facture,
                "date_ecriture": date(e["annee"], e["mois"], e["jour"]),
                "montant_ht": montant_ht_str,
                "taux_tva": "20.0",
                "montant_ttc": montant_ttc_str,
                "compte_comptable": rng.choice(["401100", "401200", "401300"]),
                "statut_paiement": rng.choices(
                    ["PAYEE", "EN_ATTENTE", "REJETEE"], weights=[0.7, 0.25, 0.05]
                )[0],
            }
        )
        if rng.random() < 0.015:
            ecritures.append(dict(ecritures[-1]))
    return ecritures


def inserer_ecritures(conn, ecritures: list[dict]) -> None:
    with conn.cursor() as cur:
        cur.execute("USE finance_compta")
        cur.executemany(
            "INSERT INTO dbo.EcrituresComptables "
            "(FournisseurID, NumeroFacture, DateEcriture, MontantHT, TauxTVA, MontantTTC, CompteComptable, StatutPaiement) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            [
                (
                    e["fournisseur_id"], e["numero_facture"], e["date_ecriture"],
                    e["montant_ht"], e["taux_tva"], e["montant_ttc"],
                    e["compte_comptable"], e["statut_paiement"],
                )
                for e in ecritures
            ],
        )


def main() -> None:
    rng = random.Random(19)

    with EVENEMENTS_PATH.open(encoding="utf-8") as f:
        donnees = json.load(f)
    fournisseurs, evenements = donnees["fournisseurs"], donnees["evenements"]

    conn = connecter()
    creer_schema(conn)
    creer_tables(conn)
    inserer_fournisseurs(conn, fournisseurs)

    ecritures = construire_ecritures(evenements, rng)
    inserer_ecritures(conn, ecritures)
    conn.close()

    print(f"{len(fournisseurs)} fournisseurs, {len(ecritures)} ecritures")


def _self_check() -> None:
    conn = connecter()
    with conn.cursor() as cur:
        cur.execute("USE finance_compta")
        cur.execute("SELECT COUNT(*) FROM dbo.Fournisseurs")
        (n_fournisseurs,) = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM dbo.EcrituresComptables")
        (n_ecritures,) = cur.fetchone()
    conn.close()
    assert n_fournisseurs > 0, "aucun fournisseur"
    assert n_ecritures > 0, "aucune ecriture"
    print(f"self-check OK: {n_fournisseurs} fournisseurs, {n_ecritures} ecritures en base")


if __name__ == "__main__":
    main()
    _self_check()
