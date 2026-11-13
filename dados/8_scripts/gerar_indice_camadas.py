#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""gerar_indice_camadas.py (v2, 26/09/2026) — regera `Fichas por camada — índice
auditado` a partir das ABAS e da coluna SUBTIPO de `Tipologias TZ - consolidado.xlsx`,
na régua em vigor (A.1.4 + A.1.5 + A.1.6 de [[Regras de classificacao das reguas]]).

v2.1 (27/09/2026): mostra a 2d separada por regime (pré-2024 escolha local × pós-2024 obrigação — A.1.7), lida da coluna "Regime da 2d" da aba 2 Parcial.

POR QUE v2: a v1 (17–19/09) convertia abas da numeração de 13/09 (1 Universal · 2
Procedimento · 3 Grupo social · 4a/4b · 5) em camadas. A planilha foi consolidada em
20/09 em 1 Universal · 2 Parcial · 3 Encerradas · Não TZ, com o subtipo numa coluna
própria, e em 26/09 ganhou a aba "Regulamentada não implantada" (A.1.6). Rodada sobre a
planilha atual, a v1 jogava os 169 casos da aba 1 em "1a" e os demais em "sem
conversão" — um índice errado com aparência de certo. A v2 lê o subtipo onde ele está.

REGRAS DO ÍNDICE
- Aba 1 Universal: agrupa por Subtipo (1a · 1b · 1c · 1d). Subtipo vazio = "1 — subtipo
  a apurar": NA ≠ 0, não é 1a por falta de evidência (piso A.2c: norma lida + prova de
  operação).
- Aba 2 Parcial: agrupa por Subtipo (2a–2d); linhas repetidas do mesmo município (A.1.5,
  episódios) aparecem uma vez por subtipo.
- Aba 3 Encerradas, Regulamentada não implantada, Não TZ: seções próprias.
- Fonte das contagens: as abas, nunca a aba RESUMO.

USO  python gerar_indice_camadas.py [--gravar]   (simula por padrão; backup em _meta/_backups/)
"""
import argparse
import datetime
import os
import re
import shutil
import sys
import unicodedata

RAIZ = os.environ.get("TZ_VAULT") or os.getcwd()
FDIR = os.path.join(RAIZ, "04 - Análises", "Casos municipais", "Fichas por município")
SAIDA = os.path.join(RAIZ, "04 - Análises", "Casos municipais",
                     "Fichas por camada — índice auditado.md")
TIP = os.path.join(RAIZ, "03 - Dados", "_data", "casos por fonte",
                   "Tipologias TZ - consolidado.xlsx")
HOJE = datetime.date.today().strftime("%d/%m/%Y")
# v2.2 (07/10/2026): A.1.7 item 5 — eleitoral é piso (pós-2024) ou trajetória (pré-2024), em aba própria, fora das camadas
ABA_ELEI = "Eleitoral — piso e trajetória"

TIT = {
    "1a": "1a — universal · ausência de portão",
    "1b": "1b — universal · procedimento (cadastro aberto a qualquer usuário)",
    "1c": "1c — universal · pessoa por residência (com ou sem cadastro)",
    "1d": "1d — universal · prazo declarado ainda vigente",
    "1?": "1 — universal · subtipo a apurar (sem norma lida + prova de operação)",
    "2a": "2a — parcial · grupo, qualquer destino (renda, CadÚnico, idade fora do piso, deficiência, vínculo)",
    "2b": "2b — parcial · espaço/linha",
    "2c": "2c — parcial · tempo recorrente (dias da semana)",
    "2d": "2d — parcial · tempo pontual (eventos)",
    "2e": "2e — parcial · finalidade (escola, saúde, prova, entrevista; registro não exaustivo)",
    "2?": "2 — parcial · subtipo não registrado",
}
ORDEM = ["1a", "1b", "1c", "1d", "1?", "2a", "2b", "2c", "2d", "2e", "2?"]


def n(s):
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or ""))
                if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip().lower()


def carregar():
    import openpyxl
    wb = openpyxl.load_workbook(TIP, read_only=True, data_only=True)
    linhas = []  # (aba, mun, uf, subtipo, portao, regime_2d)
    for aba in wb.sheetnames:
        if aba.upper().startswith("RESUMO"):
            continue
        rr = list(wb[aba].iter_rows(values_only=True))
        if not rr:
            continue
        h = [str(x or "").strip() for x in rr[0]]
        if "Município" not in h or "UF" not in h:
            continue
        im, iu = h.index("Município"), h.index("UF")
        isub = next((i for i, x in enumerate(h) if x.startswith("Subtipo")), None)
        ip = h.index("Portão") if "Portão" in h else None
        ireg = next((i for i, x in enumerate(h) if x.startswith("Regime da 2d")), None)
        for r in rr[1:]:
            if not r or not r[im]:
                continue
            g = lambda i: str(r[i]).strip() if i is not None and i < len(r) and r[i] not in (None, "") else ""
            linhas.append((aba, str(r[im]).strip(), g(iu).upper(), g(isub), g(ip), g(ireg)))
    return linhas


def fichas_por_chave():
    out = {}
    for nome in os.listdir(FDIR):
        if not (nome.startswith("Ficha") and nome.endswith(".md")):
            continue
        t = open(os.path.join(FDIR, nome), encoding="utf-8").read(4000)
        mm = re.search(r"^municipio:\s*(.+)$", t, re.M)
        uu = re.search(r"^uf:\s*(.+)$", t, re.M)
        if mm and uu:
            out[(n(mm.group(1)), uu.group(1).strip().upper())] = nome[:-3]
    return out


def cod(aba, sub):
    s = n(sub)[:2]
    if aba == "1 Universal":
        return s if s in ("1a", "1b", "1c", "1d") else "1?"
    if aba == "2 Parcial":  # A.1.15 (08/10/2026): várias por linha, ex. "2b + 2c"
        cs = sorted(set(re.findall(r"2[a-e]", n(sub))))
        return cs or "2?"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args()
    if not os.path.isdir(FDIR):
        sys.exit(f"🔴 não achei as fichas em {FDIR}")
    linhas = carregar()
    fichas = fichas_por_chave()
    grupos = {c: {} for c in ORDEM}
    outras = {}
    regimes = {}
    for aba, mun, uf, sub, portao, reg in linhas:
        if aba == ABA_ELEI or (aba == "2 Parcial" and n(sub).startswith("2d") and reg and not reg.startswith("evento")):  # v2.2 (07/10/2026)
            chave = reg.split(" —")[0] if reg else "sem registro"
            regimes[chave] = regimes.get(chave, 0) + 1
        c = cod(aba, sub)
        k = (n(mun), uf)
        if c:
            for ci in (c if isinstance(c, list) else [c]):  # A.1.15
                grupos[ci].setdefault(k, (mun, uf, portao, fichas.get(k)))
        else:
            outras.setdefault(aba, {}).setdefault(k, (mun, uf, sub, portao, fichas.get(k)))
    n1 = sum(len(grupos[c]) for c in ORDEM if c.startswith("1"))
    n2 = len({k for c in ORDEM if c.startswith("2") for k in grupos[c]})
    n2l = sum(1 for x in linhas if x[0] == "2 Parcial")

    L = ["---", 'title: "Fichas por camada — índice auditado"', "tags:",
         "  - análise", "  - caso", "  - tarifa-zero", "  - índice",
         "publish: false", "created: 2026-09-17", "---", "",
         "# Fichas por camada — índice auditado", "",
         f"Gerado por `_meta/scripts/gerar_indice_camadas.py` (v2) das **abas** e da coluna "
         f"**Subtipo** de `Tipologias TZ - consolidado.xlsx`, na régua em vigor (A.1.4, "
         f"A.1.5 e A.1.6 de [[Regras de classificacao das reguas]]). Atualizado em {HOJE}. "
         "Não editar à mão: regerar.", "",
         "> [!note] Como ler",
         "> A aba 1 Universal tem **" + str(n1) + " municípios**. Subtipo vazio aparece como "
         "**1 — subtipo a apurar**: o caso está na universal, mas ainda não tem norma lida + "
         "prova de operação (piso A.2c). Ausência de medida não é medida de ausência — "
         "não é 1a por falta de evidência. A aba RESUMO da planilha não é usada.", "",
         "## Resumo", "",
         "| camada | municípios | com ficha |", "|---|---:|---:|"]
    for c in ORDEM:
        g = grupos[c]
        if not g and c.endswith("?") and c.startswith("2"):
            continue
        L.append(f"| **{TIT[c]}** | {len(g)} | {sum(1 for x in g.values() if x[3])} |")
    for chave in ("pré-2024", "pós-2024", "evento não eleitoral", "sem ano", "sem registro"):
        if regimes.get(chave):
            L.append(f"| ↳ eleitoral · {chave} (A.1.7, fora das camadas) | {regimes[chave]} linhas | — |")
    L.append(f"| **Aba 1 — total** | {n1} | — |")
    L.append(f"| **Aba 2 — total** ({n2l} linhas; um município pode ter mais de um subtipo) | {n2} | — |")
    for aba in ("3 Encerradas", "Regulamentada não implantada", "Não TZ", ABA_ELEI):
        g = outras.get(aba, {})
        L.append(f"| **{aba}** | {len(g)} | {sum(1 for x in g.values() if x[4])} |")
    L.append("")

    for c in ORDEM:
        g = grupos[c]
        if c.startswith("2"):
            continue  # aba 2 vai em bloco compacto abaixo
        L += [f"## {TIT[c]} ({len(g)})", ""]
        if not g:
            L += ["_Nenhum caso._", ""]
            continue
        for (mun, uf, portao, ficha) in sorted(g.values(), key=lambda x: (x[1], n(x[0]))):
            alvo = f"[[{ficha}]]" if ficha else f"**{mun} ({uf})** ⚠️ sem ficha"
            L.append(f"- {alvo} · portão: `{portao}`" if portao else f"- {alvo} · portão: não registrado")
        L.append("")

    L += ["## Aba 2 — parcial (fora da contagem universal)", "",
          "Listados só os municípios com ficha; os demais contam no resumo.", ""]
    for c in ORDEM:
        if not c.startswith("2"):
            continue
        g = grupos[c]
        if not g:
            continue
        com = sorted((x for x in g.values() if x[3]), key=lambda x: (x[1], n(x[0])))
        L.append(f"### {TIT[c]} ({len(g)} municípios; {len(com)} com ficha)")
        L.append("")
        L.append(" · ".join(f"[[{x[3]}]]" for x in com) if com else "_Nenhum com ficha._")
        L.append("")

    for aba, nota in (("3 Encerradas", "Subtipo = desenho enquanto vigeu; fim por desenho (prazo atingido) ≠ fim por trajetória (revogação sem prazo)."),
                      ("Regulamentada não implantada", "Regra A.1.6: há norma, a operação gratuita não começou. Fora das camadas e da contagem."),
                      ("Não TZ", "Excluídos do escopo por decisão registrada.")):
        g = outras.get(aba, {})
        L += [f"## {aba} ({len(g)})", "", nota, ""]
        for (mun, uf, sub, portao, ficha) in sorted(g.values(), key=lambda x: (x[1], n(x[0]))):
            alvo = f"[[{ficha}]]" if ficha else f"**{mun} ({uf})** ⚠️ sem ficha"
            L.append(f"- {alvo}" + (f" · subtipo antes: `{sub}`" if sub and aba == "3 Encerradas" else "")
                     + (f" · portão: `{portao}`" if portao else ""))
        L.append("")

    L += ["## Ligações",
          "- [[Regras de classificacao das reguas]] · [[Portão de acesso]] · "
          "[[Régua Descritiva]] · [[Tipologias de Tarifa Zero (4 camadas)]] · "
          "[[Tabela consolidada - Municípios com Tarifa Zero]] · [[Pendências]]", ""]

    novo = "\n".join(L)
    antigo = open(SAIDA, encoding="utf-8").read() if os.path.exists(SAIDA) else ""
    print("2d por regime (A.1.7):", regimes)
    print(f"aba 1: {n1} · aba 2: {n2} municípios ({n2l} linhas) · " +
          " · ".join(f"{k}: {len(v)}" for k, v in outras.items()))
    for c in ORDEM:
        print(f"   {len(grupos[c]):>4}  {c}")
    if novo == antigo:
        print("sem alteração (idempotente).")
        return
    if not a.gravar:
        print(f"{len(antigo)} → {len(novo)} caracteres. Nada foi escrito. Para aplicar: --gravar")
        return
    if antigo:
        bk = os.path.join(RAIZ, "_meta", "_backups",
                          "indice-camadas-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        os.makedirs(bk, exist_ok=True)
        shutil.copy2(SAIDA, bk)
        print(f"backup: {bk}")
    open(SAIDA, "w", encoding="utf-8", newline="\n").write(novo)
    print("✅ índice regerado")


if __name__ == "__main__":
    main()
