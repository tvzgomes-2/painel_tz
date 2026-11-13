#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buscar_siscam.py — tenta localizar câmaras municipais que usam o SISCAM
("SISCAM :: Gestão do Processo Legislativo") e, nas que existirem, buscar
legislação de Tarifa Zero.

⚠️ AVISO IMPORTANTE, LEIA ANTES DE RODAR
  SISCAM é um produto comercial da SINO Informática (mesma empresa da
  "Legislação Digital"/"Sino.Siave") — cada câmara com seu próprio
  subdomínio (https://<slug>.siscam.com.br/), aparentemente uma aplicação
  web tradicional (páginas HTML, não JSON). Eu (Claude) não tenho acesso
  direto ao sandbox de nuvem para inspecionar essas páginas (bloqueio de
  rede da conta) — o que sei vem de resultados de busca (12/09/2026), não
  de ter aberto uma página de verdade. Por isso este script tem DUAS
  PARTES com confiabilidade diferente:

  1) `descobrir` — PROVÁVEL DE FUNCIONAR. Só testa se existe uma câmara
     nesse subdomínio (nenhum scraping de conteúdo, só "o host responde?").
     Baseado em exemplos reais vistos via busca (Paulínia, Sorriso,
     Guarujá, Charqueada, São Miguel Arcanjo, Niterói, Itapevi, Itajubá,
     Americana) — a maioria no padrão https://<slug>.siscam.com.br/, slug
     = nome do município sem acento/espaço. ⚠️ Exceção confirmada:
     Cordeirópolis usa `cordeiropolis9.siscam.com.br` (sufixo numérico) —
     o script não tenta sufixos numéricos por padrão (evita multiplicar
     requisições por host); se `descobrir` não achar um município que você
     sabe que tem câmara no SISCAM, tente manualmente
     `<slug>1.siscam.com.br`, `<slug>2...` etc. antes de descartar.

  2) `listar` — MENOS EXPERIMENTAL do que antes, mas ainda não confirmado
     ponta a ponta. Busca (12/09) achou DUAS câmaras diferentes e sem
     relação entre si — Sorriso/MT e Guarujá/SP — publicando sua seção de
     "Legislação" no MESMO caminho: `https://<slug>.siscam.com.br/index/75/8`.
     Isso sugere que 75/8 pode ser um código fixo da plataforma (não por
     instalação) — o script agora TENTA esse caminho direto primeiro, e só
     cai para a busca por link na home (regex, o comportamento antigo) se
     a tentativa direta não parecer uma página de legislação. Ainda não
     testado numa câmara real por mim — TESTE
     `listar --municipio sorriso --so-um --debug` primeiro (ou
     `--municipio cotia`, que foi o exemplo que o autor deu) e confira a
     saída antes de rodar a lista inteira. Padrão de arquivo confirmado
     por busca: `/arquivo?Id=<numero>` (visto em Paulínia e Itajubá).

USO
    conda activate <seu-ambiente>          # precisa de: requests (urllib
                                            # básico já cobriria descobrir,
                                            # mas listar usa requests por
                                            # comodidade de sessão/redirect)
    cd caminho\\para\\_meta\\scripts

    # 1) descobrir quais dos municípios-alvo têm câmara no SISCAM
    python buscar_siscam.py descobrir

    # 2) só nos que existirem, tentar achar e listar a seção de legislação
    python buscar_siscam.py listar

    # 3) testar a lógica de listagem em UM município só, com saída verbosa
    python buscar_siscam.py listar --municipio paulinia --so-um --debug

ALVO (mesmo critério de buscar_querido_diario.py)
    Por padrão, os municípios com `estado` começando em "B1" (número
    declarado, texto a obter) ou "C" (nada localizado) no Controle único —
    os mesmos ~126 casos que a rodada do Querido Diário também mirou. Use
    --filtro para restringir (ex.: "C") ou --municipios-csv para uma lista
    própria (precisa de colunas municipio,uf).

SAÍDA
    saida_siscam/hosts.csv          — um município por linha: existe? qual
                                       slug funcionou? (fase `descobrir`)
    saida_siscam/legislacao.csv     — despejo do que `listar` conseguiu
                                       extrair (título, data aproximada,
                                       url do arquivo, termo batido)
    saida_siscam/paginas_brutas/    — HTML bruto de cada página de listagem
                                       processada, para conferência manual
                                       (sempre salvo, mesmo sem achado —
                                       assim dá pra revisar o parser depois
                                       sem rodar de novo)

