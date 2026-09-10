"""Adaptateur MongoDB -- un seul lecteur reutilisable, meme principe que
les adaptateurs SQL. Contrairement a eux, ne retourne pas des lignes a
colonnes fixes : un document MongoDB n'a pas de schema garanti (deux
documents de la meme collection peuvent avoir des cles differentes,
cf. domaines/support-client -- derive de schema reelle simulee). Le
JSON est donc transporte tel quel jusqu'au brut Postgres (JSONB), pas
aplati ici -- l'aplatir supposerait un schema qu'un document store ne
garantit justement pas."""

from __future__ import annotations

import json
from datetime import date, datetime

from bson import ObjectId
from pymongo import MongoClient


def _serialisable(valeur):
    """bson.ObjectId et datetime ne sont pas JSON-serialisables tels
    quels -- convertis en texte, pas en int/timestamp : garder la forme
    la plus proche du document source, la conversion de type arrive en
    staging dbt comme pour les autres domaines."""
    if isinstance(valeur, ObjectId):
        return str(valeur)
    if isinstance(valeur, (datetime, date)):
        return valeur.isoformat()
    if isinstance(valeur, dict):
        return {k: _serialisable(v) for k, v in valeur.items()}
    if isinstance(valeur, list):
        return [_serialisable(v) for v in valeur]
    return valeur


def lire_mongodb(
    host: str, port: int, user: str, password: str, database: str, collection: str
) -> list[dict]:
    client = MongoClient(host=host, port=port, username=user, password=password)
    try:
        docs = list(client[database][collection].find())
        return [{"_id": str(d.pop("_id")), "document": json.dumps(_serialisable(d), ensure_ascii=False)} for d in docs]
    finally:
        client.close()
