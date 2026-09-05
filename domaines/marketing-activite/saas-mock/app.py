"""Mock d'une API SaaS marketing type Mailchimp/Brevo -- simule les 4
aspects "pousses" du cadrage (issue #2) :
  1. Polling paginé  -> GET /api/campagnes/stats (Bearer token requis)
  2. OAuth2           -> POST /oauth/token (client_credentials, jetons
                         courts, force un vrai cycle de refresh)
  3. Push (webhook)   -> POST /webhooks/declencher envoie les evenements
                         recents vers l'URL configuree via
                         /webhooks/configurer
  4. Reverse ETL      -> POST /api/segments (l'entrepot y depose un
                         segment calcule, ex. contacts a risque)

Donnees de stats calculees a partir des evenements canoniques
(generer_evenements.py) -- des metriques agregees que MySQL n'expose pas
tel quel (taux d'ouverture/clic par campagne), pas une redite des donnees
deja disponibles ailleurs.
"""

from __future__ import annotations

import json
import os
import secrets
import time
from pathlib import Path

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

CLIENT_ID = os.environ.get("SAAS_CLIENT_ID", "projet19")
CLIENT_SECRET = os.environ.get("SAAS_CLIENT_SECRET", "change-me")
TOKEN_TTL_SECONDES = 30  # court expres -- force un vrai cycle de refresh a l'usage

EVENEMENTS_PATH = Path(os.environ.get("EVENEMENTS_PATH", "/data/_evenements_communs_marketing.json"))

_tokens_valides: dict[str, float] = {}
_webhook_url: str | None = None
_segments_recus: list[dict] = []


def _charger_stats_campagnes() -> list[dict]:
    with EVENEMENTS_PATH.open(encoding="utf-8") as f:
        donnees = json.load(f)
    campagnes, envois = donnees["campagnes"], donnees["envois"]

    stats = []
    for c in campagnes:
        lies = [e for e in envois if e["campagne_id"] == c["id"]]
        n_envoyes = len(lies)
        n_ouverts = sum(1 for e in lies if e["statut"].upper() in ("OUVERT", "OPENED", "OPEN", "CLIQUE", "CLICKED", "CLICK"))
        n_clics = sum(1 for e in lies if e["statut"].upper() in ("CLIQUE", "CLICKED", "CLICK"))
        n_desabo = sum(1 for e in lies if e["statut"].upper() in ("DESABONNE", "UNSUBSCRIBED", "UNSUB"))
        stats.append(
            {
                "campagne_id": c["id"],
                "nom": c["nom"],
                "envoyes": n_envoyes,
                "ouverts": n_ouverts,
                "clics": n_clics,
                "desabonnements": n_desabo,
                "taux_ouverture": round(n_ouverts / n_envoyes, 4) if n_envoyes else 0,
                "taux_clic": round(n_clics / n_envoyes, 4) if n_envoyes else 0,
            }
        )
    return stats


def _verifier_token() -> bool:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    token = auth[len("Bearer ") :]
    expiration = _tokens_valides.get(token)
    if expiration is None or time.time() > expiration:
        return False
    return True


@app.post("/oauth/token")
def oauth_token():
    if request.form.get("grant_type") != "client_credentials":
        return jsonify({"error": "unsupported_grant_type"}), 400
    if request.form.get("client_id") != CLIENT_ID or request.form.get("client_secret") != CLIENT_SECRET:
        return jsonify({"error": "invalid_client"}), 401

    token = secrets.token_urlsafe(24)
    _tokens_valides[token] = time.time() + TOKEN_TTL_SECONDES
    return jsonify({"access_token": token, "token_type": "Bearer", "expires_in": TOKEN_TTL_SECONDES})


@app.get("/api/campagnes/stats")
def campagnes_stats():
    if not _verifier_token():
        return jsonify({"error": "invalid_token"}), 401

    page = int(request.args.get("page", 1))
    par_page = int(request.args.get("par_page", 3))
    toutes = _charger_stats_campagnes()
    debut = (page - 1) * par_page
    page_courante = toutes[debut : debut + par_page]

    return jsonify(
        {
            "page": page,
            "par_page": par_page,
            "total": len(toutes),
            "a_page_suivante": debut + par_page < len(toutes),
            "resultats": page_courante,
        }
    )


@app.post("/webhooks/configurer")
def webhooks_configurer():
    global _webhook_url
    if not _verifier_token():
        return jsonify({"error": "invalid_token"}), 401
    _webhook_url = request.json.get("url")
    return jsonify({"configure": True, "url": _webhook_url})


@app.post("/webhooks/declencher")
def webhooks_declencher():
    """Simule l'envoi push d'evenements recents vers le webhook configure
    -- appele manuellement ici (au lieu d'un vrai cron temps reel cote
    SaaS), mais fait un vrai appel HTTP sortant, pas une simulation en
    memoire."""
    if not _verifier_token():
        return jsonify({"error": "invalid_token"}), 401
    if not _webhook_url:
        return jsonify({"error": "no_webhook_configured"}), 400

    stats = _charger_stats_campagnes()
    evenement = {"type": "campagne.stats_mises_a_jour", "campagnes": stats[:2]}
    try:
        reponse = requests.post(_webhook_url, json=evenement, timeout=5)
        return jsonify({"envoye": True, "statut_destinataire": reponse.status_code})
    except requests.RequestException as exc:
        return jsonify({"envoye": False, "erreur": str(exc)}), 502


@app.post("/api/segments")
def api_segments():
    """Reverse ETL : l'entrepot depose ici un segment calcule."""
    if not _verifier_token():
        return jsonify({"error": "invalid_token"}), 401
    segment = request.json
    _segments_recus.append(segment)
    return jsonify({"recu": True, "taille_segment": len(segment.get("contacts", []))})


@app.get("/api/segments")
def api_segments_liste():
    """Endpoint de verification (pas dans un vrai SaaS) -- liste ce qui a
    ete recu, pour prouver que le reverse ETL a bien ecrit quelque chose."""
    return jsonify(_segments_recus)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
