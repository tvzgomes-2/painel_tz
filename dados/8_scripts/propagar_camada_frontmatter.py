#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""propagar_camada_frontmatter.py — propaga a camada CONFIRMADA pelo bloco
"Portão de acesso" (gerado por enriquecer_regua_portao.py) para o campo
`camada:` do frontmatter, quando os dois divergem.

Só age em fichas com camada CONFIRMADA (não "candidato pela aba"), e só quando
o frontmatter está no formato simples "universal (1a)" / "parcial (2d)" /
"encerrada (3)" — sem prosa de trajetória. Frontmatter com prosa (trajetória,
"a classificar", texto livre) é listado como "não tocado — decisão manual",
nunca sobrescrito: um bloco Portão só enxerga UMA evidência de portão, não a
história completa de um caso multi-episódio (achado em Palmas/TO, 20/09/2026).

IDEMPOTENTE. Simula por padrão. Backup antes de gravar.

USO  python propagar_camada_frontmatter.py [--gravar]
"""
import argparse
import datetime
import glob
import os
import re
import shutil
import sys

RAIZ = os.environ.get("TZ_VAULT") or os.getcwd()
PASTA = os.path.join(RAIZ, "04 - Análises", "Casos municipais", "Fichas por município")

RE_FM_CAMADA_LINHA = re.compile(r"^camada:\s*(.+)$", re.M)
RE_FM_SIMPLES = re.compile(r"^(universal|parcial|encerrada)\s*\(([1-3][a-d]?)\)$")
RE_PORTAO_CAMADA = re.compile(
    r"Camada correspondente na régua em vigor \(1 a 3\):\*\*\s*\*\*(\d[a-z]?)\s*—",
    re.IGNORECASE,
)

PREFIXO = {"1": "universal", "2": "parcial", "3": "encerrada"}


def rotulo(codigo):
    return f"{PREFIXO[codigo[0]]} ({codigo})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args()

    arquivos = sorted(glob.glob(os.path.join(PASTA, "Ficha - *.md")))
    if not arquivos:
        sys.exit(f"🔴 nenhuma ficha achada em {PASTA}")

    propor, manual = [], []
    for caminho in arquivos:
        with open(caminho, encoding="utf-8") as f:
            txt = f.read()
        nome = os.path.basename(caminho)

        m_portao = RE_PORTAO_CAMADA.search(txt)
        if not m_portao:
            continue  # sem camada confirmada — nada a propagar
        codigo_confirmado = m_portao.group(1).lower()

        m_fm = RE_FM_CAMADA_LINHA.search(txt)
        if not m_fm:
            continue
        valor_fm = m_fm.group(1).strip()
        valor_fm_limpo = valor_fm.strip('"').strip()

        m_simples = RE_FM_SIMPLES.match(valor_fm_limpo)
        if not m_simples:
            # frontmatter com prosa/trajetória — nunca sobrescrever sozinho
            codigo_fm = re.search(r"\(([1-3][a-d]?)\)", valor_fm)
            if codigo_fm and codigo_fm.group(1).lower() != codigo_confirmado:
                manual.append((nome, valor_fm, codigo_confirmado))
            continue

        codigo_fm = m_simples.group(2).lower()
        if codigo_fm == codigo_confirmado:
            continue  # já bate

        novo_valor = rotulo(codigo_confirmado)
        linha_velha = m_fm.group(0)
        linha_nova = f"camada: {novo_valor}"
        propor.append((nome, caminho, txt, linha_velha, linha_nova, codigo_fm, codigo_confirmado))

    print(f"{len(arquivos)} fichas · {len(propor)} com frontmatter simples a propagar · "
          f"{len(manual)} com prosa/trajetória — NÃO tocadas, decisão manual\n")

    for nome, _, _, velha, nova, cfm, cconf in propor:
        print(f"  {nome}: {velha!r}  →  {nova!r}")
    if manual:
        print("\n--- frontmatter com prosa, divergente do portão confirmado, NÃO tocado ---")
        for nome, valor_fm, cconf in manual:
            print(f"  {nome}: frontmatter={valor_fm!r} · portão confirma {cconf!r}")

    if not a.gravar:
        print("\nnada foi escrito. Para aplicar: --gravar")
        return

    bk = os.path.join(RAIZ, "_meta", "_backups",
                      "camada-frontmatter-" + datetime.datetime.now().strftime("%Y-%m-%d_%H%M"))
    os.makedirs(bk, exist_ok=True)
    for nome, caminho, txt, velha, nova, _, _ in propor:
        shutil.copy2(caminho, os.path.join(bk, nome))
        novo_txt = txt.replace(velha, nova, 1)
        with open(caminho, "w", encoding="utf-8", newline="\n") as f:
            f.write(novo_txt)
    print(f"\n✅ {len(propor)} fichas · backup em {os.path.basename(bk)}")


if __name__ == "__main__":
    main()
