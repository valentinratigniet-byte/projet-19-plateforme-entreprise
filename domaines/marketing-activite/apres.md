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
| Contacts | 206 (dont ~8% encodage suspect, ~5% doublons) | 206 (encodage/doublons flagués, visibles) |
| Envois | 755 (statuts en 6+ variantes FR/EN) | 755 (4 statuts canoniques + INCONNU) |
| Cohérence stats SaaS vs MySQL | non vérifiée | **8/8 campagnes cohérentes** |
| Accès de la Direction aux données personnelles | non contrôlé | **aucun** (0 table, vérifié par tentative de lecture réelle) |
| Mécanismes SaaS poussés (OAuth2/polling/webhook/reverse ETL) | non éprouvés | **4/4 vérifiés réellement** (refresh de jeton attendu en conditions réelles, webhook reçu côté destinataire, segment de 124 contacts confirmé reçu) |

## Constat honnête

Le taux de mojibake (~8% des noms) et de doublons (~5%) n'a pas été
"corrigé" au sens strict — il a été **rendu visible et mesurable**. Une
correction automatique du charset aurait été plus impressionnante à
montrer, mais moins honnête : reformater à l'aveugle du texte sur un
encodage déjà corrompu peut fabriquer un résultat qui a l'air correct
sans l'être. Le choix assumé ici est de signaler le problème à la source
plutôt que de le masquer en aval.

## Recommandations pour l'équipe Marketing/Activité

1. **Corriger la configuration de charset MySQL** (colonnes en
   `utf8mb4` partout, pas un mélange latin1/utf8mb4) — un correctif
   d'infrastructure, pas un contournement applicatif à répéter à
   chaque extraction.
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
