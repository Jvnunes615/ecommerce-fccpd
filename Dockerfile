# Imagem unica usada por todos os servicos. O comando especifico (qual app.py)
# e definido por cada servico no docker-compose.yml.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Porta padrao (sobrescrita por cada servico). Documentacao apenas.
EXPOSE 5001 5002 5003 5012 8080

CMD ["python", "gateway/app.py"]
