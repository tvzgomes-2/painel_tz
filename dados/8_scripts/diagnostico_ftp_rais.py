#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diagnostico_ftp_rais.py — só LISTA o que existe no FTP público do
PDET/Ministério do Trabalho, em vários níveis de pasta candidatos, pra
descobrirmos o caminho/nome real dos arquivos da RAIS 2022+ (o caminho
antigo documentado em cemin.wikidot.com/raisrm, /pdet/microdados/RAIS/
<ano>/<UF><ano>.7z, deu "550 arquivo não encontrado" pros 2 anos testados
— o Ministério deve ter reorganizado as pastas). Não baixa nada, só lista.

USO: python diagnostico_ftp_rais.py"""
import ftplib

HOST = "ftp.mtps.gov.br"

# candidatos de pasta a inspecionar — vamos ver qual existe de verdade
PASTAS_CANDIDATAS = [
    "/",
    "/pdet",
    "/pdet/microdados",
    "/pdet/microdados/RAIS",
    "/pdet/microdados/RAIS/2022",
    "/pdet/microdados/RAIS/2023",
    "/pdet/microdados/RAIS/2024",
    "/RAIS",
    "/microdados",
]


def main():
    ftp = ftplib.FTP(HOST, timeout=30)
    ftp.login()
    print(f"Conectado em {HOST}\n")

    for pasta in PASTAS_CANDIDATAS:
        print(f"=== {pasta} ===")
        try:
            itens = []
            ftp.retrlines(f"LIST {pasta}", itens.append)
            if not itens:
                print("  (vazio ou sem permissão)")
            for linha in itens[:40]:
                print(f"  {linha}")
            if len(itens) > 40:
                print(f"  ... (+{len(itens)-40} itens)")
        except ftplib.error_perm as e:
            print(f"  ⚠️ não existe / sem acesso: {e}")
        except Exception as e:
            print(f"  ⚠️ erro: {e}")
        print()

    ftp.quit()


if __name__ == "__main__":
    main()
