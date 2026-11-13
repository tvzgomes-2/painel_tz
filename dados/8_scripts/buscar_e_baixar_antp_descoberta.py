#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Busca e baixa os PDFs dos itens da Frente C marcados `baixar=1` num CSV de
triagem (formato `id;secao;edicao;data;titulo;autor;baixar;motivo;url_candidato`,
como `RSL2_frenteC_30_semlink_triagem_2026-09-12.csv`).

POR QUE ESTE SCRIPT RODA NA SUA MÁQUINA, NÃO NA NUVEM
------------------------------------------------------
Os domínios da ANTP (antp.org.br, files.antp.org.br, antigo.antp.org.br) e o
serviço de busca usado para descoberta estão fora da lista de domínios
liberados no proxy de rede da sessão na nuvem. Mesmo princípio já registrado
em `baixar_pdfs_antp_por_csv.py`.

O QUE MUDA EM RELAÇÃO AO `baixar_pdfs_antp_por_csv.py`
-------------------------------------------------------
Aquele script espera que o CSV já traga a URL do PDF (coluna `link`), porque
foi feito para o resultado do scraper `rsl2_antp_biblioteca_scraper.py`, que
só varre o catálogo ANTIGO (antigo.antp.org.br) — e é exatamente esse catálogo
que devolveu "SEM LINK" para os 30 itens desta triagem. Uma checagem manual
(feita nesta sessão, 12/09/2026) mostrou que a ANTP migrou parte do acervo
para um domínio NOVO (files.antp.org.br), com um padrão de nome de arquivo
plausível de encontrar por busca (ex.: RTP 152 e o "Fundo Social do Transporte
Público" de Néspoli/2020 — este último confirmado em
files.antp.org.br/2020/10/21/fundo-social-do-transporte-publico--fstp.pdf).

⚠️ CORREÇÃO PÓS-RODADA DE 12/09/2026 (importante, leia antes de rodar de novo)
-------------------------------------------------------------------------------
A primeira versão deste script baixava automaticamente o PRIMEIRO resultado
plausível da busca por palavra-chave (ddgs) sempre que `url_candidato` vinha
vazio — sem checar se o CONTEÚDO do PDF batia com o título procurado. Numa
rodada real (12/09/2026, 12 itens, 4 "baixados"), a conferência manual do
conteúdo mostrou que **3 dos 4 "baixados" eram o documento ERRADO**:
  - id1 baixou o manual nacional "Custos dos Serviços de Transporte Público
    por Ônibus — Método de Cálculo" (ago/2017), não o item do Fórum Gaúcho.
  - id2 baixou um artigo da NTU ("Panorama da mobilidade urbana..."), sem
    relação com o item do Fórum Mineiro/BH.
  - id18 baixou de fato a apresentação de Adauto Farias (que é o item id17,
    "Subsídio à Tarifa do Transporte Coletivo — Caso: Município de São
    Paulo"), mas gravou com o nome/metadado do id18 (Wilson Folgozi de
    Brito) — ou seja, o item 17 foi encontrado e mal-rotulado, e o item 18
    continua de fato sem achar.
  Só id8 saiu certo — mas usava `url_candidato` pré-semeado (link já
  conferido manualmente antes da rodada), não busca automática.

  **Por isso esta versão NÃO baixa mais nada que venha só de busca por
  palavra-chave.** Ela agora só baixa automaticamente quando `url_candidato`
  já vem preenchido no CSV (link que você já conferiu manualmente). Para os
  itens sem `url_candidato`, ela lista os candidatos encontrados pela busca
  (sem baixar) para você conferir o título/autor a olho e colar o link
  certo em `url_candidato` numa próxima rodada.

Este script faz, para cada linha com `baixar=1`:
  1. Se `url_candidato` vier preenchida: baixa direto e confirma que é um
     PDF de verdade (assinatura `%PDF-`) antes de gravar como sucesso —
     subpáginas HTML de erro não contam como PDF. Isto é o único jeito de
     terminar com status "baixado".
  2. Se `url_candidato` vier vazia: BUSCA o título no DuckDuckGo (biblioteca
     `ddgs`, sem chave de API) restrita aos domínios prováveis da ANTP/FNP e
     REGISTRA os candidatos encontrados (até 5) na coluna `candidatos_busca`
     do manifesto, com status "candidatos_para_conferir" — nada é baixado
     automaticamente a partir daqui.

Não decide nada sobre corpus_rsl.csv nem sobre ficha — só baixa (quando o
link já foi conferido por você) e registra num manifesto. A leitura, a
conferência de conteúdo e a decisão de fichar continuam manuais.

INSTALAÇÃO (uma vez só, no seu ambiente conda)
-----------------------------------------------
    pip install ddgs

