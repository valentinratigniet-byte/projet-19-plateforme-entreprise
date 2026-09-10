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

CDC (Change Data Capture) active sur dbo.Fournisseurs : contrairement a
EcrituresComptables (recree a chaque run -- un flux d'evenements, pas
une fiche qui se modifie), Fournisseurs n'est cree et peuple qu'au
PREMIER lancement -- les lancements suivants appliquent de VRAIES
UPDATE/INSERT sur la table existante (changement d'IBAN, renommage...),
exactement ce qu'un CDC a besoin de voir passer dans le journal de
transactions pour avoir quelque chose a capturer. La relancer detruite
a chaque fois (comme avant) aurait rendu le CDC muet -- DROP TABLE
desactive la capture, il n'y aurait jamais eu de changement a lire.
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


def fournisseurs_deja_crees(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("USE finance_compta")
        cur.execute("SELECT OBJECT_ID('dbo.Fournisseurs', 'U')")
        return cur.fetchone()[0] is not None


def creer_table_fournisseurs_si_absente(conn) -> bool:
    """Jamais de DROP ici (contrairement a EcrituresComptables) -- une
    fiche fournisseur doit survivre entre deux lancements pour que le CDC
    ait de vrais changements a capturer. Renvoie True si la table vient
    d'etre creee (= premier lancement, chargement initial a faire)."""
    if fournisseurs_deja_crees(conn):
        return False
    with conn.cursor() as cur:
        cur.execute("USE finance_compta")
        cur.execute(
            """
            CREATE TABLE dbo.Fournisseurs (
                FournisseurID INT PRIMARY KEY,
                RaisonSociale NVARCHAR(100),
                SIREN VARCHAR(20),
                IBAN VARCHAR(34)
            )
            """
        )
    return True


def creer_table_ecritures(conn):
    with conn.cursor() as cur:
        cur.execute("USE finance_compta")
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


def activer_cdc(conn) -> None:
    """Idempotent : sp_cdc_enable_table renvoie une erreur si deja
    activee, on la tolere. Necessite SQL Server Agent actif
    (MSSQL_AGENT_ENABLED=true) -- c'est le job qu'il lance qui deverse
    le journal de transactions dans les tables de changement ; sans lui
    aucune erreur ne le signale, les tables de changement restent juste
    vides indefiniment."""
    with conn.cursor() as cur:
        cur.execute("USE finance_compta")
        cur.execute("SELECT is_cdc_enabled FROM sys.databases WHERE name = 'finance_compta'")
        if not cur.fetchone()[0]:
            cur.execute("EXEC sys.sp_cdc_enable_db")
        cur.execute(
            "SELECT 1 FROM cdc.change_tables WHERE capture_instance = 'dbo_Fournisseurs'"
        )
        if cur.fetchone() is None:
            cur.execute(
                "EXEC sys.sp_cdc_enable_table @source_schema=N'dbo', "
                "@source_name=N'Fournisseurs', @role_name=NULL, @supports_net_changes=1"
            )


def simuler_maj_fournisseurs(conn, rng: random.Random) -> int:
    """Lancements suivants (table deja peuplee) : quelques fournisseurs
    changent reellement (IBAN, raison sociale -- fusion/rachat), plus une
    petite chance d'un nouveau fournisseur. Ce sont ces UPDATE/INSERT,
    pas le chargement initial, que le CDC est cense capturer."""
    from faker import Faker

    fake = Faker("fr_FR")
    with conn.cursor() as cur:
        cur.execute("USE finance_compta")
        cur.execute("SELECT FournisseurID FROM dbo.Fournisseurs")
        ids = [r[0] for r in cur.fetchall()]

    if not ids:
        return 0

    n_maj = max(1, len(ids) // 20)  # ~5% des fournisseurs changent a chaque run
    modifies = rng.sample(ids, k=min(n_maj, len(ids)))
    with conn.cursor() as cur:
        cur.execute("USE finance_compta")
        for fid in modifies:
            if rng.random() < 0.5:
                cur.execute(
                    "UPDATE dbo.Fournisseurs SET IBAN = %s WHERE FournisseurID = %d",
                    (fake.iban(), fid),
                )
            else:
                cur.execute(
                    "UPDATE dbo.Fournisseurs SET RaisonSociale = %s WHERE FournisseurID = %d",
                    (fake.company(), fid),
                )
        if rng.random() < 0.3:
            nouvel_id = max(ids) + 1
            cur.execute(
                "INSERT INTO dbo.Fournisseurs (FournisseurID, RaisonSociale, SIREN, IBAN) "
                "VALUES (%d, %s, %s, %s)",
                (nouvel_id, fake.company(), str(rng.randint(100000000, 999999999)), fake.iban()),
            )
            modifies.append(nouvel_id)
    return len(modifies)


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

    premier_lancement = creer_table_fournisseurs_si_absente(conn)
    if premier_lancement:
        inserer_fournisseurs(conn, fournisseurs)
        n_changements = len(fournisseurs)
    else:
        n_changements = simuler_maj_fournisseurs(conn, rng)
    activer_cdc(conn)

    creer_table_ecritures(conn)
    ecritures = construire_ecritures(evenements, rng)
    inserer_ecritures(conn, ecritures)
    conn.close()

    mot = "charges (1er lancement)" if premier_lancement else "modifies/ajoutes (CDC)"
    print(f"{n_changements} fournisseurs {mot}, {len(ecritures)} ecritures")


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
