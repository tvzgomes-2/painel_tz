#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""checar_camada_frontmatter.py — READ-ONLY. Compara o `camada:` do
frontmatter de cada ficha com a camada que o próprio bloco `### Portão de
acesso — critério da régua descritiva` (gerado por enriquecer_regua_portao.py
em 19/09/2026) calcula para o mesmo caso, dentro da MESMA ficha.

Achado em Itapeva/SP (20/09/2026): frontmatter diz `camada: universal (1a)`,
mas o bloco Portão de acesso da própria ficha calcula **1b** (portão de
procedimento) — a conta nunca voltou pro frontmatter. É comparação
estrutural (dois campos gerados, não prosa livre), portanto mais confiável
que o cruzamento por vocabulário de reconciliar_fichas.py.

Não edita nada — só lista os casos onde os dois campos divergem.

USO  python checar_camada_frontmatter.py [--report]
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

RE_FM_CAMADA = re.compile(r"^camada:\s*(.+)$", re.M)
RE_PORTAO_CAMADA = re.compile(
    r"Camada correspondente na régua em vigor \(1 a 3\):\*\*\s*\*\*(\d[a-z]?)\s*—",
    re.IGNORECASE,
)
RE_CODIGO = re.compile(r"\b([1-3][a-d]?)\b")


def extrai_codigo_fm(valor):
    """Extrai o código (1a, 1b, 2c, 3...) de um valor de frontmatter tipo
    'universal (1a)' ou 'trajetória — ... → camada 2a temporal-dias (ativa)'."""
    m = re.search(r"\(([1-3][a-d]?)\)", valor)
    if m:
        return m.group(1)
    # fallback: procura 'camada N' ou 'camada Na' no texto
    m = re.search(r"camada\s+([1-3][a-d]?)\b", valor, re.IGNORECASE)
    if m:
        return m.group(1)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()

    arquivos = sorted(glob.glob(os.path.join(PASTA, "Ficha - *.md")))
    if not arquivos:
        sys.exit(f"🔴 nenhuma ficha achada em {PASTA}")

    com_bloco_portao = 0
    divergentes = []
    sem_camada_extraivel = []

    for caminho in arquivos:
        with open(caminho, encoding="utf-8") as f:
            txt = f.read()
        nome = os.path.basename(caminho)

        m_portao = RE_PORTAO_CAMADA.search(txt)
        if not m_portao:
            continue  # ficha sem o bloco de portão (ainda não gerado) — fora do escopo
        com_bloco_portao += 1
        codigo_portao = m_portao.group(1).lower()

        m_fm = RE_FM_CAMADA.search(txt)
        valor_fm = m_fm.group(1).strip() if m_fm else None
        codigo_fm = extrai_codigo_fm(valor_fm) if valor_fm else None

        if not codigo_fm:
            sem_camada_extraivel.append((nome, valor_fm))
            continue

        if codigo_fm.lower() != codigo_portao:
            divergentes.append({
                "ficha": nome,
                "frontmatter.camada": valor_fm,
                "codigo_frontmatter": codigo_fm,
                "codigo_portao_calculado": codigo_portao,
            })

    print(f"Fichas com bloco 'Portão de acesso' gerado: {com_bloco_portao} de {len(arquivos)}")
    print(f"Fichas com código de camada no frontmatter DIVERGENTE do que o bloco calcula: "
          f"{len(divergentes)}")
    print(f"Fichas com frontmatter.camada em formato não reconhecido (não comparável): "
          f"{len(sem_camada_extraivel)}\n")

    for d in divergentes:
        print(f"### {d['ficha']}")
        print(f"  frontmatter.camada: {d['frontmatter.camada']!r}  →  código {d['codigo_frontmatter']}")
        print(f"  bloco Portão de acesso calcula: {d['codigo_portao_calculado']}")
        print()

    if sem_camada_extraivel:
        print("--- não comparável (formato de frontmatter.camada fora do padrão) ---")
        for nome, valor in sem_camada_extraivel[:20]:
            print(f"  {nome}: {valor!r}")
        if len(sem_camada_extraivel) > 20:
            print(f"  ... e mais {len(sem_camada_extraivel) - 20}")

    if a.report:
        caminho_rel = os.path.join(RAIZ, "_meta", f"divergencia-camada-frontmatter-{HOJE}.md")
        with open(caminho_rel, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"# Divergência frontmatter.camada × bloco Portão de acesso ({HOJE})\n\n")
            f.write(f"Gerado por `_meta/scripts/checar_camada_frontmatter.py` (read-only). "
                    f"{com_bloco_portao} fichas têm o bloco 'Portão de acesso'; "
                    f"{len(divergentes)} divergem do frontmatter.\n\n")
            for d in divergentes:
                f.write(f"## {d['ficha']}\n\n")
                f.write(f"- **frontmatter.camada:** {d['frontmatter.camada']} (código {d['codigo_frontmatter']})\n")
                f.write(f"- **bloco Portão de acesso calcula:** {d['codigo_portao_calculado']}\n\n")
        print(f"\n✅ relatório gravado em {caminho_rel}")


if __name__ == "__main__":
    main()
