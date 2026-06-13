# Imagem unica usada por todos os servicos. O comando especifico (qual app.py)
# e definido por cada servico no docker-compose.yml.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Gera os certificados TLS (CA + servidor com SAN para os nomes dos servicos
# do docker-compose) durante o build, ja que e a mesma imagem para todos.
RUN python scripts/generate_certs.py

# Porta padrao (sobrescrita por cada servico). Documentacao apenas.
EXPOSE 5001 5002 5003 5012 8080

CMD ["python", "gateway/app.py"]
