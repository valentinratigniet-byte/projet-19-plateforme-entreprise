{#
  Par defaut dbt concatene le schema du profil ("raw") avec le schema
  custom du modele ("staging"/"marts"), donnant "raw_staging"/"raw_marts"
  -- confus par rapport au cadrage (issue #2) qui documente juste
  "staging"/"marts". Override standard pour utiliser le schema custom tel
  quel.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
