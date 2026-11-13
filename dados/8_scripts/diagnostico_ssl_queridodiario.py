#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diagnostico_ssl_queridodiario.py

O SECLEVEL=1 não resolveu o SSLV3_ALERT_HANDSHAKE_FAILURE contra
api.queridodiario.ok.org.br. Este script testa várias hipóteses, uma de
cada vez, e imprime qual (se alguma) funciona — para eu ajustar o script
principal com base no que realmente funciona aqui, em vez de eu adivinhar
de novo às cegas (não consigo testar essa URL do meu lado; a rede daqui
bloqueia o domínio antes mesmo de tentar).

Uso:
    conda activate <seu_ambiente>
    cd caminho\\para\\_meta\\scripts
    python diagnostico_ssl_queridodiario.py

Autor: Thiago Von Zeidler Gomes
Orientadora: Prof.ª Silvana Zioni
"""
import ssl
import subprocess
import sys

URL = "https://api.queridodiario.ok.org.br/gazettes?querystring=teste&size=1"


def secao(titulo):
    print(f"\n=== {titulo} ===")


def tentar_requests(nome, ctx_factory):
    import requests
    from requests.adapters import HTTPAdapter

    class Adapter(HTTPAdapter):
        def init_poolmanager(self, *a, **kw):
            kw["ssl_context"] = ctx_factory()
            return super().init_poolmanager(*a, **kw)

    s = requests.Session()
    if ctx_factory is not None:
        s.mount("https://", Adapter())
    try:
        r = s.get(URL, timeout=15)
        print(f"  ✅ {nome}: status HTTP {r.status_code}")
        print(f"     trecho da resposta: {r.text[:300]}")
        return True
    except Exception as e:
        print(f"  🔴 {nome}: {type(e).__name__}: {e}")
        return False


def main():
    secao("Ambiente")
    print(f"  Python: {sys.version}")
    print(f"  ssl.OPENSSL_VERSION: {ssl.OPENSSL_VERSION}")
    try:
        import requests
        print(f"  requests: {requests.__version__}")
    except Exception as e:
        print(f"  requests não importou: {e}")
    try:
        import urllib3
        print(f"  urllib3: {urllib3.__version__}")
    except Exception as e:
        print(f"  urllib3 não importou: {e}")

    secao("Teste 1 — requests, contexto padrão (repete o erro original)")
    tentar_requests("padrão", None)

    secao("Teste 2 — requests, SECLEVEL=1 (o que já tentamos e falhou)")
    def ctx_seclevel1():
        c = ssl.create_default_context()
        c.set_ciphers("DEFAULT@SECLEVEL=1")
        return c
    tentar_requests("SECLEVEL=1", ctx_seclevel1)

    secao("Teste 3 — requests, SECLEVEL=0 (permissivo ao máximo em cifras)")
    def ctx_seclevel0():
        c = ssl.create_default_context()
        c.set_ciphers("ALL:@SECLEVEL=0")
        return c
    tentar_requests("SECLEVEL=0", ctx_seclevel0)

    secao("Teste 4 — requests, forçando TLS 1.2 como mínimo e máximo")
    def ctx_tls12():
        c = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        c.minimum_version = ssl.TLSVersion.TLSv1_2
        c.maximum_version = ssl.TLSVersion.TLSv1_2
        c.set_ciphers("ALL:@SECLEVEL=0")
        return c
    tentar_requests("TLS 1.2 fixo", ctx_tls12)

    secao("Teste 5 — requests, sem verificar certificado (só para ISOLAR a causa; "
          "NÃO é para uso normal)")
    def ctx_sem_verificar():
        c = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        c.check_hostname = False
        c.verify_mode = ssl.CERT_NONE
        c.set_ciphers("ALL:@SECLEVEL=0")
        return c
    tentar_requests("sem verificação de certificado", ctx_sem_verificar)

    secao("Teste 6 — curl do sistema (fora do Python, para ver se é um "
          "problema específico do OpenSSL do Python ou é a rede/máquina toda)")
    try:
        r = subprocess.run(
            ["curl", "-sS", "-o", "NUL", "-w", "HTTP_STATUS:%{http_code}", URL],
            capture_output=True, text=True, timeout=20,
        )
        print(f"  stdout: {r.stdout}")
        if r.stderr:
            print(f"  stderr: {r.stderr[:500]}")
    except FileNotFoundError:
        print("  curl não encontrado neste sistema (tudo bem, é só mais um dado).")
    except Exception as e:
        print(f"  🔴 curl: {type(e).__name__}: {e}")

    print("\n=== Fim do diagnóstico — me manda esta saída inteira ===")


if __name__ == "__main__":
    main()
