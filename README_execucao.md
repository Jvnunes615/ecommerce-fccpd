# E-commerce em Microsserviços — FCCPD

Sistema de e-commerce mínimo composto por **4 microsserviços** (Produtos roda em
**2 réplicas**) coordenados por um **API Gateway**, com replicação de dados,
detecção de falha por **heartbeat**, autenticação via **JWT** e comunicação
interna inteiramente em **HTTPS/TLS** (CA própria).

```
                 Cliente (navegador / curl / Postman)
                              │
                   ┌──────────▼──────────┐
                   │   API Gateway :8080 │  ← ponto de entrada único + heartbeat
                   │       (HTTPS)       │
                   └─┬────────┬────────┬─┘
          ┌──────────┘        │        └──────────┐
   ┌──────▼──────┐   ┌────────▼────────┐   ┌──────▼──────┐
   │ Usuários    │   │ Produtos        │   │ Pedidos     │
   │   :5001     │   │ :5002  ⇄  :5012 │   │   :5003     │
   │  (HTTPS)    │   │ (primário/réplica)  │  (HTTPS)    │
   └─────────────┘   │     (HTTPS)     │   └─────────────┘
                      └─────────────────┘
```

## Tecnologias
- **Backend:** Python 3 + Flask (1 dependência externa: `Flask`).
- **JWT e hash de senha:** biblioteca padrão do Python (`hmac`/`hashlib`,
  algoritmo HS256 + PBKDF2-HMAC-SHA256). Não há dependências nativas que exijam
  compilação, então roda em qualquer máquina com Python.
- **Comunicação entre serviços:** HTTPS/REST (JSON), via `urllib` com
  verificação de certificado contra uma CA própria.
- **TLS:** certificados auto-assinados gerados por `scripts/generate_certs.py`
  (requer `openssl` no PATH). Gerados automaticamente na primeira execução.
- **Frontend:** HTML + CSS + JavaScript puro (loja e dashboard de monitoramento),
  servidos pelo próprio Gateway.
- **Persistência:** SQLite (um arquivo `.db` por serviço, e um por réplica de
  Produtos), via módulo `sqlite3` da biblioteca padrão.

---

## Como rodar

Existem **duas formas**. Escolha uma.

### Opção A: Localmente com Python (recomendada para correção rápida)

Pré-requisito: **Python 3.10+** e **openssl** no PATH (já vem com Git for
Windows, macOS e a maioria das distros Linux).

```bash
1. Entre na pasta do projeto
cd ecommerce

2. (Opcional) crie um ambiente virtual
python -m venv .venv
Windows:
.venv\Scripts\activate
Linux/Mac:
source .venv/bin/activate

3. Instale a dependência
pip install -r requirements.txt

4. Suba TODOS os serviços com um único comando
python scripts/start_all.py
```

Na primeira execução, o script gera automaticamente os certificados TLS em
`certs/` (chamando `scripts/generate_certs.py`). Em seguida inicia, em
processos separados:
`Usuários (5001)`, `Produtos primário (5002)`, `Produtos réplica (5012)`,
`Pedidos (5003)` e `Gateway (8080)` — todos servindo HTTPS.

```bash
# 5. (Opcional, em outro terminal) popule dados de exemplo
python scripts/seed.py
```

Acesse no navegador: **https://localhost:8080** (loja) e
**https://localhost:8080/dashboard** (monitoramento).

> O navegador vai exibir um aviso de certificado auto-assinado (esperado em
> ambiente de desenvolvimento). Clique em "Avançado" → "Continuar para
> localhost".

> Encerrar: `Ctrl+C` no terminal do `start_all.py`.

> Se preferir não usar TLS, defina `USE_TLS=false` no `.env` antes de subir —
> os serviços passam a usar HTTP simples.

### Opção B: Docker Compose

Pré-requisito: **Docker** e **Docker Compose**.

```bash
cd ecommerce
docker compose up --build
```