ETIQUETA
    --pausa (padrão 1,5s por host) e User-Agent identificando a pesquisa.
    Respeita robots.txt antes de buscar qualquer página de conteúdo (função
    `permitido_por_robots`) — se o robots.txt de uma câmara proibir o
    caminho, o script PULA aquele host e registra o motivo, não tenta
    contornar. São câmaras municipais pequenas, sem defesa de tráfego — não
    abuse: não paralelizei este script de propósito (diferente do
    sapl_varredura.py, que usa threads), para manter uma requisição de cada
    vez.

Autor: Thiago Von Zeidler Gomes
Orientadora: Prof.ª Silvana Zioni
"""
import sys
import re
import csv
import time
import json
import argparse
import unicodedata
import urllib.robotparser
from pathlib import Path
from urllib.parse import urljoin, urlparse

# Console do Windows (cmd.exe / Anaconda Prompt) costuma vir em cp1252 e
# estoura UnicodeEncodeError ao imprimir acentos — mesma correção usada em
# sapl_varredura.py.
for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import requests
except ImportError:
    sys.exit(
        "Faltou o pacote 'requests'. Instale com: pip install requests\n"
        "(ou: conda install requests)"
    )

VERSAO = "0.1 (12-09-2026) — EXPLORATÓRIO, ver aviso no topo do arquivo"

USER_AGENT = (
    "Pesquisa-Academica-UFABC-TarifaZero/0.1 "
    "(doutorado PGT/UFABC; contato: thiago@poloplanejamento.com; "
    "levantamento de legislacao municipal de transporte publico)"
)

CAMINHO_CONTROLE = (
    Path(__file__).resolve().parent.parent.parent
    / "03 - Dados" / "_data" / "Legislacao e contratos TZ"
    / "_historico" / "Controle unico - legislacao PlanMob e contratos, 176 casos (2026-09-11).csv"
)

# Termos fortes de Tarifa Zero — mesma lista de buscar_querido_diario.py,
# para os dois levantamentos ficarem comparáveis.
TERMOS = [
    "tarifa zero",
    "passe livre",
    "transporte coletivo gratuito",
    "transporte gratuito",
    "gratuidade tarifária",
    "subsídio tarifário",
]

# Padrões de subdomínio a tentar por município, na ordem. Baseado nos 7
# exemplos vistos (a maioria é só o nome da cidade "colado", sem acento,
# sem espaço/hífen; Niterói foi o único caso com prefixo "camara").
def candidatos_slug(municipio: str) -> list:
    base = normalizar(municipio)
    variantes = [
        base,
        f"camara{base}",
        f"cm{base}",
        f"camaramunicipalde{base}",
    ]
    # remove duplicatas mantendo ordem
    vistos, out = set(), []
    for v in variantes:
        if v not in vistos:
            vistos.add(v)
            out.append(v)
    return out


def normalizar(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]", "", s)  # remove espaço, hífen, apóstrofo etc.
    return s


def montar_alvos(filtro, municipios_csv) -> list:
    """Devolve lista de dicts {municipio, uf}."""
    if municipios_csv:
        with open(municipios_csv, encoding="utf-8-sig") as f:
            leitor = csv.DictReader(f)
            return [{"municipio": r["municipio"], "uf": r["uf"]} for r in leitor]

    if not CAMINHO_CONTROLE.exists():
        sys.exit(
            f"Não achei o Controle único em:\n  {CAMINHO_CONTROLE}\n"
            "Ajuste CAMINHO_CONTROLE no topo do script, ou use --municipios-csv "
            "com sua própria lista (colunas: municipio,uf)."
        )

    import pandas as pd  # só carregado aqui — descobrir/listar não precisam de pandas

    df = pd.read_csv(CAMINHO_CONTROLE, dtype={"cod_ibge": str})
    df["estado"] = df["estado"].astype(str)
    alvo = df[df["estado"].str.startswith(tuple(filtro.split(",")))] if filtro else df[
        df["estado"].str.startswith(("B1", "C"))
    ]
    return alvo[["municipio", "uf"]].to_dict("records")


def sessao_http() -> "requests.Session":
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def host_existe(sess, slug: str, timeout=12):
    """Tenta GET na raiz do subdomínio. Devolve (existe: bool, status, url_final,
    motivo) — trata timeout/DNS/conexão recusada como 'não existe', qualquer
    resposta HTTP (mesmo 404/403/redirect) como 'existe' (o host responde,
    então a câmara está lá, mesmo que a raiz não seja a página certa)."""
    url = f"https://{slug}.siscam.com.br/"
    try:
        r = sess.get(url, timeout=timeout, allow_redirects=True)
        return True, r.status_code, r.url, None
    except requests.exceptions.SSLError as e:
        # tenta http:// puro antes de desistir — alguns hosts antigos não têm TLS
        try:
            r = sess.get(f"http://{slug}.siscam.com.br/", timeout=timeout, allow_redirects=True)
            return True, r.status_code, r.url, "sem TLS (http simples)"
        except Exception:
            return False, None, None, f"erro SSL: {e}"
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        return False, None, None, type(e).__name__
    except Exception as e:
        return False, None, None, f"{type(e).__name__}: {e}"


def cmd_descobrir(args):
    saida = Path(args.saida)
    saida.mkdir(exist_ok=True)
    alvos = montar_alvos(args.filtro, args.municipios_csv)
    print(f"{len(alvos)} município(s) a testar (até {sum(len(candidatos_slug(a['municipio'])) for a in alvos)} tentativas de subdomínio).")

    sess = sessao_http()
    linhas = []
    for i, alvo in enumerate(alvos):
        municipio, uf = alvo["municipio"], alvo["uf"]
        achou = False
        for slug in candidatos_slug(municipio):
            existe, status, url_final, motivo = host_existe(sess, slug)
            if existe:
                print(f"[{i+1}/{len(alvos)}] {municipio}/{uf} -> 🎯 {slug}.siscam.com.br (HTTP {status})")
                linhas.append({
                    "municipio": municipio, "uf": uf, "slug_encontrado": slug,
                    "status_http": status, "url_final": url_final, "existe": True,
                    "tentativas": ", ".join(candidatos_slug(municipio)),
                })
                achou = True
                break
            time.sleep(args.pausa)
        if not achou:
            print(f"[{i+1}/{len(alvos)}] {municipio}/{uf} -> nenhum subdomínio respondeu")
            linhas.append({
                "municipio": municipio, "uf": uf, "slug_encontrado": "",
                "status_http": "", "url_final": "", "existe": False,
                "tentativas": ", ".join(candidatos_slug(municipio)),
            })
        time.sleep(args.pausa)

    campos = ["municipio", "uf", "existe", "slug_encontrado", "status_http", "url_final", "tentativas"]
    with open(saida / "hosts.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)

    n_achados = sum(1 for l in linhas if l["existe"])
    print(f"\n=== {n_achados}/{len(linhas)} município(s) com câmara no SISCAM ===")
    print(f"Detalhe em {saida}/hosts.csv — próximo passo: python buscar_siscam.py listar")
    print(
        "\n⚠️  Lembrete: 'existe' aqui só significa que ALGO respondeu em "
        "https://<slug>.siscam.com.br/ — pode ser a home da câmara, uma tela "
        "de login, ou um domínio genérico que por acaso resolve. Confirme "
        "visualmente 1 ou 2 antes de confiar na lista inteira."
    )


def permitido_por_robots(sess, url: str, cache: dict) -> bool:
    parsed = urlparse(url)
    origem = f"{parsed.scheme}://{parsed.netloc}"
    if origem not in cache:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(urljoin(origem, "/robots.txt"))
        try:
            r = sess.get(urljoin(origem, "/robots.txt"), timeout=10)
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
            else:
                rp.parse([])  # sem robots.txt публicado -> permissivo
        except Exception:
            rp.parse([])
        cache[origem] = rp
    return cache[origem].can_fetch(USER_AGENT, url)


# --- Parser de listagem — ver aviso no topo do arquivo --------------------
# Duas hipóteses de padrão de link de documento, na ordem em que o script
# tenta (a primeira que achar QUALQUER ocorrência na página "vence" e é
# usada para toda a página):
#   (a) <a href="/arquivo?Id=NNNNN">Título do documento aqui</a>
#   (b) qualquer <a> cujo texto pareça ementa/título de lei (heurística
#       fraca: contém "Lei", "Decreto", "Resolução" etc. + um número)
PADRAO_LINK_ARQUIVO = re.compile(
    r'<a[^>]+href="([^"]*?/arquivo\?Id=\d+[^"]*)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
PADRAO_LINK_LEGISLACAO_NAV = re.compile(
    r'<a[^>]+href="([^"]*?/index/\d+/\d+[^"]*)"[^>]*>\s*([^<]*legisla[^<]*)</a>',
    re.IGNORECASE,
)

# Caminho visto em 2 instalações independentes (Sorriso/MT e Guarujá/SP) —
# ver aviso no topo do arquivo. Tentado primeiro, direto, antes de cair
# para a busca por link na home.
CAMINHO_LEGISLACAO_PADRAO = "/index/75/8"


def limpar_html(txt: str) -> str:
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"&nbsp;", " ", txt)
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()


def parece_pagina_de_legislacao(html: str) -> bool:
    """Heurística fraca: a página tem algum link /arquivo?Id=... (documento
    de verdade) OU a palavra 'legisla' aparece perto do topo do HTML. Não é
    prova — só serve para decidir se o caminho-padrão /index/75/8 "colou"
    ou se é melhor cair para a busca por link na home."""
    if PADRAO_LINK_ARQUIVO.search(html):
        return True
    return "legisla" in limpar_html(html[:4000]).lower()


def achar_link_legislacao(sess, home_url: str, checar_robots, tentar_caminho_padrao: bool = True) -> str:
    # 1) tentativa direta no caminho visto em Sorriso/Guarujá — evita ter
    #    que baixar e regexar a home quando o padrão se repete.
    #    `checar_robots(url) -> bool` é chamado ANTES de qualquer GET, para
    #    respeitar robots.txt mesmo neste atalho (mesma regra do resto do
    #    script — ver ETIQUETA no topo do arquivo).
    if tentar_caminho_padrao:
        candidato = urljoin(home_url, CAMINHO_LEGISLACAO_PADRAO)
        if checar_robots(candidato):
            try:
                r = sess.get(candidato, timeout=15)
                if r.status_code == 200 and parece_pagina_de_legislacao(r.text):
                    return candidato
            except Exception:
                pass  # cai para a busca por link na home, abaixo

    # 2) busca por link de "Legislação" na home (comportamento original)
    r = sess.get(home_url, timeout=15)
    m = PADRAO_LINK_LEGISLACAO_NAV.search(r.text)
    if m:
        return urljoin(home_url, m.group(1))
    return None


def extrair_documentos(html: str, base_url: str) -> list:
    docs = []
    for m in PADRAO_LINK_ARQUIVO.finditer(html):
        href, texto = m.group(1), limpar_html(m.group(2))
        if not texto:
            continue
        docs.append({"url": urljoin(base_url, href), "titulo": texto})
    return docs


def cmd_listar(args):
    saida = Path(args.saida)
    (saida / "paginas_brutas").mkdir(parents=True, exist_ok=True)

    hosts_csv = saida / "hosts.csv"
    if args.municipio:
        alvos = [{"municipio": args.municipio, "uf": "", "slug_encontrado": args.municipio, "existe": True}]
    else:
        if not hosts_csv.exists():
            sys.exit(f"Não achei {hosts_csv} — rode 'descobrir' primeiro (ou passe --municipio para testar um só).")
        with open(hosts_csv, encoding="utf-8-sig") as f:
            alvos = [r for r in csv.DictReader(f) if r.get("existe") == "True"]

    if args.so_um and alvos:
        alvos = alvos[:1]

    print(f"{len(alvos)} câmara(s) SISCAM a tentar listar.")

    sess = sessao_http()
    robots_cache = {}
    achados = []

    for i, alvo in enumerate(alvos):
        slug = alvo.get("slug_encontrado") or normalizar(alvo["municipio"])
        home = f"https://{slug}.siscam.com.br/"
        print(f"\n=== [{i+1}/{len(alvos)}] {alvo['municipio']}/{alvo.get('uf','')} ({home}) ===")

        if not permitido_por_robots(sess, home, robots_cache):
            print("  🔴 robots.txt proíbe — pulando este host (não tentei contornar).")
            continue

        try:
            link_legis = achar_link_legislacao(
                sess, home,
                checar_robots=lambda u: permitido_por_robots(sess, u, robots_cache),
            )
        except Exception as e:
            print(f"  🔴 erro ao buscar a home: {e}")
            continue

        if not link_legis:
            print("  ·  não achei link de 'Legislação' na home (regex não bateu — "
                  "ver aviso no topo do arquivo; pode precisar ajustar o padrão).")
            if args.debug:
                (saida / "paginas_brutas" / f"{slug}__home.html").write_text(
                    sess.get(home, timeout=15).text, encoding="utf-8"
                )
                print(f"     HTML da home salvo em paginas_brutas/{slug}__home.html para conferência.")
            continue

        print(f"  link de legislação encontrado: {link_legis}")

        if not permitido_por_robots(sess, link_legis, robots_cache):
            print("  🔴 robots.txt proíbe esse caminho — pulando.")
            continue

        try:
            r = sess.get(link_legis, timeout=15)
        except Exception as e:
            print(f"  🔴 erro ao buscar a listagem: {e}")
            continue

        (saida / "paginas_brutas" / f"{slug}__listagem.html").write_text(r.text, encoding="utf-8")

        docs = extrair_documentos(r.text, link_legis)
        print(f"  {len(docs)} documento(s) encontrado(s) na página (sem paginação seguida ainda — ver aviso).")

        for doc in docs:
            baixo = doc["titulo"].lower()
            termos_batidos = [t for t in TERMOS if t in baixo]
            if termos_batidos:
                achados.append({
                    "municipio": alvo["municipio"], "uf": alvo.get("uf", ""),
                    "titulo": doc["titulo"], "url": doc["url"],
                    "termos_batidos": ", ".join(termos_batidos),
                })
                print(f"  🎯 {doc['titulo'][:100]}")

        time.sleep(args.pausa)

    campos = ["municipio", "uf", "titulo", "url", "termos_batidos"]
    with open(saida / "legislacao.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(achados)

    print(f"\n=== {len(achados)} título(s) batendo termo de Tarifa Zero, em {len(alvos)} câmara(s) tentadas ===")
    print(f"Detalhe em {saida}/legislacao.csv")
    print(
        "\n⚠️  Isto é triagem pelo TÍTULO do documento, mais raso ainda que a "
        "triagem por excerto do Querido Diário — o título pode não mencionar "
        "gratuidade mesmo numa lei relevante, e um título com 'passe livre' "
        "pode ser categorial (idoso, PCD, estudante), não Tarifa Zero. Abra o "
        "'url' e confirme antes de tratar como achado. E se 'X documento(s) "
        "encontrado(s) na página' veio 0 ou muito baixo em várias câmaras, o "
        "parser provavelmente precisa de ajuste — ver aviso no topo do arquivo."
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="comando", required=True)

    p1 = sub.add_parser("descobrir", help="testa quais municípios-alvo têm câmara no SISCAM")
    p1.add_argument("--saida", default="saida_siscam")
    p1.add_argument("--filtro", default=None, help='prefixo de "estado" no Controle único (ex.: "C" ou "B1"); padrão: B1 e C juntos')
    p1.add_argument("--municipios-csv", default=None, help="CSV próprio (colunas: municipio,uf) em vez do Controle único")
    p1.add_argument("--pausa", type=float, default=1.5)
    p1.set_defaults(func=cmd_descobrir)

    p2 = sub.add_parser("listar", help="tenta achar e listar a seção de legislação nas câmaras descobertas")
    p2.add_argument("--saida", default="saida_siscam")
    p2.add_argument("--municipio", default=None, help="testar um slug específico direto (ignora hosts.csv)")
    p2.add_argument("--so-um", action="store_true", help="processa só o primeiro host da lista (ou o --municipio dado) — para testar o parser")
    p2.add_argument("--debug", action="store_true", help="salva a home mesmo quando não acha o link de legislação")
    p2.add_argument("--pausa", type=float, default=1.5)
    p2.set_defaults(func=cmd_listar)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
