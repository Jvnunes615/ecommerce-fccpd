# E-commerce em Microsserviços — FCCPD

Projeto da disciplina **Fundamentos de Computação Concorrente, Paralela e Distribuída (FCCPD)**.

Sistema de e-commerce mínimo composto por **4 microsserviços** (Produtos roda em
**2 réplicas**) coordenados por um **API Gateway**, com:

- Autenticação via **JWT** (HS256, implementado com a biblioteca padrão do Python)
- Replicação **síncrona (consistência forte)** entre 2 réplicas do Serviço de Produtos
- Detecção de falhas via **heartbeat** no API Gateway (log de falha/recuperação + 503)
- Comunicação interna em **HTTPS/TLS** (CA própria, certificados auto-assinados)
- Persistência em **SQLite**
- Frontend em HTML/CSS/JS puro (loja + dashboard de monitoramento)
- **Docker Compose** para subir toda a infraestrutura

## Arquitetura

Cliente (navegador / curl / Postman)
|
v
API Gateway :8080 (HTTPS)
- ponto de entrada unico
- heartbeat
|
+--------+--------+--------+
| | |
v v v
Usuarios :5001 Produtos Pedidos :5003
(HTTPS) :5002 <-> :5012
(primario/replica, HTTPS)
(HTTPS)

## Como executar

Instruções completas (Python local ou Docker Compose) estão em
[`README_execucao.md`](README_execucao.md).

```bash
# Forma rápida (Python local)
pip install -r requirements.txt
python scripts/start_all.py
```

Acesse **https://localhost:8080** (loja) e **https://localhost:8080/dashboard** (monitoramento).

## Relatório

O relatório técnico, respondendo às perguntas sobre comunicação, consistência,
tolerância a falhas, segurança JWT e limitações, está em
[`relatorio.pdf`](relatorio.pdf).

## Tecnologias

- Python 3 + Flask
- JWT (HS256) e hash de senha (PBKDF2-HMAC-SHA256) via biblioteca padrão
- SQLite
- HTTPS/TLS com CA própria
- HTML/CSS/JS puro
- Docker / Docker Compose

## Autor

João Victor Nunes


    