Os certificados TLS são gerados durante o build da imagem (o Dockerfile
instala `openssl` e executa `generate_certs.py`), com SAN cobrindo os nomes
dos serviços do compose (`users`, `products-primario`, `products-replica`,
`orders`, `gateway`).

Acesse **https://localhost:8080**. Para popular dados:
`python scripts/seed.py` (a partir da máquina host) ou use a interface da loja.

---

## Usuário de exemplo (após `seed.py`)
- **Admin:** `admin@fccpd.com` / `admin123` (pode criar produtos)

---

## Endpoints (via Gateway, base `https://localhost:8080`)

### Usuários
| Método | Rota | Auth | Descrição |
|---|---|---|---|
| POST | `/users/register` | — | Cria usuário (`name`, `email`, `password`, `role?`) |
| POST | `/users/login` | — | Autentica e retorna JWT |
| GET | `/users/<id>` | JWT | Dados do usuário |

### Produtos
| Método | Rota | Auth | Descrição |
|---|---|---|---|
| GET | `/products` | — | Lista produtos (leitura round-robin entre réplicas) |
| GET | `/products/<id>` | — | Detalha um produto |
| POST | `/products` | JWT admin | Cria produto (replicado nas 2 réplicas) |

### Pedidos
| Método | Rota | Auth | Descrição |
|---|---|---|---|
| POST | `/orders` | JWT | Cria pedido (`productId`, `quantity?`) |
| GET | `/orders/<userId>` | JWT | Lista pedidos do usuário |

### Monitoramento / Health
| Método | Rota | Descrição |
|---|---|---|
| GET | `/status` | Estado de saúde de todos os serviços (JSON) |
| GET | `/health` | Disponível em **cada** microsserviço: `{"status":"ok"}` |

---

## Exemplos com `curl`

> Como os certificados são auto-assinados, use `curl -k` (ignora verificação
> de CA) ou aponte `--cacert certs/ca.crt`.

```bash
# Registrar e logar
curl -k -X POST https://localhost:8080/users/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Joao","email":"joao@test.com","password":"123456"}'

TOKEN=$(curl -sk -X POST https://localhost:8080/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@fccpd.com","password":"admin123"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

# Criar produto (admin)
curl -k -X POST https://localhost:8080/products \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Mouse","price":99.9,"stock":10}'

# Listar produtos
curl -k https://localhost:8080/products

# Criar pedido
curl -k -X POST https://localhost:8080/orders \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"productId":"<id-do-produto>","quantity":2}'
```

---

## Testando os requisitos

- **Replicação:** após criar um produto, verifique que ele aparece no
  `data/products_primary.db` **e** `data/products_replica.db` (tabela `items`).
- **Heartbeat / tolerância a falhas:** derrube um serviço (ex.: feche o processo
  na porta 5003) e observe, em ~10s, o log do Gateway registrando
  `FALHA: servico "orders" ... INDISPONIVEL` e as requisições a `/orders`
  retornando **503**. Ao reiniciar o serviço, o Gateway loga `RECUPERACAO`.
- **JWT/segurança:** tente `POST /products` com um token de usuário comum →
  resposta **403**; sem token → **401**.
- **TLS:** todas as URLs internas (`.env` / `docker-compose.yml`) usam
  `https://`; a conexão é validada contra `certs/ca.crt` (sem desabilitar
  verificação de hostname).

---

## Estrutura de pastas
```
ecommerce/
├── gateway/      → API Gateway + heartbeat + proxy
├── users/        → Serviço de Usuários
├── products/     → Serviço de Produtos (código único p/ as 2 réplicas)
├── orders/       → Serviço de Pedidos
├── common/       → módulos compartilhados (auth JWT, store SQLite, http TLS, config, tls)
├── frontend/     → loja (index.html) e dashboard (dashboard.html) + assets
├── scripts/      → start_all.py, seed.py, generate_certs.py, generate_report.py
├── data/         → bases SQLite (geradas em runtime)
├── certs/        → certificados TLS (gerados em runtime / build, não versionados)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env / .env.example
├── README_execucao.md
└── relatorio.pdf
```
