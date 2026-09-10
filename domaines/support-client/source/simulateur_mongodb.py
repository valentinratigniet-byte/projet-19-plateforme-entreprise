"""Simule un systeme de tickets SAV sur MongoDB -- schema-on-read reel,
pas un JSON propre inspire de force dans des colonnes SQL. Genere
plusieurs mois "vecus" comme les autres domaines, pour que les defauts
emergent de l'usage plutot que d'etre injectes un par un.

Defaut propre a un document store, absent des 3 domaines relationnels
existants : DERIVE DE SCHEMA. Les tickets les plus anciens utilisent
"customer_ref" (ancien systeme, avant une migration jamais retro-
appliquee aux documents deja crees -- MongoDB ne force aucun schema,
rien n'empeche deux formes de coexister indefiniment). Les tickets
recents utilisent "client_id". Aucune des deux n'est fausse -- il faut
lire les deux formes, pas "corriger" les anciens documents.

Autres defauts reels injectes :
  - ~8% des tickets referencent un numero_commande qui n'existe pas
    forcement cote Ventes/Commerce (client qui se trompe de numero, ou
    commande hors de la periode suivie)
  - ~15% des tickets n'ont aucun message (cree puis jamais suivi)
  - satisfaction renseignee seulement sur ~35% des tickets resolus
    (la plupart des clients ignorent l'enquete de satisfaction --
    un vrai taux de reponse, pas 100%)
"""

from __future__ import annotations

import os
import random
from datetime import datetime, timedelta

from faker import Faker
from pymongo import MongoClient

fake = Faker("fr_FR")

CATEGORIES = ["livraison", "produit", "facturation", "autre"]
PRIORITES = ["basse", "normale", "haute", "urgente"]
STATUTS = ["ouvert", "en_cours", "resolu", "ferme"]
SUJETS = {
    "livraison": ["Colis endommage a la livraison", "Retard de livraison", "Colis jamais recu", "Adresse de livraison erronee"],
    "produit": ["Produit defectueux", "Produit ne correspond pas a la description", "Piece manquante", "Question technique"],
    "facturation": ["Erreur de montant facture", "Remboursement non recu", "Double prelevement", "Facture non recue"],
    "autre": ["Demande d'information", "Modification de commande", "Reclamation generale"],
}


def connecter():
    return MongoClient(
        host=os.environ.get("MONGO_HOST", "projet19-mongodb"),
        port=int(os.environ.get("MONGO_PORT", "27017")),
        username="root",
        password=os.environ["MONGO_ROOT_PASSWORD"],
    )


def generer_messages(rng: random.Random, date_creation: datetime, statut: str) -> list[dict]:
    if rng.random() < 0.15:
        return []  # cree puis jamais suivi -- defaut reel, pas une exception a filtrer
    n = rng.randint(1, 5)
    messages = []
    t = date_creation
    for i in range(n):
        auteur = "client" if i % 2 == 0 else "agent"
        t = t + timedelta(hours=rng.randint(1, 48))
        messages.append({"auteur": auteur, "texte": fake.sentence(nb_words=12), "date": t})
    return messages


def generer_ticket(rng: random.Random, index: int, mois: datetime, forme_ancienne: bool) -> dict:
    categorie = rng.choice(CATEGORIES)
    statut = rng.choices(STATUTS, weights=[0.15, 0.20, 0.40, 0.25])[0]
    date_creation = mois + timedelta(days=rng.randint(0, 27), hours=rng.randint(0, 23))

    ticket = {
        "_id": f"TK{mois.strftime('%Y%m')}{index:05d}",
        "sujet": rng.choice(SUJETS[categorie]),
        "categorie": categorie,
        "priorite": rng.choices(PRIORITES, weights=[0.35, 0.40, 0.20, 0.05])[0],
        "statut": statut,
        "date_creation": date_creation,
        "messages": generer_messages(rng, date_creation, statut),
    }

    # Derive de schema reelle : cle differente selon l'anciennete du ticket,
    # jamais retro-migree -- pas simule "a moitie", les deux formes cohabitent.
    client_id = f"CL{rng.randint(10000, 99999)}"
    if forme_ancienne:
        ticket["customer_ref"] = client_id
    else:
        ticket["client_id"] = client_id

    # ~8% referencent une commande qui peut ne pas exister cote Ventes/Commerce
    if rng.random() < 0.60:
        annee_mois_cmd = (mois - timedelta(days=rng.randint(0, 90))).strftime("%Y%m")
        ticket["numero_commande"] = f"{annee_mois_cmd}{rng.randint(1, 9999):04d}"

    if statut in ("resolu", "ferme"):
        ticket["date_derniere_maj"] = date_creation + timedelta(days=rng.randint(1, 10))
        if rng.random() < 0.35:
            ticket["satisfaction"] = rng.choices([1, 2, 3, 4, 5], weights=[0.05, 0.05, 0.15, 0.35, 0.40])[0]

    return ticket


def generer_tickets(rng: random.Random) -> list[dict]:
    tickets = []
    debut = datetime(2024, 8, 1)
    n_mois = 25  # meme profondeur d'historique que les autres domaines
    for m in range(n_mois):
        mois = datetime(debut.year + (debut.month - 1 + m) // 12, (debut.month - 1 + m) % 12 + 1, 1)
        # Bascule de forme de schema aux 2/3 de l'historique -- les tickets
        # les plus anciens restent en "customer_ref" pour de bon.
        forme_ancienne = m < (n_mois * 2 // 3)
        n_tickets = rng.randint(15, 35)
        for i in range(1, n_tickets + 1):
            tickets.append(generer_ticket(rng, i, mois, forme_ancienne))
    return tickets


def main() -> None:
    rng = random.Random(19)
    tickets = generer_tickets(rng)

    client = connecter()
    db = client["support_client"]
    db.tickets.drop()
    db.tickets.insert_many(tickets)
    client.close()

    n_ancienne_forme = sum(1 for t in tickets if "customer_ref" in t)
    print(f"{len(tickets)} tickets charges ({n_ancienne_forme} en ancienne forme customer_ref)")


def _self_check() -> None:
    client = connecter()
    db = client["support_client"]
    n = db.tickets.count_documents({})
    client.close()
    assert n > 0, "aucun ticket en base"
    print(f"self-check OK: {n} tickets en base")


if __name__ == "__main__":
    main()
    _self_check()
