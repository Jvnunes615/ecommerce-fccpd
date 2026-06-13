"""Gera o relatorio.pdf a partir do conteudo abaixo (usa fpdf2, Python puro)."""
import os
from fpdf import FPDF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "relatorio.pdf")

PRIMARY = (40, 70, 160)
DARK = (30, 30, 30)
GRAY = (90, 90, 90)


class Report(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 6, "E-commerce em Microsservicos | FCCPD", align="R")
        self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 6, f"Pagina {self.page_no()}", align="C")


def title(pdf, text):
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*PRIMARY)
    pdf.multi_cell(0, 8, text)
    pdf.ln(1)


def subtitle(pdf, text):
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*GRAY)
    pdf.multi_cell(0, 5, text)
    pdf.ln(3)


def question(pdf, num, text):
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*PRIMARY)
    pdf.multi_cell(0, 6, f"{num}. {text}")
    pdf.ln(0.5)


def para(pdf, text):
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(*DARK)
    pdf.multi_cell(0, 5.2, text)
    pdf.ln(1.5)


def bullet(pdf, text):
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(*DARK)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5.2, f"-  {text}")
    pdf.ln(0.5)


def build():
    pdf = Report(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(18, 16, 18)

    title(pdf, "Relatorio: Sistema de E-commerce em Microsservicos")
    subtitle(pdf, "Disciplina: Fundamentos de Computacao Concorrente, Paralela e Distribuida (FCCPD)  |  "
                  "Arquitetura: API Gateway + Usuarios + Produtos (2 replicas) + Pedidos  |  "
                  "Stack: Python/Flask, comunicacao REST/HTTPS, JWT (HS256), SQLite, frontend HTML/CSS.")

    question(pdf, 1, "Como a comunicacao entre os microsservicos foi implementada?")
    para(pdf, "A comunicacao e feita via HTTPS/REST com payloads em JSON. Todos os servicos usam "
              "TLS com certificados auto-assinados emitidos por uma CA propria (generate_certs.py), "
              "de forma que cada chamada interna e criptografada e o certificado e verificado contra "
              "a CA local, sem desabilitar a verificacao de hostname. O API Gateway e o ponto de "
              "entrada unico: recebe requisicoes do cliente e as repassa (proxy) ao microsservico "
              "responsavel, preservando metodo, corpo e cabecalho Authorization (JWT). "
              "Internamente os servicos tambem conversam por HTTPS/REST: o Servico de Pedidos "
              "consulta o Servico de Produtos (GET /products/<id>) para validar o item antes de "
              "gravar, e a replica primaria de Produtos chama a replica par (POST /internal/replicate) "
              "para propagar escritas. Optou-se por REST por ser simples, sem dependencias externas "
              "alem do Flask; gRPC ou filas (RabbitMQ/Kafka) seriam alternativas para maior "
              "desempenho ou desacoplamento assincrono.")

    question(pdf, 2, "Qual estrategia de consistencia foi adotada na replicacao? Forte ou eventual? Por que?")
    para(pdf, "Foi adotada consistencia FORTE (replicacao sincrona). Quando um produto e criado, a "
              "replica primaria grava no seu banco SQLite local e so confirma sucesso (HTTP 201) ao "
              "cliente apos a replica par tambem confirmar a gravacao. Se a propagacao para a par "
              "falhar (rede ou servico fora), a escrita local e desfeita via rollback de transacao "
              "e o cliente recebe 503: a operacao e atomica (grava nas duas ou em nenhuma). A "
              "leitura e distribuida por round-robin entre as duas replicas. A escolha pela "
              "consistencia forte garante que qualquer replica lida devolve sempre o mesmo conjunto "
              "de produtos, evitando o cliente ver um catalogo divergente a cada leitura. O custo "
              "e menor disponibilidade de escrita: se uma replica estiver fora, nao se aceita nova "
              "escrita. Consistencia eventual traria maior disponibilidade, mas permitiria leituras "
              "temporariamente divergentes, o que e indesejavel para um catalogo de produtos.")

    question(pdf, 3, "O que acontece se o Servico de Pedidos cair? O restante continua funcionando?")
    para(pdf, "Sim. Como os microsservicos sao independentes e tem bancos SQLite separados, a queda "
              "do Servico de Pedidos NAO afeta Usuarios nem Produtos: o cliente continua podendo "
              "registrar-se, fazer login e navegar/criar produtos normalmente. O heartbeat do Gateway "
              "detecta a falha em ate ~10 segundos (2 verificacoes sem resposta no intervalo de 5s), "
              "registra a ocorrencia em log com timestamp e passa a responder 503 (Service Unavailable) "
              "apenas para as rotas /orders, deixando claro ao cliente qual recurso esta indisponivel. "
              "Quando o servico volta, o heartbeat registra a recuperacao e o roteamento e normalizado "
              "automaticamente. Isso foi validado em teste: ao derrubar a porta 5003, o Gateway logou "
              "FALHA e retornou 503; ao reiniciar, logou RECUPERACAO.")

    question(pdf, 4, "Como o JWT garante que um usuario comum nao consiga criar produtos?")
    para(pdf, "No login, o Servico de Usuarios gera um token JWT assinado com uma chave secreta "
              "(HS256 via hmac da stdlib Python, sem dependencia externa) contendo userId, email, "
              "role (user ou admin) e exp (expiracao). O endpoint POST /products e protegido pelo "
              "middleware require_admin, que: (a) extrai e valida a assinatura do token com a mesma "
              "chave secreta: se o token foi adulterado, a assinatura nao confere e a requisicao e "
              "rejeitada com 401; (b) verifica se nao expirou; e (c) exige que o campo role seja "
              "exatamente 'admin', retornando 403 caso contrario. Como o role esta dentro do payload "
              "assinado, um usuario comum nao consegue forja-lo: alterar o role invalidaria a "
              "assinatura. Assim, mesmo possuindo um token valido de usuario, ele recebe 403 ao "
              "tentar criar produtos, comportamento confirmado em teste manual.")

    question(pdf, 5, "Quais limitacoes a implementacao possui em relacao a um sistema real de producao?")
    bullet(pdf, "Servidor de desenvolvimento do Flask (Werkzeug), nao um WSGI de producao "
                "(gunicorn/uvicorn) atras de um balanceador de carga real.")
    bullet(pdf, "Replicacao apenas entre 2 nos, sem eleicao de lider, sem reconciliacao automatica "
                "apos particao de rede; quando uma replica esta fora, escritas falham.")
    bullet(pdf, "Certificados TLS auto-assinados por CA propria: adequados para desenvolvimento e "
                "comunicacao interna, mas em producao usaria-se certificados emitidos por uma CA "
                "publica (ex: Let's Encrypt) ou um servico de gestao de certificados (Vault, AWS ACM).")
    bullet(pdf, "Chave JWT e segredo de replicacao em variaveis de ambiente; em producao usar-se-ia "
                "um cofre de segredos (HashiCorp Vault, AWS Secrets Manager).")
    bullet(pdf, "Sem refresh token, revogacao de token, rate limiting, observabilidade distribuida "
                "(metricas/tracing com Prometheus/Jaeger) nem circuit breaker robusto (Hystrix/Resilience4j).")
    bullet(pdf, "Heartbeat simples com estado em memoria do Gateway, sem persistencia nem alta "
                "disponibilidade do proprio Gateway, que e um ponto unico de falha (SPOF).")
    bullet(pdf, "SQLite e adequado para este escopo educacional, mas nao escala horizontalmente; em "
                "producao usaria-se PostgreSQL/MySQL com replicas gerenciadas.")
    pdf.ln(2)
    para(pdf, "Apesar dessas limitacoes, o projeto cumpre os objetivos didaticos: decomposicao em "
              "microsservicos independentes, persistencia em SQLite, replicacao com consistencia forte, "
              "deteccao de falha por heartbeat, seguranca com JWT e comunicacao interna via HTTPS/TLS "
              "com CA propria (item opcional implementado).")

    pdf.output(OUT)
    print("Gerado:", OUT)


if __name__ == "__main__":
    build()
