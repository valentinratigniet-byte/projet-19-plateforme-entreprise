-- RLS multi-roles sur les marts Ventes/Commerce (marts.fait_ventes,
-- marts.dim_client). Roles applicatifs (NOLOGIN -- des groupes, pas des
-- comptes de connexion directs), a assigner aux vrais utilisateurs/apps
-- via GRANT role TO user une fois la connectique BI branchee.
--
-- Choix de perimetre par role, documente dans decisions.md :
--   role_rh          : aucun acces -- pas de justification metier a voir
--                       la donnee commerciale.
--   role_finance      : acces complet (reconciliation budgetaire, y
--                       compris les commandes annulees pour les
--                       depreciations).
--   role_direction    : acces complet (pilotage).
--   role_commercial   : commandes VALIDEE/LIVREE uniquement -- vue
--                       operationnelle, les annulations ne relevent pas
--                       du quotidien de l'equipe commerciale.

CREATE ROLE role_rh NOLOGIN;
CREATE ROLE role_finance NOLOGIN;
CREATE ROLE role_direction NOLOGIN;
CREATE ROLE role_commercial NOLOGIN;

GRANT USAGE ON SCHEMA marts TO role_rh, role_finance, role_direction, role_commercial;
GRANT SELECT ON marts.fait_ventes, marts.dim_client
    TO role_rh, role_finance, role_direction, role_commercial;

ALTER TABLE marts.fait_ventes ENABLE ROW LEVEL SECURITY;
ALTER TABLE marts.dim_client ENABLE ROW LEVEL SECURITY;

-- RH : zero ligne, sur les deux tables.
CREATE POLICY rh_aucun_acces ON marts.fait_ventes
    FOR SELECT TO role_rh USING (false);
CREATE POLICY rh_aucun_acces ON marts.dim_client
    FOR SELECT TO role_rh USING (false);

-- Finance/Direction : tout, y compris les annulations.
CREATE POLICY finance_direction_complet ON marts.fait_ventes
    FOR SELECT TO role_finance, role_direction USING (true);
CREATE POLICY finance_direction_complet_clients ON marts.dim_client
    FOR SELECT TO role_finance, role_direction USING (true);

-- Commercial : commandes actives uniquement (pas les annulees).
CREATE POLICY commercial_actives ON marts.fait_ventes
    FOR SELECT TO role_commercial USING (statut <> 'ANNULEE');
CREATE POLICY commercial_clients ON marts.dim_client
    FOR SELECT TO role_commercial USING (true);
