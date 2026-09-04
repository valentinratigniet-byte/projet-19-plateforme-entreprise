{#
  Regles de nettoyage documentees ici (le detail metier va dans
  regles-transformation.md du domaine) :
  - CMDDAT : deux formats coexistent dans le brut (derive constatee sur
    2 mois, cf. avant.md) -- YYYYMMDD tente en premier, DDMMYYYY en
    repli si l'annee n'est pas plausible.
  - STCMD : variantes d'orthographe regroupees par prefixe (VAL/LIV/ANN)
    plutot qu'une liste exhaustive de correspondances exactes.
  - PRIXUN/MTTHT : stockes en centimes (texte) dans le brut -> euros.
  - client_connu : commandes dont le CLICOD n'existe pas dans le fichier
    clients (FK partielle reelle du brut) -- gardees et flaguees, pas
    supprimees silencieusement.
#}

with source as (

    select * from {{ source('raw', 'ventes_commandes') }}

),

clients as (

    select clicod from {{ ref('stg_ventes_clients') }}

),

nettoye as (

    select
        trim(upper(s."CLICOD"))    as clicod,
        trim(s."CMDNUM")           as cmdnum,
        case
            when substring(s."CMDDAT" from 5 for 2)::int between 1 and 12
                 and substring(s."CMDDAT" from 1 for 4)::int between 2020 and 2035
                then to_date(s."CMDDAT", 'YYYYMMDD')
            when substring(s."CMDDAT" from 3 for 2)::int between 1 and 12
                then to_date(s."CMDDAT", 'DDMMYYYY')
            else null
        end                                                       as date_commande,
        (substring(s."CMDDAT" from 5 for 2)::int not between 1 and 12
         or substring(s."CMDDAT" from 1 for 4)::int not between 2020 and 2035)
                                                                    as date_format_derive,
        trim(s."ARTCOD")                                           as artcod,
        s."QTECMD"::int                                            as qte_commandee,
        (s."PRIXUN"::numeric) / 100                                as prix_unitaire_eur,
        (s."MTTHT"::numeric) / 100                                 as montant_ht_eur,
        case
            when upper(trim(s."STCMD")) like 'VAL%' then 'VALIDEE'
            when upper(trim(s."STCMD")) like 'LIV%' then 'LIVREE'
            when upper(trim(s."STCMD")) like 'ANN%' then 'ANNULEE'
            else 'INCONNU'
        end                                                        as statut,
        s._source_file,
        s._ingested_at

    from source s

),

avec_client_connu as (

    select
        n.*,
        c.clicod is not null as client_connu

    from nettoye n
    left join clients c on n.clicod = c.clicod

)

select * from avec_client_connu
