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
| dont tirage "corruption d'encodage" appliqué par le simulateur | 8 % (paramètre du générateur, pas un défaut visible) |
| dont mojibake **réellement visible** dans les données actuelles | **0 %** (0/206, mesuré — voir constat ci-dessous) |
| dont doublons probables (ré-inscription, email identique) | 5,8 % (12/206) |
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
- **Encodage** : le simulateur applique un vrai bug de configuration
  MySQL (colonne latin1 au lieu d'utf8mb4, `source/generer_evenements.py::_mojibake`)
  sur un tirage aléatoire de 8 % des noms — **mais ce bug ne devient
  visible que sur un nom qui contient déjà un accent** (le round-trip
  UTF-8 → latin1 est un no-op sur de l'ASCII pur). Mesuré précisément :
  8,5 % des 200 noms canoniques ont un accent, 8 % subissent le tirage
  de corruption, l'intersection donne **0 occurrence visible sur ce
  jeu de données** (0/206) — un résultat plausible, pas un bug du
  générateur (voir le calcul détaillé dans `apres.md`). Documenté
  précisément après avoir trouvé et corrigé une erreur de mesure : une
  première version de cette doc rapportait "~8 % d'encodage suspect" en
  confondant le taux de tirage du générateur avec un taux de défaut
  réellement observé dans les données.
- **Rattachement web → campagne** : dépend d'UTM libres, jamais garantis
  cohérents (casse, typo constatée).
