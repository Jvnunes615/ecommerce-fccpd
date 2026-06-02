# E-commerce em Microsserviços — FCCPD

Sistema de e-commerce mínimo composto por **4 microsserviços** (Produtos roda em
**2 réplicas**) coordenados por um **API Gateway**, com replicação de dados,
detecção de falha por **heartbeat** e autenticação via **JWT**.

```
                 Cliente (navegador / curl / Postman)
                              │
                   ┌──────────▼──────────┐
                   │   API Gateway :8080 │  ← ponto de entrada único + heartbeat
                   └─┬────────┬────────┬─┘
          ┌──────────┘        │        └──────────┐
   ┌──────▼──────┐   ┌────────▼────────┐   ┌──────▼──────┐
   │ Usuários    │   │ Produtos        │   │ Pedidos     │
   │   :5001     │   │ :5002  ⇄  :5012 │   │   :5003     │
   └─────────────┘   │ (primário/réplica)   └─────────────┘
                     └─────────────────┘
```

## Tecnologias
- **Backend:** Python 3 + Flask (1 dependência externa: `Flask`).
- **JWT e hash de senha:** biblioteca padrão do Python (`hmac`/`hashlib`,
  algoritmo HS256 + PBKDF2-HMAC-SHA256). Não há dependências nativas que exijam
  compilação, então roda em qualquer máquina com Python.
- **Comunicação entre serviços:** HTTP/REST (JSON), via `urllib`.
- **Frontend:** HTML + CSS + JavaScript puro (loja e dashboard de monitoramento),
  servidos pelo próprio Gateway.
- **Persistência:** um arquivo JSON por serviço (e um por réplica de Produtos).

---

## Como rodar

Existem **duas formas**. Escolha uma.

### Opção A — Localmente com Python (recomendada para correção rápida)

Pré-requisito: **Python 3.10+** instalado.

```bash
# 1. Entre na pasta do projeto
cd ecommerce

# 2. (Opcional) crie um ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Instale a dependência
pip install -r requirements.txt

# 4. Suba TODOS os serviços com um único comando
python scripts/start_all.py
```

Isso inicia, em processos separados:
`Usuários (5001)`, `Produtos primário (5002)`, `Produtos réplica (5012)`,
`Pedidos (5003)` e `Gateway (8080)`.

```bash
# 5. (Opcional, em outro terminal) popule dados de exemplo
python scripts/seed.py
```

Acesse no navegador: **http://localhost:8080** (loja) e
**http://localhost:8080/dashboard** (monitoramento).

> Encerrar: `Ctrl+C` no terminal do `start_all.py`.

### Opção B — Docker Compose

Pré-requisito: **Docker** e **Docker Compose**.

```bash
cd ecommerce
docker compose up --build
```

Acesse **http://localhost:8080**. Para popular dados:
`python scripts/seed.py` (a partir da máquina host) ou use a interface da loja.

---

## Usuário de exemplo (após `seed.py`)
- **Admin:** `admin@fccpd.com` / `admin123` (pode criar produtos)

---

## Endpoints (via Gateway, base `http://localhost:8080`)

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

```bash
# Registrar e logar
curl -X POST http://localhost:8080/users/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Joao","email":"joao@test.com","password":"123456"}'

TOKEN=$(curl -s -X POST http://localhost:8080/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@fccpd.com","password":"admin123"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

# Criar produto (admin)
curl -X POST http://localhost:8080/products \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Mouse","price":99.9,"stock":10}'

# Listar produtos
curl http://localhost:8080/products

# Criar pedido
curl -X POST http://localhost:8080/orders \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"productId":"<id-do-produto>","quantity":2}'
```

---

## Testando os requisitos

- **Replicação:** após criar um produto, verifique que ele aparece em
  `data/products_primary.json` **e** `data/products_replica.json`.
- **Heartbeat / tolerância a falhas:** derrube um serviço (ex.: feche o processo
  na porta 5003) e observe, em ~10s, o log do Gateway registrando
  `FALHA: servico "orders" ... INDISPONIVEL` e as requisições a `/orders`
  retornando **503**. Ao reiniciar o serviço, o Gateway loga `RECUPERACAO`.
- **JWT/segurança:** tente `POST /products` com um token de usuário comum →
  resposta **403**; sem token → **401**.

---

## Estrutura de pastas
```
ecommerce/
├── gateway/      → API Gateway + heartbeat + proxy
├── users/        → Serviço de Usuários
├── products/     → Serviço de Produtos (código único p/ as 2 réplicas)
├── orders/       → Serviço de Pedidos
├── common/       → módulos compartilhados (auth JWT, store JSON, http, config)
├── frontend/     → loja (index.html) e dashboard (dashboard.html) + assets
├── scripts/      → start_all.py (sobe tudo) e seed.py (dados de exemplo)
├── data/         → bases JSON (geradas em runtime)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env / .env.example
├── README_execucao.md
└── relatorio.pdf
```
