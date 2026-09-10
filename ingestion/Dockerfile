FROM python:3.12-slim
WORKDIR /app
# libfbclient2 -- firebird-driver est un wrapper autour de la bibliotheque
# cliente native Firebird, pas un driver pur Python (contrairement a
# pymssql/PyMySQL/psycopg2-binary, deja auto-suffisants) -- sans elle,
# "The location of Firebird Client Library could not be determined."
RUN apt-get update && apt-get install -y --no-install-recommends libfbclient2 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY adaptateurs/ ./adaptateurs/
