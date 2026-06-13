"""Gera os certificados TLS auto-assinados em certs/.

Requer openssl no PATH (disponivel no Git for Windows, macOS e Linux).
Execute uma vez antes de subir os servicos:
    python scripts/generate_certs.py

Os arquivos gerados (ca.crt, server.crt, server.key) sao usados por todos
os microsservicos para comunicacao HTTPS interna (mutual TLS via CA proprio).
"""
import os
import subprocess
import sys
import textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERTS = os.path.join(ROOT, "certs")


def run(cmd, **kw):
    result = subprocess.run(cmd, capture_output=True, **kw)
    if result.returncode != 0:
        print("ERRO:", result.stderr.decode(errors="replace"))
        sys.exit(1)


def main():
    os.makedirs(CERTS, exist_ok=True)

    ca_key = os.path.join(CERTS, "ca.key")
    ca_crt = os.path.join(CERTS, "ca.crt")
    srv_key = os.path.join(CERTS, "server.key")
    srv_csr = os.path.join(CERTS, "server.csr")
    srv_crt = os.path.join(CERTS, "server.crt")
    san_cfg = os.path.join(CERTS, "san.cnf")

    ca_cfg = os.path.join(CERTS, "ca.cnf")
    with open(ca_cfg, "w") as f:
        f.write(textwrap.dedent("""\
            [req]
            distinguished_name = req_dn
            prompt = no
            [req_dn]
            CN = FCCPD-CA
            O  = FCCPD
            C  = BR
            [v3_ca]
            subjectKeyIdentifier = hash
            authorityKeyIdentifier = keyid:always,issuer
            basicConstraints = critical,CA:true
            keyUsage = critical,digitalSignature,cRLSign,keyCertSign
        """))

    with open(san_cfg, "w") as f:
        f.write(textwrap.dedent("""\
            [req]
            distinguished_name = req_dn
            req_extensions = v3_server
            prompt = no
            [req_dn]
            CN = fccpd-services
            [v3_server]
            basicConstraints = CA:false
            keyUsage = critical,digitalSignature,keyEncipherment
            extendedKeyUsage = serverAuth
            subjectAltName = @alt_names
            [alt_names]
            DNS.1 = localhost
            DNS.2 = users
            DNS.3 = products-primario
            DNS.4 = products-replica
            DNS.5 = orders
            DNS.6 = gateway
            IP.1 = 127.0.0.1
        """))

    print("Gerando CA...")
    run(["openssl", "genrsa", "-out", ca_key, "2048"])
    run(["openssl", "req", "-new", "-x509", "-days", "3650",
         "-key", ca_key, "-out", ca_crt,
         "-config", ca_cfg, "-extensions", "v3_ca"])

    print("Gerando certificado do servidor...")
    run(["openssl", "genrsa", "-out", srv_key, "2048"])
    run(["openssl", "req", "-new", "-key", srv_key, "-out", srv_csr,
         "-config", san_cfg])
    run(["openssl", "x509", "-req", "-days", "3650",
         "-in", srv_csr, "-CA", ca_crt, "-CAkey", ca_key,
         "-CAcreateserial", "-out", srv_crt,
         "-extensions", "v3_server", "-extfile", san_cfg])

    print(f"Certificados gerados em {CERTS}/")
    for f in ["ca.crt", "server.crt", "server.key"]:
        path = os.path.join(CERTS, f)
        size = os.path.getsize(path)
        print(f"  {f}: {size} bytes")


if __name__ == "__main__":
    main()
