#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baixa os PDFs da biblioteca da ANTP listados num CSV de triagem (formato
`expressoes;titulo;grupo;categoria;link;descricao;prioridade;nota_triagem`,
como o `desoneracao_triagem_2026-09-12.csv`) — genérico o bastante para
servir a qualquer lote de candidatos raspado por `rsl2_antp_biblioteca_scraper.py`
mais uma coluna `prioridade` (alta/duvidosa/nao_classificada, ou o que o
autor tiver decidido).

POR QUE ESTE SCRIPT RODA NA SUA MÁQUINA, NÃO NA NUVEM
------------------------------------------------------
Os domínios da ANTP (antigo.antp.org.br e antp.org.br) estão fora da lista
de domínios liberados no proxy de rede da sessão na nuvem — toda tentativa
de acessá-los de lá falha com "Host not in allowlist" ou "connect_rejected".
Isso não afeta a sua máquina: o scraper `rsl2_antp_biblioteca_scraper.py`
já rodou daqui sem problema. Este script segue o mesmo princípio.

USO
---
    # 1) sempre primeiro — só mostra o que seria baixado, não baixa nada:
    python baixar_pdfs_antp_por_csv.py --csv "...\\desoneracao_triagem_2026-09-12.csv" \\
        --dest "...\\pasta_destino" --prioridade alta --so-listar

    # 2) depois de conferir a lista, baixar de fato:
    python baixar_pdfs_antp_por_csv.py --csv "...\\desoneracao_triagem_2026-09-12.csv" \\
        --dest "...\\pasta_destino" --prioridade alta

    # baixar duas prioridades de uma vez:
    python baixar_pdfs_antp_por_csv.py --csv "..." --dest "..." --prioridade alta duvidosa

Cada PDF é salvo como "<indice>_<grupo-categoria-sanitizados>_<titulo-sanitizado>.pdf"
(nomes previsíveis e sem colisão, já que o nome original no servidor da ANTP
é um GUID sem significado). Ao final, grava um manifesto CSV em --dest
(mesmo padrão `;`, sem BOM, LF) com o que foi baixado, tamanho e status —
NADA aqui decide sobre entrada no corpus: o manifesto é só de download,
a leitura e a decisão de fichar continuam manuais.
"""

import argparse
import csv
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request

USER_AGENT = "Mozilla/5.0 (compatible; RSL-PGT092-research-script/1.0; +pesquisa academica UFABC)"
MAX_TENTATIVAS = 4
SLEEP_PADRAO = 1.5  # segundos entre downloads - ser gentil com o servidor da ANTP


def sanitizar(texto, tamanho_max=60):
    if not texto:
        return "sememnome"
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    limpo = re.sub(r"[^a-zA-Z0-9]+", "-", sem_acento).strip("-").lower()
    return limpo[:tamanho_max] or "sememnome"


def nome_arquivo(indice, row):
    grupo_cat = "-".join(p for p in (row.get("grupo", ""), row.get("categoria", "")) if p)
    return f"{indice:02d}_{sanitizar(grupo_cat, 30)}_{sanitizar(row.get('titulo', ''), 50)}.pdf"


def baixar_um(url, destino, sleep_entre_tentativas=2.0):
    """Baixa um PDF com retries simples (sem resume por byte - os arquivos
    da ANTP costumam ser pequenos o bastante para não precisar disso)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ultimo_erro = None
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                dados = resp.read()
            if not dados:
                raise RuntimeError("resposta vazia")
            tmp = destino + ".part"
            with open(tmp, "wb") as f:
                f.write(dados)
            os.replace(tmp, destino)
            return len(dados), None
        except Exception as e:
            ultimo_erro = e
            if tentativa < MAX_TENTATIVAS:
                print(f"    [tentativa {tentativa}/{MAX_TENTATIVAS}] falhou ({e}) - "
                      f"aguardando {sleep_entre_tentativas:.0f}s...")
                time.sleep(sleep_entre_tentativas)
                sleep_entre_tentativas = min(20, sleep_entre_tentativas * 2)
    return 0, ultimo_erro


