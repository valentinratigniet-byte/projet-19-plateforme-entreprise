# Adaptateurs d'ingestion

Un adaptateur par TYPE de source, pas par domaine (doctrine du cadrage,
[issue #2](https://github.com/valentinratigniet-byte/valentinratigniet-byte/issues/2)) :

- `adaptateurs/fichier_plat.py` — fichier à largeur fixe (AS/400).
- `adaptateurs/excel.py` — fichier Excel (`data_only=False`, garde les
  formules cassées visibles au lieu de les faire disparaître).
- `adaptateurs/postgres_writer.py` — écriture générique dans `raw`
  (colonnes en TEXT, `_source_file`/`_ingested_at` pour la traçabilité,
  noms de colonnes sanitisés pour SQL sans toucher aux valeurs).

Chaque domaine a son propre script d'orchestration
(`domaines/<domaine>/ingestion.py`) qui importe ces adaptateurs et
décide : quel spec, quelle table `raw`, remplacement ou ajout.

## Exécution

Conteneurisé (`Dockerfile`, image `projet19-ingestion`) — le host du VPS
n'a pas les libs nécessaires (psycopg2, openpyxl) et on ne les installe
pas au niveau système.

```bash
docker build -t projet19-ingestion ingestion/
docker run --rm \
  --network entrepot_default \
  -v /opt/projet19/domaines/<domaine>:/domain \
  -e PYTHONPATH=/app \
  -e PGHOST=projet19-postgres -e PGPORT=5432 -e PGDATABASE=projet19 \
  -e PGUSER=ingestion -e PGPASSWORD=*** \
  -w /domain \
  projet19-ingestion python ingestion.py
```

À orchestrer via le workflow n8n indispensable du domaine (à venir).
