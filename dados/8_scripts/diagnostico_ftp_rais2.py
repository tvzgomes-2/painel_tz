#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diagnostico_ftp_rais2.py — 2ª rodada do diagnóstico: já sabemos que
/pdet/microdados/RAIS/<ano>/ existe e que em 2022 os arquivos são
RAIS_ESTAB_PUB.7z (nacional, único, ~91MB) + RAIS_VINC_PUB_<REGIAO>.7z (6
arquivos por região, não por UF). Erro em 2023/2024 na 1ª rodada foi só de
ACENTUAÇÃO na listagem (ftplib decodifica em utf-8 por padrão; o servidor
usa latin-1/cp1252) — aqui força a conexão em latin-1 antes de listar.

USO: python diagnostico_ftp_rais2.py"""
import ftplib

HOST = "ftp.mtps.gov.br"
PASTAS = [
    "/pdet/microdados/RAIS/2022",
    "/pdet/microdados/RAIS/2023",
    "/pdet/microdados/RAIS/2023 Parcial",
    "/pdet/microdados/RAIS/2024",
    "/pdet/microdados/RAIS",  # lista de novo, completa, sem cortar em 40
]


def main():
    ftp = ftplib.FTP(HOST, timeout=30)
    ftp.encoding = "latin-1"  # servidor usa latin-1/cp1252, não utf-8
    ftp.login()
    print(f"Conectado em {HOST} (encoding latin-1)\n")

    for pasta in PASTAS:
        print(f"=== {pasta} ===")
        try:
            itens = []
            ftp.retrlines(f"LIST {pasta}", itens.append)
            if not itens:
                print("  (vazio ou sem permissão)")
            for linha in itens:
                print(f"  {linha}")
        except ftplib.error_perm as e:
            print(f"  ⚠️ não existe / sem acesso: {e}")
        except Exception as e:
            print(f"  ⚠️ erro: {e}")
        print()

    ftp.quit()


if __name__ == "__main__":
    main()
