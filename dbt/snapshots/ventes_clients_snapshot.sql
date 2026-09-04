{#
  SCD type 2 sur le fichier clients AS/400 (raw.ventes_clients, remplace
  a chaque run). Strategie "check" plutot que "timestamp" : l'AS/400 ne
  fournit pas de colonne de derniere modification fiable -- honnete de
  comparer les colonnes reelles plutot que de supposer une colonne qui
  n'existe pas.
#}
{% snapshot ventes_clients_snapshot %}

{#
  Colonnes brutes creees avec des identifiants cites (majuscules, cf.
  ingestion/adaptateurs/postgres_writer.py) -- il faut les citer ici aussi,
  sinon Postgres les cherche en minuscules et echoue "column does not exist".

  target_schema = raw_historise, pas raw : le role ingestion possede
  raw (lecture seule pour dbt_transform), dbt_transform possede tout ce
  qu'il derive -- snapshots inclus -- meme separation de privileges que
  le reste (cf. entrepot/init/01_schema_raw.sql).
#}
{{
    config(
        target_schema='raw_historise',
        unique_key='"CLICOD"',
        strategy='check',
        check_cols=['"CLINOM"', '"CLIVIL"', '"CLICP"'],
    )
}}

select * from {{ source('raw', 'ventes_clients') }}

{% endsnapshot %}
