# Marketing/Activité — état nettoyé et résultats

## Ce qui a été fait

MySQL (contacts/campagnes/envois) + JSON (événements web) + API SaaS
(stats par polling OAuth2) → adaptateurs d'ingestion → `raw` → snapshot
dbt (SCD2 contacts) → `staging` (nettoyage documenté) → `marts`
(`dim_contact`, `fait_envois`, `fait_evenements_web`,
`fait_performance_campagnes`) → RLS avec minimisation d'accès (Direction
limitée aux agrégats) → **reverse ETL vérifié** (segment poussé vers le
SaaS). 45/45 tests dbt passent (projet entier), 9/9 cas RLS Marketing.

## Résultats chiffrés

| Indicateur | Avant | Après |
|---|---|---|
| Contacts | 206 (0 mojibake réellement visible, mesuré — voir constat ; 5,8% doublons) | 206 (`nom_encodage_suspect` prêt à flaguer si un futur lot en produit ; doublons flagués, visibles) |
| Envois | 755 (statuts en 6+ variantes FR/EN) | 755 (4 statuts canoniques + INCONNU) |
| Cohérence stats SaaS vs MySQL | non vérifiée | **8/8 campagnes cohérentes** |
| Accès de la Direction aux données personnelles | non contrôlé | **aucun** (0 table, vérifié par tentative de lecture réelle) |
| Mécanismes SaaS poussés (OAuth2/polling/webhook/reverse ETL) | non éprouvés | **4/4 vérifiés réellement** (refresh de jeton attendu en conditions réelles, webhook reçu côté destinataire, segment de 124 contacts confirmé reçu) |

## Constat honnête

Le taux de doublons (5,8 %, 12/206) n'a pas été "corrigé" au sens
strict — il a été **rendu visible et mesurable** (`contact_doublon_probable`).
Une fusion automatique aurait été plus impressionnante à montrer, mais
moins honnête sans règle de survivorship métier validée : le choix
assumé est de signaler le problème à la source plutôt que de le masquer
en aval (même raisonnement que Ventes/Commerce).

**Correction de mesure faite avant publication (mesuré, pas inventé) :**
en préparant les schémas avant/après pour ce domaine, une vérification
plus poussée du taux de mojibake documenté (~8 %) a montré que ce
chiffre confondait le **taux de tirage** du générateur (`rng.random() <
0.08` dans `generer_evenements.py`) avec un **taux de défaut réellement
visible**. Le bug simulé (encode UTF-8 → decode latin1) ne produit un
texte visiblement corrompu que si le nom contient déjà un caractère
accentué — sur de l'ASCII pur, l'aller-retour est un no-op. Calcul
exact reproduit sur les 200 contacts canoniques : 8,5 % ont un accent,
8 % subissent le tirage de corruption, l'intersection tombe sur
**0 occurrence visible** (0/206, confirmé en base). `nom_encodage_suspect`
reste un flag légitime et fonctionnel (couvert par un flux de traitement
réel, testable sur un nom volontairement construit) — il se trouve
seulement qu'aucun nom du jeu actuel ne le déclenche. Documenté ici
plutôt que corrigé silencieusement, même discipline que les 2 faux
positifs de housekeeping (Phase 6).

## Recommandations pour l'équipe Marketing/Activité

1. **Corriger la configuration de charset MySQL** (colonnes en
   `utf8mb4` partout, pas un mélange latin1/utf8mb4) — préventif : le
   risque n'a produit aucune corruption visible sur ce jeu de données
   (0/206, un heureux hasard statistique vu le faible taux de noms
   accentués tirés), mais le mauvais paramétrage reste réel et se
   manifesterait sur un jeu de contacts plus riche en noms accentués —
   un correctif d'infrastructure, pas un contournement applicatif à
   répéter à chaque extraction.
2. **Rattacher les contacts par un identifiant stable**, pas par email
   seul — élimine le risque de doublons de ré-inscription à la source.
3. **Le reverse ETL fonctionne, à industrialiser** : la définition du
   segment "contacts engagés" vit dans une requête SQL versionnée
   (`reverse_etl.py`), pas dans l'outil SaaS — permet de faire évoluer
   la logique de ciblage sans dépendre des capacités de segmentation du
   SaaS.
4. **Utiliser `fait_performance_campagnes` comme source de vérité côté
   pilotage** — la cohérence SaaS/MySQL vérifiée (8/8) permet de faire
   confiance à ce mart sans revalidation manuelle à chaque fois.
5. **Les ~3% d'événements web dupliqués** ne faussent pas les analyses
   par campagne (agrégées côté SaaS/MySQL, pas côté événements bruts)
   mais mériteraient un dédoublonnage dédié si une analyse au niveau
   session individuelle est un jour nécessaire.
