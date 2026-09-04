-- Roles RLS partages entre domaines (RH/Finance/Direction) -- crees une
-- fois au niveau entrepot, pas par domaine (concepts transverses). Les
-- roles operationnels specifiques a un domaine (ex. role_commercial pour
-- Ventes) sont crees par le domaine concerne.
CREATE ROLE role_rh NOLOGIN;
CREATE ROLE role_finance NOLOGIN;
CREATE ROLE role_direction NOLOGIN;
