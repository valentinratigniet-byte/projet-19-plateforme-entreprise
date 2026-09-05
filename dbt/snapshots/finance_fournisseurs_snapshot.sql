{#
  SCD type 2 sur les fournisseurs SQL Server (raw.finance_fournisseurs,
  remplace a chaque run) -- meme pattern que ventes_clients_snapshot.
  Colonnes citees en casse mixte (pymssql renvoie la casse SQL Server
  d'origine : "FournisseurID", pas "fournisseurid").
#}
{% snapshot finance_fournisseurs_snapshot %}

{{
    config(
        target_schema='raw_historise',
        unique_key='"FournisseurID"',
        strategy='check',
        check_cols=['"RaisonSociale"', '"SIREN"', '"IBAN"'],
    )
}}

select * from {{ source('raw', 'finance_fournisseurs') }}

{% endsnapshot %}
