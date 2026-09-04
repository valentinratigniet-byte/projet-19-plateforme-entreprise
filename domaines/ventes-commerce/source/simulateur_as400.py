"""Simule les exports batch nocturnes d'un AS/400 (DB2 for i) de gestion
commerciale : fichiers plats a largeur fixe, conventions AS/400 (noms de
colonnes cryptiques <=10 caracteres, majuscules). Genere plusieurs mois
"vecus" pour que les defauts emergent de l'usage plutot que d'etre
injectes un par un a la main.

Deux fichiers par mois, comme un vrai atelier AS/400 les deposerait :
  CLIENTS_AS400_AAAAMM.txt   - snapshot du fichier clients
  CMDES_AS400_AAAAMM.txt     - commandes du mois

Defauts reels injectes (documentes dans decisions.md / avant.md a venir) :
  - doublons clients (variantes de saisie au fil des mois)
  - commandes referencant un CLICOD absent du fichier clients (FK partielle)
  - statuts de commande orthographies de facon incoherente
  - une periode ou le format de date derive (bug d'export historique)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

fake = Faker("fr_FR")

OUT_DIR = Path(__file__).parent / "exports"

# Largeurs de champs (convention AS/400 : majuscules, <=10 caracteres)
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
    ("PRIXUN", 10),  # centimes, zero-pad
    ("MTTHT", 12),   # centimes, zero-pad
    ("STCMD", 6),
]

ARTICLES = [f"ART{n:03d}" for n in range(1, 41)]
STATUTS_VALIDES = ["VAL", "LIV", "ANN"]
# Variantes "sales" du meme statut logique, rencontrees au fil du temps
STATUTS_VARIANTES = {
    "VAL": ["VAL", "Val", "VALID", "VAL "],
    "LIV": ["LIV", "Liv", "LIVR", "LIV "],
    "ANN": ["ANN", "ANNUL", "Ann", "ANN "],
}


def pad(value: str, width: int) -> str:
    value = str(value)[:width]
    return value.ljust(width)


def pad_num(value: int, width: int) -> str:
    return str(value).rjust(width, "0")[:width]


@dataclass
class Client:
    code: str
    nom: str
    ville: str
    code_postal: str


def generer_clients(n: int, rng: random.Random) -> list[Client]:
    clients = []
    for i in range(1, n + 1):
        clients.append(
            Client(
                code=f"CL{i:06d}",
                nom=fake.company()[:30],
                ville=fake.city()[:20],
                code_postal=fake.postcode(),
            )
        )
    return clients


def injecter_doublons(clients: list[Client], rng: random.Random, taux: float = 0.05) -> list[Client]:
    """~5% des clients ont une variante mal saisie (nom tronque/reformule,
    nouveau code) coexistant avec l'original -- doublon reel, pas un flag."""
    doublons = []
    for c in clients:
        if rng.random() < taux:
            variante_nom = c.nom.upper() if rng.random() < 0.5 else c.nom.replace(" ", "")
            doublons.append(
                Client(
                    code=f"CL{900000 + len(doublons):06d}",
                    nom=variante_nom[:30],
                    ville=c.ville,
                    code_postal=c.code_postal,
                )
            )
    return clients + doublons


def ecrire_fichier(path: Path, spec: list[tuple[str, int]], lignes: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="cp1252", newline="\r\n") as f:
        for ligne in lignes:
            row = "".join(
                pad(ligne[nom], largeur) if isinstance(ligne[nom], str) else pad_num(ligne[nom], largeur)
                for nom, largeur in spec
            )
            f.write(row + "\n")


