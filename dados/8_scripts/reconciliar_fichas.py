#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""reconciliar_fichas.py — varredura READ-ONLY das 267 fichas municipais em
busca de campos-resumo (frontmatter e bullets de topo) que podem estar
desatualizados frente a um achado/correção registrado mais adiante na MESMA
ficha.

======================================================================
POR QUE ISTO EXISTE
======================================================================
Achado em Cláudio/MG (20/09/2026): a seção `## Fatores impulsionadores/
limitantes` dizia "crise aguda (evento climático/calamidade)" como
impulsionador. Mas um callout mais abaixo, na MESMA ficha, de 19/09/2026,
registra que a motivação real — confirmada por documento primário — foi
"rescisão contratual da concessionária", e que o campo "deve ser corrigida...
a revisar pelo autor". O campo-resumo nunca foi atualizado depois da
correção. Antes de transformar esses campos em prosa (pedido do autor,
20/09/2026), é preciso achar quantas fichas têm esse mesmo padrão —
senão a prosa fica bem escrita e errada.

======================================================================
O QUE O SCRIPT FAZ, E O QUE NÃO FAZ
======================================================================
NÃO edita nada. NÃO decide se há contradição de fato — só aponta onde um
marcador de correção/divergência aparece perto (por vocabulário) de um
campo-resumo candidato, para leitura humana (ou de uma passada de IA
dedicada) decidir. Falso positivo é esperado e aceitável; falso negativo
(marcador de correção que o script não pega) é o risco maior, então a
lista de palavras-gatilho é ampla de propósito.

Campos-resumo verificados: frontmatter (camada, situacao, tipologia_analitica,
ano_inicio, operador, status_ficha) e os bullets de "## Fatores
impulsionadores/limitantes" e "**Motivações:**" (dentro de "## 2. Principais
dados").

Marcadores de correção/divergência procurados no restante do corpo: callouts
[!info]/[!warning]/[!danger] com ✅/🔴/🚨, e as palavras corrig-, divergênc-,
resolvid-, revisar, superad-, "não confere", contradiz, equivoc-, "achado
desta rodada", "correção de achado".

