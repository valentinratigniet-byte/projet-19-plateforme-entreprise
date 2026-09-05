"""Adaptateur generique -- API REST paginee avec OAuth2 (client
credentials). Gere l'acquisition ET le refresh du jeton (les jetons
courts d'une vraie SaaS expirent en cours de traitement, pas seulement
au demarrage) -- un seul adaptateur, reutilisable pour toute API du
meme type."""

from __future__ import annotations

import time

import requests


class ClientOAuth2:
    def __init__(self, token_url: str, client_id: str, client_secret: str):
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None
        self._expire_a: float = 0

    def jeton(self) -> str:
        if self._token is None or time.time() >= self._expire_a - 2:
            self._rafraichir()
        return self._token

    def _rafraichir(self) -> None:
        reponse = requests.post(
            self._token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            timeout=10,
        )
        reponse.raise_for_status()
        corps = reponse.json()
        self._token = corps["access_token"]
        self._expire_a = time.time() + corps["expires_in"]


def lire_api_paginee(oauth: ClientOAuth2, url: str, par_page: int = 3) -> list[dict]:
    resultats = []
    page = 1
    while True:
        reponse = requests.get(
            url,
            params={"page": page, "par_page": par_page},
            headers={"Authorization": f"Bearer {oauth.jeton()}"},
            timeout=10,
        )
        reponse.raise_for_status()
        corps = reponse.json()
        resultats.extend(corps["resultats"])
        if not corps.get("a_page_suivante"):
            break
        page += 1
    return resultats


def envoyer_segment(oauth: ClientOAuth2, url: str, segment: dict) -> dict:
    """Reverse ETL -- pousse un segment calcule vers l'API SaaS."""
    reponse = requests.post(
        url,
        json=segment,
        headers={"Authorization": f"Bearer {oauth.jeton()}"},
        timeout=10,
    )
    reponse.raise_for_status()
    return reponse.json()
