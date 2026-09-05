{#
  SCD type 2 sur les contacts MySQL (raw.marketing_contacts, remplace a
  chaque run) -- meme pattern que Ventes/Finance.
#}
{% snapshot marketing_contacts_snapshot %}

{{
    config(
        target_schema='raw_historise',
        unique_key='id',
        strategy='check',
        check_cols=['email', 'prenom', 'nom'],
    )
}}

select * from {{ source('raw', 'marketing_contacts') }}

{% endsnapshot %}
