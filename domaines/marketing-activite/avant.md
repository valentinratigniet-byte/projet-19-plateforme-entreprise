# Marketing/Activité — état brut

Trois sources, simulées mais délibérément hétérogènes
(`source/generer_evenements.py` génère un socle d'événements réels
partagé, consommé par les simulateurs MySQL/JSON), plus une 4e source
comportementale (l'API SaaS mock, `saas-mock/app.py`) — chargées telles
quelles dans `raw`.

## MySQL (contacts + campagnes + envois)

| Métrique | Valeur |
|---|---|
| Contacts | 206 |
| dont casse d'email incohérente | ~10 % |
| dont nom avec encodage suspect (bug charset latin1/utf8mb4) | ~8 % |
| dont doublons probables (ré-inscription, email identique) | ~5 % |
| Campagnes | 8 |
| Envois | 755 |
| dont statut en anglais (stack marketing typique) | variable, mélange FR/EN |

## JSON — flux événementiel web

| Métrique | Valeur |
|---|---|
| Événements (8 mois) | 720 |
| dont UTM source avec typo constatée ("emial") | présent, non exhaustif |
| dont événements domain-dupliqués (retry client) | ~3 % |
| Structure | semi-structurée (objet `contexte` imbriqué à aplatir) |

## API SaaS (mock) — 4 mécanismes poussés vérifiés

| Mécanisme | Vérifié comment |
|---|---|
| OAuth2 (jeton court, 30s, refresh forcé) | Attente réelle de l'expiration (32s), nouveau jeton confirmé différent |
| Polling paginé (`/api/campagnes/stats`) | 8 campagnes récupérées sur plusieurs pages |
| Webhook push (`/webhooks/declencher`) | Réception confirmée côté destinataire (HTTP 200) |
| Reverse ETL (`/api/segments`) | Segment de 124 contacts réellement reçu côté SaaS |

## Constat sur la cohérence inter-sources

Les statistiques de campagnes rapportées par l'API SaaS (calculées côté
"plateforme") et celles recalculées indépendamment depuis MySQL
concordent exactement (`marts.fait_performance_campagnes.coherent_avec_mysql`
= `true` sur les 8 campagnes) — un vrai test de cohérence, pas une
supposition.

## Score qualité initial

- **Identité contact** : pas de clé stable entre systèmes — email seul,
  avec casse incohérente et doublons réels.
- **Encodage** : un sous-ensemble de noms est illisible en l'état
  (mojibake), un vrai bug de configuration MySQL simulé, pas une faute
  de frappe isolée.
- **Rattachement web → campagne** : dépend d'UTM libres, jamais garantis
  cohérents (casse, typo constatée).
