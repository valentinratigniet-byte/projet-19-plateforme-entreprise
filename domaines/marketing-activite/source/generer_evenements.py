"""Genere la liste canonique des "vrais" evenements marketing (contact,
campagne, envoi, puis evenements web qui en decoulent) -- source de
verite commune consommee par simulateur_mysql.py ET
simulateur_evenements_json.py, meme discipline que Finance/Compta
(evenements partages pour que le funnel envoi->clic->visite mesure un
vrai phenomene, pas deux jeux de donnees sans lien).
"""

from __future__ import annotations

import json
import random
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

OUT_DIR = Path(__file__).parent / "exports"

CAMPAGNES = [
    ("Newsletter mensuelle", "email"),
    ("Promo ete", "email"),
    ("Relance panier abandonne", "email"),
    ("Lancement produit", "email"),
    ("Enquete satisfaction", "email"),
    ("Black friday", "email"),
    ("Bienvenue nouveaux clients", "email"),
    ("Reactivation inactifs", "email"),
]


def _mojibake(texte: str) -> str:
    """Simule un vrai bug d'encodage MySQL (colonne latin1 au lieu
    d'utf8mb4) -- encode en utf-8 puis redecode en latin1, comme un
    vrai mismatch de charset le produirait."""
    try:
        return texte.encode("utf-8").decode("latin1")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return texte


def generer_contacts(n: int, rng: random.Random) -> list[dict]:
    fake = Faker("fr_FR")
    Faker.seed(19)
    contacts = []
    for i in range(1, n + 1):
        prenom, nom = fake.first_name(), fake.last_name()
        email = f"{prenom}.{nom}@{fake.free_email_domain()}".lower()
        if rng.random() < 0.10:
            email = email[0].upper() + email[1:]  # casse incoherente (saisie manuelle/import)
        if rng.random() < 0.08:
            nom = _mojibake(nom)  # bug d'encodage reel
        contacts.append(
            {
                "id": i,
                "email": email,
                "prenom": prenom,
                "nom": nom,
                "date_creation": fake.date_between(start_date="-2y", end_date="-1M").isoformat(),
            }
        )

    # ~5% de doublons (re-inscription avec le meme email, ID different)
    doublons = []
    for c in contacts:
        if rng.random() < 0.05:
            doublons.append({**c, "id": 9000 + len(doublons)})
    return contacts + doublons


def generer_campagnes(rng: random.Random) -> list[dict]:
    campagnes = []
    for i, (nom, type_) in enumerate(CAMPAGNES, start=1):
        mois = ((i - 1) % 8) + 1
        campagnes.append(
            {
                "id": i,
                "nom": nom,
                "type": type_,
                "date_envoi": f"2026-{mois:02d}-{rng.randint(1, 25):02d}",
                "utm_campaign": nom.lower().replace(" ", "_"),
            }
        )
    return campagnes


def generer_envois_et_evenements(
    contacts: list[dict], campagnes: list[dict], rng: random.Random
) -> tuple[list[dict], list[dict]]:
    envois = []
    evenements = []
    session_id = 0

    statuts_variantes = {
        "ENVOYE": ["ENVOYE", "sent", "Sent"],
        "OUVERT": ["OUVERT", "opened", "Open"],
        "CLIQUE": ["CLIQUE", "clicked", "Click"],
        "DESABONNE": ["DESABONNE", "unsubscribed", "Unsub"],
    }

    for campagne in campagnes:
        cibles = rng.sample(contacts, k=min(len(contacts), rng.randint(60, 120)))
        for contact in cibles:
            r = rng.random()
            if r < 0.05:
                statut_logique = "DESABONNE"
            elif r < 0.35:
                statut_logique = "CLIQUE"
            elif r < 0.65:
                statut_logique = "OUVERT"
            else:
                statut_logique = "ENVOYE"

            envois.append(
                {
                    "contact_id": contact["id"],
                    "campagne_id": campagne["id"],
                    "date_envoi": campagne["date_envoi"],
                    "statut": rng.choice(statuts_variantes[statut_logique]),
                }
            )

            if statut_logique == "CLIQUE":
                date_envoi = datetime.fromisoformat(campagne["date_envoi"])
                for _ in range(rng.randint(1, 3)):
                    session_id += 1
                    horodatage = date_envoi + timedelta(
                        hours=rng.randint(0, 48), minutes=rng.randint(0, 59)
                    )
                    # variantes UTM realistes : casse et typos
                    utm_source = rng.choice(["email", "Email", "EMAIL", "emial"])
                    evenements.append(
                        {
                            "session_id": session_id,
                            "contact_id": contact["id"],
                            "type_evenement": rng.choice(["pageview", "pageview", "form_submit"]),
                            "horodatage": horodatage.isoformat(),
                            "utm_source": utm_source,
                            "utm_medium": rng.choice(["email", "newsletter", None]),
                            "utm_campaign": campagne["utm_campaign"],
                            "url": rng.choice(["/produit", "/promo", "/accueil", "/contact"]),
                        }
                    )

    # trafic organique/direct, sans rattachement a une campagne (bruit reel)
    for _ in range(int(len(envois) * 0.3)):
        session_id += 1
        contact = rng.choice(contacts) if rng.random() < 0.4 else None
        jour = rng.randint(1, 28)
        mois = rng.randint(1, 8)
        evenements.append(
            {
                "session_id": session_id,
                "contact_id": contact["id"] if contact else None,
                "type_evenement": rng.choice(["pageview", "pageview", "pageview", "form_submit"]),
                "horodatage": f"2026-{mois:02d}-{jour:02d}T{rng.randint(0,23):02d}:00:00",
                "utm_source": None,
                "utm_medium": None,
                "utm_campaign": None,
                "url": rng.choice(["/produit", "/accueil", "/blog", "/contact"]),
            }
        )

    return envois, evenements


def main() -> None:
    rng = random.Random(19)

    contacts = generer_contacts(200, rng)
    campagnes = generer_campagnes(rng)
    envois, evenements = generer_envois_et_evenements(contacts, campagnes, rng)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "_evenements_communs_marketing.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "contacts": contacts,
                "campagnes": campagnes,
                "envois": envois,
                "evenements_web": evenements,
            },
            f,
            ensure_ascii=False,
        )

    print(
        f"{len(contacts)} contacts, {len(campagnes)} campagnes, "
        f"{len(envois)} envois, {len(evenements)} evenements web"
    )


if __name__ == "__main__":
    main()
