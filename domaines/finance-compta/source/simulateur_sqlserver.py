"""Simule un ERP comptable sur SQL Server -- pas un fichier a generer,
directement les tables de la source de production (comme un vrai ETL
lirait une vraie base SQL Server en place). Genere fournisseurs +
ecritures comptables sur 8 mois simules, avec des defauts differents de
ceux du domaine Ventes/Commerce (pas 2x le meme type de "sale") :

  - SIREN parfois absent, mal forme, ou avec espaces
  - montants stockes en texte (varchar), format FR (virgule + espace
    insecable) sur certaines lignes -- import legacy mal configure
  - NumeroFacture avec un format qui NE correspond PAS exactement au
    format utilise cote Factur-X (rapprochement a construire, pas donne)
  - quelques ecritures en double (erreur de saisie comptable reelle)
"""

from __future__ import annotations

import os
import random
from datetime import date, timedelta

import pymssql
from faker import Faker

fake = Faker("fr_FR")


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
        cur.execute(
            "IF DB_ID('finance_compta') IS NULL CREATE DATABASE finance_compta"
        )
    conn.commit() if hasattr(conn, "commit") else None


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


def generer_fournisseurs(n: int, rng: random.Random) -> list[dict]:
    fournisseurs = []
    for i in range(1, n + 1):
        # ~10% de SIREN mal formes ou absents -- defaut reel a rattraper en nettoyage
        r = rng.random()
        if r < 0.05:
            siren = None
        elif r < 0.10:
            siren = f"{rng.randint(100, 999)} {rng.randint(100, 999)} {rng.randint(100, 999)}"  # avec espaces
        else:
            siren = str(rng.randint(100000000, 999999999))

        fournisseurs.append(
            {
                "id": i,
                "raison_sociale": fake.company(),
                "siren": siren,
                "iban": fake.iban(),
            }
        )
    return fournisseurs


def generer_ecritures(
    fournisseurs: list[dict], annee_mois: str, rng: random.Random, n: int
) -> list[dict]:
    annee, mois = int(annee_mois[:4]), int(annee_mois[4:])
    ecritures = []
    for i in range(n):
        f = rng.choice(fournisseurs)
        jour = rng.randint(1, 28)
        d = date(annee, mois, jour)

        montant_ht = round(rng.uniform(80, 15000), 2)
        taux_tva = rng.choice([20.0, 10.0, 5.5])
        montant_ttc = round(montant_ht * (1 + taux_tva / 100), 2)

        # ~15% des montants stockes en texte format FR (virgule) --
        # import legacy incoherent, pas systematique
        if rng.random() < 0.15:
            montant_ht_str = f"{montant_ht:,.2f}".replace(",", " ").replace(".", ",")
            montant_ttc_str = f"{montant_ttc:,.2f}".replace(",", " ").replace(".", ",")
        else:
            montant_ht_str = f"{montant_ht:.2f}"
            montant_ttc_str = f"{montant_ttc:.2f}"

        numero_facture = f"FA{annee_mois}{i:04d}"

        ecritures.append(
            {
                "fournisseur_id": f["id"] if rng.random() > 0.02 else None,  # ~2% orpheline
                "numero_facture": numero_facture,
                "date_ecriture": d,
                "montant_ht": montant_ht_str,
                "taux_tva": str(taux_tva),
                "montant_ttc": montant_ttc_str,
                "compte_comptable": rng.choice(["401100", "401200", "401300"]),
                "statut_paiement": rng.choices(
                    ["PAYEE", "EN_ATTENTE", "REJETEE"], weights=[0.7, 0.25, 0.05]
                )[0],
            }
        )

        # ~1.5% de double-saisie reelle (erreur comptable)
        if rng.random() < 0.015:
            ecritures.append(dict(ecritures[-1]))

    return ecritures


def inserer_fournisseurs(conn, fournisseurs: list[dict]) -> None:
    with conn.cursor() as cur:
        cur.execute("USE finance_compta")
        cur.executemany(
            "INSERT INTO dbo.Fournisseurs (FournisseurID, RaisonSociale, SIREN, IBAN) "
            "VALUES (%d, %s, %s, %s)",
            [(f["id"], f["raison_sociale"], f["siren"], f["iban"]) for f in fournisseurs],
        )


def inserer_ecritures(conn, ecritures: list[dict]) -> None:
    with conn.cursor() as cur:
        cur.execute("USE finance_compta")
        cur.executemany(
            "INSERT INTO dbo.EcrituresComptables "
            "(FournisseurID, NumeroFacture, DateEcriture, MontantHT, TauxTVA, MontantTTC, CompteComptable, StatutPaiement) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            [
                (
                    e["fournisseur_id"],
                    e["numero_facture"],
                    e["date_ecriture"],
                    e["montant_ht"],
                    e["taux_tva"],
                    e["montant_ttc"],
                    e["compte_comptable"],
                    e["statut_paiement"],
                )
                for e in ecritures
            ],
        )


def main() -> None:
    rng = random.Random(19)
    Faker.seed(19)

    conn = connecter()
    creer_schema(conn)
    creer_tables(conn)

    fournisseurs = generer_fournisseurs(80, rng)
    inserer_fournisseurs(conn, fournisseurs)

    mois_simules = [f"2026{m:02d}" for m in range(1, 9)]
    total_ecritures = 0
    for idx, aaaamm in enumerate(mois_simules):
        n = 60 + idx * 15
        ecritures = generer_ecritures(fournisseurs, aaaamm, rng, n)
        inserer_ecritures(conn, ecritures)
        total_ecritures += len(ecritures)
        print(f"{aaaamm}: {len(ecritures)} ecritures")

    conn.close()
    print(f"Total: {len(fournisseurs)} fournisseurs, {total_ecritures} ecritures")


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
