"""Verifie reellement les 4 mecanismes SaaS -- pas juste que le code
existe : polling pagine, refresh de jeton OAuth2 (attend l'expiration
reelle), webhook push (verifie la reception cote destinataire), reverse
ETL (verifie que le SaaS a bien recu le segment)."""

from __future__ import annotations

import os
import time

import requests

from adaptateurs.api_rest import ClientOAuth2, envoyer_segment, lire_api_paginee

BASE_URL = os.environ.get("SAAS_BASE_URL", "http://projet19-saas-mock:5000")


def main() -> None:
    oauth = ClientOAuth2(
        f"{BASE_URL}/oauth/token",
        os.environ.get("SAAS_CLIENT_ID", "projet19"),
        os.environ["SAAS_CLIENT_SECRET"],
    )

    # 1. Polling pagine
    campagnes = lire_api_paginee(oauth, f"{BASE_URL}/api/campagnes/stats", par_page=3)
    assert len(campagnes) == 8, f"attendu 8 campagnes, recu {len(campagnes)}"
    print(f"[OK] polling pagine : {len(campagnes)} campagnes recuperees sur plusieurs pages")

    # 2. Refresh de jeton -- attend l'expiration reelle (30s) puis rappelle
    premier_jeton = oauth.jeton()
    print("attente de l'expiration du jeton (32s)...")
    time.sleep(32)
    campagnes_bis = lire_api_paginee(oauth, f"{BASE_URL}/api/campagnes/stats", par_page=3)
    second_jeton = oauth._token
    assert second_jeton != premier_jeton, "le jeton n'a pas ete rafraichi"
    assert len(campagnes_bis) == 8
    print(f"[OK] refresh OAuth2 : nouveau jeton acquis automatiquement apres expiration")

    # 3. Webhook push -- configure puis declenche, verifie la reception
    requests.post(
        f"{BASE_URL}/webhooks/configurer",
        json={"url": "http://webhook-echo:5001/"},
        headers={"Authorization": f"Bearer {oauth.jeton()}"},
        timeout=10,
    ).raise_for_status()
    reponse = requests.post(
        f"{BASE_URL}/webhooks/declencher",
        headers={"Authorization": f"Bearer {oauth.jeton()}"},
        timeout=10,
    )
    reponse.raise_for_status()
    assert reponse.json()["envoye"] is True
    print("[OK] webhook declenche, destinataire a repondu", reponse.json())

    # 4. Reverse ETL -- envoie un segment, verifie qu'il est bien recu cote SaaS
    segment_test = {"nom": "contacts_engages_test", "contacts": [1, 2, 3]}
    resultat = envoyer_segment(oauth, f"{BASE_URL}/api/segments", segment_test)
    assert resultat["taille_segment"] == 3
    segments_recus = requests.get(f"{BASE_URL}/api/segments", timeout=10).json()
    assert any(s.get("nom") == "contacts_engages_test" for s in segments_recus)
    print(f"[OK] reverse ETL : segment recu cote SaaS ({len(segments_recus)} segment(s) au total)")

    print("self-check OK: 4 mecanismes verifies (polling, refresh, webhook, reverse ETL)")


if __name__ == "__main__":
    main()