def gravar_csv_validado(caminho, linhas, campos):
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=campos, delimiter=";", lineterminator="\n")
    w.writeheader()
    w.writerows(linhas)
    texto = buf.getvalue()
    checagem = list(csv.reader(io.StringIO(texto), delimiter=";"))
    tamanhos = {len(r) for r in checagem}
    assert len(tamanhos) == 1, f"CSV desalinhado: tamanhos de linha {tamanhos}"
    assert len(checagem) == len(linhas) + 1, "numero de linhas nao bate apos reparse"
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        f.write(texto)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True, help="CSV de triagem (com coluna 'prioridade' e 'link')")
    ap.add_argument("--dest", required=True, help="pasta onde os PDFs (e o manifesto) sao salvos")
    ap.add_argument("--prioridade", nargs="+", default=["alta"],
                     help="valor(es) da coluna 'prioridade' a baixar (default: alta)")
    ap.add_argument("--coluna-prioridade", default="prioridade", help="nome da coluna de prioridade (default: prioridade)")
    ap.add_argument("--coluna-link", default="link", help="nome da coluna de URL (default: link)")
    ap.add_argument("--so-listar", action="store_true", help="so mostra o que seria baixado, nao baixa nada")
    ap.add_argument("--forcar", action="store_true", help="baixa de novo mesmo que o arquivo ja exista")
    ap.add_argument("--sleep", type=float, default=SLEEP_PADRAO, help=f"segundos entre downloads (default {SLEEP_PADRAO})")
    args = ap.parse_args()

    with open(args.csv, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))

    if not linhas:
        sys.exit(f"ERRO: {args.csv} nao tem nenhuma linha.")
    if args.coluna_prioridade not in linhas[0]:
        sys.exit(f"ERRO: coluna '{args.coluna_prioridade}' nao existe no CSV. "
                  f"Colunas disponiveis: {list(linhas[0].keys())}")

    alvo = [(i, r) for i, r in enumerate(linhas) if r.get(args.coluna_prioridade) in args.prioridade]

    print(f"[baixar_pdfs] {len(alvo)} de {len(linhas)} linha(s) selecionada(s) "
          f"(prioridade em {args.prioridade}):\n")
    for i, r in alvo:
        print(f"  [{i:02d}] {r.get('titulo','')!r} — {r.get('grupo','')}/{r.get('categoria','')}")
        print(f"       {r.get(args.coluna_link, '')}")

    if args.so_listar:
        print("\n--so-listar: nada foi baixado. Rode de novo sem essa flag para baixar de fato.")
        return

    os.makedirs(args.dest, exist_ok=True)
    manifesto = []
    for i, r in alvo:
        url = (r.get(args.coluna_link) or "").strip()
        arquivo = nome_arquivo(i, r)
        destino = os.path.join(args.dest, arquivo)
        registro = {
            "indice": i, "titulo": r.get("titulo", ""), "grupo": r.get("grupo", ""),
            "categoria": r.get("categoria", ""), "prioridade": r.get(args.coluna_prioridade, ""),
            "link": url, "arquivo_local": arquivo, "tamanho_bytes": "", "status": "",
        }
        if not url:
            print(f"\n[{i:02d}] SEM LINK — pulando ({r.get('titulo','')!r})")
            registro["status"] = "sem_link"
            manifesto.append(registro)
            continue
        if not args.forcar and os.path.exists(destino) and os.path.getsize(destino) > 0:
            print(f"\n[{i:02d}] ja existe ({os.path.getsize(destino)/1e3:.0f} KB) - pulando "
                  f"(use --forcar para baixar de novo)")
            registro["tamanho_bytes"] = os.path.getsize(destino)
            registro["status"] = "ja_existia"
            manifesto.append(registro)
            continue

        print(f"\n[{i:02d}] baixando: {r.get('titulo','')!r}")
        print(f"     {url}")
        tamanho, erro = baixar_um(url, destino)
        if erro:
            print(f"     FALHOU apos {MAX_TENTATIVAS} tentativas: {erro}")
            registro["status"] = f"falhou: {erro}"
        else:
            print(f"     OK — {tamanho/1e3:.0f} KB salvos em {destino}")
            registro["tamanho_bytes"] = tamanho
            registro["status"] = "baixado"
        manifesto.append(registro)
        time.sleep(args.sleep)

    caminho_manifesto = os.path.join(
        args.dest, f"manifesto_downloads_{time.strftime('%Y-%m-%d_%H%M')}.csv")
    campos = ["indice", "titulo", "grupo", "categoria", "prioridade", "link", "arquivo_local",
              "tamanho_bytes", "status"]
    gravar_csv_validado(caminho_manifesto, manifesto, campos)
    print(f"\n[baixar_pdfs] manifesto gravado em {caminho_manifesto}")

    falhas = [m for m in manifesto if m["status"].startswith("falhou")]
    if falhas:
        print(f"\n[aviso] {len(falhas)} download(s) falharam - rode de novo (sem --forcar) "
              f"para tentar so os que faltam, ja que os que deram certo serao pulados.")


if __name__ == "__main__":
    main()