def generer_mois(
    annee_mois: str,
    clients: list[Client],
    rng: random.Random,
    n_commandes: int,
    date_derive: bool,
) -> tuple[list[dict], list[dict]]:
    lignes_clients = [
        {"CLICOD": c.code, "CLINOM": c.nom, "CLIVIL": c.ville, "CLICP": c.code_postal}
        for c in clients
    ]

    annee, mois = int(annee_mois[:4]), int(annee_mois[4:])
    lignes_cmdes = []
    for i in range(n_commandes):
        jour = rng.randint(1, 28)
        d = date(annee, mois, jour)
        date_str = d.strftime("%d%m%Y") if date_derive else d.strftime("%Y%m%d")

        # ~3% des commandes referencent un client absent (FK partielle :
        # client supprime du fichier clients apres la commande, par ex.)
        if rng.random() < 0.03:
            clicod = f"CL{rng.randint(700000, 799999):06d}"
        else:
            clicod = rng.choice(clients).code

        statut_logique = rng.choices(STATUTS_VALIDES, weights=[0.6, 0.3, 0.1])[0]
        statut = rng.choice(STATUTS_VARIANTES[statut_logique])

        qte = rng.randint(1, 50)
        prix_unitaire_centimes = rng.randint(500, 50000)
        montant_ht_centimes = qte * prix_unitaire_centimes

        lignes_cmdes.append(
            {
                "CLICOD": clicod,
                "CMDNUM": f"{annee_mois}{i:04d}",
                "CMDDAT": date_str,
                "ARTCOD": rng.choice(ARTICLES),
                "QTECMD": qte,
                "PRIXUN": prix_unitaire_centimes,
                "MTTHT": montant_ht_centimes,
                "STCMD": statut,
            }
        )
    return lignes_clients, lignes_cmdes


def main() -> None:
    rng = random.Random(19)
    Faker.seed(19)

    clients = generer_clients(300, rng)
    clients = injecter_doublons(clients, rng)

    # 8 mois simules (2026-01 a 2026-08), volume croissant -- le volume
    # ET les doublons/incoherences emergent de l'usage repete, pas d'un
    # coup de baguette.
    mois_simules = [f"2026{m:02d}" for m in range(1, 9)]
    # Periode ou le format de date a derive : un vrai bug d'export vecu
    # sur 2 mois avant d'etre corrige (a documenter dans avant.md/decisions.md).
    mois_derive = {"202603", "202604"}

    for idx, aaaamm in enumerate(mois_simules):
        n_commandes = 150 + idx * 40  # croissance mensuelle réaliste
        lignes_clients, lignes_cmdes = generer_mois(
            aaaamm, clients, rng, n_commandes, date_derive=aaaamm in mois_derive
        )
        ecrire_fichier(OUT_DIR / f"CLIENTS_AS400_{aaaamm}.txt", CLIENTS_SPEC, lignes_clients)
        ecrire_fichier(OUT_DIR / f"CMDES_AS400_{aaaamm}.txt", CMDES_SPEC, lignes_cmdes)
        print(f"{aaaamm}: {len(lignes_clients)} clients, {len(lignes_cmdes)} commandes -> {OUT_DIR}")


def _self_check() -> None:
    """Verification minimale : les fichiers generes respectent bien la
    largeur de ligne attendue par le spec (sinon le parseur d'ingestion
    plantera silencieusement sur un decalage de colonnes)."""
    largeur_clients = sum(w for _, w in CLIENTS_SPEC)
    largeur_cmdes = sum(w for _, w in CMDES_SPEC)
    for path in OUT_DIR.glob("CLIENTS_AS400_*.txt"):
        with path.open(encoding="cp1252") as f:
            for ligne in f:
                assert len(ligne.rstrip("\n")) == largeur_clients, f"{path}: largeur incorrecte"
    for path in OUT_DIR.glob("CMDES_AS400_*.txt"):
        with path.open(encoding="cp1252") as f:
            for ligne in f:
                assert len(ligne.rstrip("\n")) == largeur_cmdes, f"{path}: largeur incorrecte"
    print("self-check OK: largeur de ligne fixe respectee sur tous les fichiers generes")


if __name__ == "__main__":
    main()
    _self_check()