USO
---
    # 1) sempre primeiro — só mostra o que seria buscado/baixado, não baixa nada:
    python buscar_e_baixar_antp_descoberta.py --csv "...\\RSL2_frenteC_30_semlink_triagem_2026-09-12.csv" \\
        --dest "...\\frenteC_pdfs" --so-listar

    # 2) depois de conferir a lista, buscar e baixar de fato:
    python buscar_e_baixar_antp_descoberta.py --csv "...\\RSL2_frenteC_30_semlink_triagem_2026-09-12.csv" \\
        --dest "...\\frenteC_pdfs"

    # só tentar de novo os que falharam ou nao foram encontrados (pula os ja baixados):
    python buscar_e_baixar_antp_descoberta.py --csv "..." --dest "..." --somente-pendentes

Cada PDF é salvo como "<id>_<titulo-sanitizado>.pdf". Ao final, grava um
manifesto CSV em --dest (mesmo padrão `;`, sem BOM, LF) com o que foi
encontrado, a URL usada, tamanho e status.
"""

import argparse
import csv
import io
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "Mozilla/5.0 (compatible; RSL-PGT092-research-script/1.0; +pesquisa academica UFABC)"
MAX_TENTATIVAS = 3
SLEEP_PADRAO = 2.0  # segundos entre itens - ser gentil com ANTP/FNP e com o buscador
HOSTS_PROVAVEIS = (
    "antp.org.br", "files.antp.org.br", "files-server.antp.org.br",
    "antigo.antp.org.br", "multimidia.fnp.org.br", "fnp.org.br",
)


def sanitizar(texto, tamanho_max=60):
    if not texto:
        return "sememnome"
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    limpo = re.sub(r"[^a-zA-Z0-9]+", "-", sem_acento).strip("-").lower()
    return limpo[:tamanho_max] or "sememnome"


def nome_arquivo(row):
    return f"{int(row['id']):02d}_{sanitizar(row.get('titulo', ''), 55)}.pdf"


def url_e_provavel(url):
    try:
        host = urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(host == h or host.endswith("." + h) for h in HOSTS_PROVAVEIS)


def buscar_candidatos(titulo, autor, max_resultados=6):
    """Busca no DuckDuckGo (pacote `ddgs`) e devolve URLs de PDF nos domínios
    prováveis da ANTP/FNP, na ordem em que vieram (mais relevante primeiro)."""
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # nome antigo do pacote
        except ImportError:
            print("    [erro] pacote de busca nao instalado. Rode: pip install ddgs")
            return []

    consultas = [
        f'"{titulo}" antp.org.br filetype:pdf',
        f'"{titulo}" site:files.antp.org.br',
        f'"{titulo}" {autor} antp filetype:pdf' if autor else None,
    ]
    candidatos = []
    vistos = set()
    with DDGS() as ddgs:
        for q in consultas:
            if not q:
                continue
            try:
                for r in ddgs.text(q, max_results=max_resultados):
                    url = r.get("href") or r.get("url") or ""
                    if not url or url in vistos:
                        continue
                    vistos.add(url)
                    if url.lower().endswith(".pdf") and url_e_provavel(url):
                        candidatos.append(url)
            except Exception as e:
                print(f"    [busca] falhou para {q!r}: {e}")
            time.sleep(1.0)  # ser gentil com o buscador entre consultas
    return candidatos


def baixar_um(url, destino):
    """Baixa um arquivo e confirma que é PDF de verdade (assinatura %PDF-)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    espera = 2.0
    ultimo_erro = None
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                dados = resp.read()
            if not dados:
                raise RuntimeError("resposta vazia")
            if not dados.lstrip()[:5] == b"%PDF-":
                raise RuntimeError("resposta nao e um PDF valido (assinatura ausente)")
            tmp = destino + ".part"
            with open(tmp, "wb") as f:
                f.write(dados)
            os.replace(tmp, destino)
            return len(dados), None
        except Exception as e:
            ultimo_erro = e
            if tentativa < MAX_TENTATIVAS:
                print(f"    [tentativa {tentativa}/{MAX_TENTATIVAS}] falhou ({e}) - aguardando {espera:.0f}s...")
                time.sleep(espera)
                espera = min(20, espera * 2)
    return 0, ultimo_erro