USO  python reconciliar_fichas.py [--report]
"""
import argparse
import datetime
import glob
import os
import re
import sys

RAIZ = os.environ.get("TZ_VAULT") or os.getcwd()
PASTA = os.path.join(RAIZ, "04 - Análises", "Casos municipais", "Fichas por município")
HOJE = datetime.date.today().strftime("%Y-%m-%d")

MARCADORES = re.compile(
    r"(✅|🔴|🚨).{0,80}?(corrig\w*|diverg[êe]nc\w*|resolvid\w*|revisar|superad\w*|"
    r"n[ãa]o confere|contradiz\w*|equivoc\w*|achado desta rodada|corre[çc][ãa]o de achado)",
    re.IGNORECASE,
)
# tópicos e as palavras que os identificam, para cruzar campo-resumo × marcador
TOPICOS = {
    "motivacao": [r"motiva", r"gênese", r"genese", r"pandemia", r"crise", r"rescis[aã]o",
                  r"emerg[êe]ncia", r"colapso"],
    "camada": [r"camada", r"universal", r"parcial", r"encerrad", r"port[aã]o"],
    "situacao": [r"situa[çc][ãa]o", r"\bativa\b", r"\bencerrada\b"],
    "operador": [r"operador", r"concession[aá]ri", r"prefeitura", r"locação", r"locacao"],
    "ano_inicio": [r"ano.?in[íi]cio", r"desde \d{4}", r"institu[íi]da? em \d{4}"],
}


def secao(texto, titulo_regex, ate_regex=r"^#{1,4}\s|^---\s*$"):
    m = re.search(titulo_regex, texto, re.M)
    if not m:
        return ""
    resto = texto[m.end():]
    fim = re.search(ate_regex, resto, re.M)
    return resto[: fim.start()] if fim else resto


def frontmatter(txt):
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        return {}
    fm = {}
    for linha in m.group(1).split("\n"):
        mm = re.match(r"^(\w[\w_]*):\s*(.+)$", linha)
        if mm:
            fm[mm.group(1)] = mm.group(2).strip().strip('"')
    return fm


def bate_topico(campo_nome, valor, snippet):
    valor = (valor or "").lower()
    snippet_low = snippet.lower()
    palavras = []
    for topico, regexes in TOPICOS.items():
        if any(re.search(r, campo_nome, re.I) for r in [topico]) or any(
            re.search(r, valor) for r in regexes
        ):
            palavras.extend(regexes)
    if not palavras:
        # fallback: qualquer palavra de 5+ letras do próprio valor do campo
        palavras = [re.escape(w) for w in re.findall(r"\w{5,}", valor)]
    return any(re.search(p, snippet_low) for p in palavras)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="grava relatório em _meta/")
    a = ap.parse_args()

    arquivos = sorted(glob.glob(os.path.join(PASTA, "Ficha - *.md")))
    if not arquivos:
        sys.exit(f"🔴 nenhuma ficha achada em {PASTA}")

    achados = []
    total_marcadores = 0
    for caminho in arquivos:
        with open(caminho, encoding="utf-8") as f:
            txt = f.read()
        nome = os.path.basename(caminho)

        marcas = list(MARCADORES.finditer(txt))
        if not marcas:
            continue
        total_marcadores += len(marcas)

        fm = frontmatter(txt)
        fatores = secao(txt, r"^##\s*Fatores impulsionadores/limitantes\s*$")
        motiv_m = re.search(r"\*\*Motiva[çc][õo]es:\*\*\s*(.+)", txt)
        campos = {
            "frontmatter.camada": fm.get("camada"),
            "frontmatter.situacao": fm.get("situacao"),
            "frontmatter.operador": fm.get("operador"),
            "frontmatter.ano_inicio": fm.get("ano_inicio"),
            "Fatores impulsionadores/limitantes": fatores.strip()[:300] if fatores.strip() else None,
            "Motivações (§2)": motiv_m.group(1).strip()[:300] if motiv_m else None,
        }

        for marca in marcas:
            ini = max(0, marca.start() - 300)
            fim = min(len(txt), marca.end() + 300)
            snippet = txt[ini:fim]
            for campo_nome, valor in campos.items():
                if valor and bate_topico(campo_nome, valor, snippet):
                    achados.append({
                        "ficha": nome,
                        "campo": campo_nome,
                        "valor_atual": valor,
                        "marcador": marca.group(0),
                        "contexto": re.sub(r"\s+", " ", snippet).strip(),
                    })

    fichas_distintas = sorted({a["ficha"] for a in achados})
    print(f"Fichas com marcador de correção/divergência: "
          f"{len({os.path.basename(x) for x in arquivos if MARCADORES.search(open(x, encoding='utf-8').read())})} "
          f"de {len(arquivos)} · total de marcadores: {total_marcadores}")
    print(f"Fichas com POSSÍVEL campo-resumo desatualizado (cruzamento por vocabulário): "
          f"{len(fichas_distintas)}")
    print(f"Candidatos totais (ficha × campo × marcador): {len(achados)}\n")

    for nome in fichas_distintas:
        itens = [x for x in achados if x["ficha"] == nome]
        print(f"### {nome}")
        for it in itens:
            print(f"  - campo: {it['campo']}")
            print(f"    valor atual: {it['valor_atual']!r}")
            print(f"    marcador: {it['marcador']!r}")
            print(f"    contexto: …{it['contexto']}…")
        print()

    if a.report:
        caminho_rel = os.path.join(RAIZ, "_meta", f"reconciliacao-fichas-{HOJE}.md")
        with open(caminho_rel, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"# Reconciliação de fichas — candidatos a campo-resumo desatualizado ({HOJE})\n\n")
            f.write(f"Gerado por `_meta/scripts/reconciliar_fichas.py` (read-only). "
                    f"{len(fichas_distintas)} fichas de {len(arquivos)} com candidato.\n\n")
            f.write("⚠️ Falso positivo é esperado — é cruzamento por vocabulário, não leitura "
                    "semântica. Cada item precisa de checagem manual (ou de uma passada de IA "
                    "dedicada) antes de qualquer edição.\n\n")
            for nome in fichas_distintas:
                itens = [x for x in achados if x["ficha"] == nome]
                f.write(f"## {nome}\n\n")
                for it in itens:
                    f.write(f"- **campo:** `{it['campo']}`\n")
                    f.write(f"  **valor atual:** {it['valor_atual']}\n")
                    f.write(f"  **marcador:** {it['marcador']}\n")
                    f.write(f"  **contexto:** …{it['contexto']}…\n\n")
        print(f"\n✅ relatório gravado em {caminho_rel}")


if __name__ == "__main__":
    main()