def gravar_csv_validado(caminho, linhas, campos):
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
    ap.add_argument("--csv", required=True, help="CSV de triagem (com colunas 'baixar', 'titulo', 'url_candidato')")
    ap.add_argument("--dest", required=True, help="pasta onde os PDFs (e o manifesto) sao salvos")
    ap.add_argument("--so-listar", action="store_true", help="so mostra o que seria buscado/baixado, nao faz nada")
    ap.add_argument("--somente-pendentes", action="store_true",
                     help="pula itens ja baixados com sucesso numa rodada anterior (confere pelo arquivo local)")
    ap.add_argument("--sleep", type=float, default=SLEEP_PADRAO, help=f"segundos entre itens (default {SLEEP_PADRAO})")
    args = ap.parse_args()

    with open(args.csv, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))

    if not linhas:
        sys.exit(f"ERRO: {args.csv} nao tem nenhuma linha.")

    alvo = [r for r in linhas if str(r.get("baixar", "")).strip() == "1"]

    print(f"[buscar_e_baixar] {len(alvo)} de {len(linhas)} linha(s) marcada(s) para baixar:\n")
    for r in alvo:
        tem_url = "com url_candidato" if r.get("url_candidato", "").strip() else "SEM url — vai buscar"
        print(f"  [{r['id']:>2}] {r['titulo']!r} ({tem_url})")

    if args.so_listar:
        print("\n--so-listar: nada foi buscado nem baixado. Rode de novo sem essa flag para executar.")
        return

    os.makedirs(args.dest, exist_ok=True)
    manifesto = []
    for r in alvo:
        arquivo = nome_arquivo(r)
        destino = os.path.join(args.dest, arquivo)
        registro = {
            "id": r["id"], "titulo": r["titulo"], "secao": r.get("secao", ""),
            "autor": r.get("autor", ""), "url_usada": "", "arquivo_local": arquivo,
            "tamanho_bytes": "", "status": "", "candidatos_busca": "",
        }

        if args.somente_pendentes and os.path.exists(destino) and os.path.getsize(destino) > 0:
            print(f"\n[{r['id']:>2}] ja existe ({os.path.getsize(destino)/1e3:.0f} KB) - pulando")
            registro.update(tamanho_bytes=os.path.getsize(destino), status="ja_existia")
            manifesto.append(registro)
            continue

        print(f"\n[{r['id']:>2}] {r['titulo']!r}")

        url_seed = (r.get("url_candidato") or "").strip()

        if url_seed:
            # Único caminho que pode terminar em "baixado": link ja conferido
            # manualmente (por voce ou numa rodada anterior), presente no CSV.
            print(f"     baixando de url_candidato (ja conferido): {url_seed}")
            tamanho, erro = baixar_um(url_seed, destino)
            if not erro:
                print(f"     OK — {tamanho/1e3:.0f} KB salvos em {destino}")
                registro.update(url_usada=url_seed, tamanho_bytes=tamanho, status="baixado")
            else:
                print(f"     falhou: {erro}")
                registro["status"] = f"falhou: {erro}"
        else:
            # Sem link conferido: so lista candidatos da busca, NAO baixa nada
            # automaticamente (ver nota de correcao no topo do arquivo - a
            # rodada de 12/09/2026 mostrou 3 de 4 downloads automaticos errados).
            print("     sem url_candidato — buscando candidatos por titulo (ddgs), so para listar...")
            achados = buscar_candidatos(r["titulo"], r.get("autor", ""))
            if achados:
                for url in achados:
                    print(f"     candidato (NAO baixado — confira o titulo/autor antes de usar): {url}")
                registro["candidatos_busca"] = " | ".join(achados)
                registro["status"] = "candidatos_para_conferir"
            else:
                print("     nenhum candidato plausível encontrado pela busca")
                registro["status"] = "nao_encontrado"
        manifesto.append(registro)
        time.sleep(args.sleep)

    caminho_manifesto = os.path.join(
        args.dest, f"manifesto_descoberta_{time.strftime('%Y-%m-%d_%H%M')}.csv")
    campos = ["id", "titulo", "secao", "autor", "url_usada", "arquivo_local", "tamanho_bytes",
              "status", "candidatos_busca"]
    gravar_csv_validado(caminho_manifesto, manifesto, campos)
    print(f"\n[buscar_e_baixar] manifesto gravado em {caminho_manifesto}")

    para_conferir = [m for m in manifesto if m["status"] == "candidatos_para_conferir"]
    if para_conferir:
        print(f"\n[aviso] {len(para_conferir)} item(ns) com candidato(s) encontrado(s) pela busca, "
              f"mas NAO baixados — confira a coluna 'candidatos_busca' do manifesto, abra o PDF que "
              f"parecer certo, confirme que titulo/autor batem, e so entao cole a URL em "
              f"'url_candidato' no CSV de triagem para uma nova rodada com --somente-pendentes.")

    nao_encontrados = [m for m in manifesto if m["status"] == "nao_encontrado"]
    if nao_encontrados:
        print(f"\n[aviso] {len(nao_encontrados)} item(ns) sem nenhum candidato plausivel — "
              f"pode valer tentar manualmente no navegador (ex.: 'ANTP <titulo>' ou visitar "
              f"antp.org.br/biblioteca/ e buscar pelo titulo) e preencher 'url_candidato' no CSV "
              f"para uma nova rodada. Repare tambem que parte destes 'nao encontrado' pode ser "
              f"falha do proprio buscador (o pacote ddgs as vezes erra por instabilidade de um dos "
              f"backends que usa por baixo — nao é garantia de que o documento nao existe).")


if __name__ == "__main__":
    main()
