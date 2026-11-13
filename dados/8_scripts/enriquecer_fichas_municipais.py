#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""enriquecer_fichas_municipais.py — insere, em cada ficha de município
(`04 - Análises/Casos municipais/Fichas por município/*.md`), uma seção
"## Dados quantitativos" com as variáveis de emprego/financiamento
integradas nesta rodada (23-24/07/2026): RAIS 2022 (vínculos formais),
SIDRA 2024 (salário médio), Censo 2022 (informalidade ampla) e a
simulação CTP/CTPU (base tributável + arrecadação simulada). Para os
municípios que já têm custo real conhecido (`serie_ctp_vs_custo_real.csv`,
21 municípios), acrescenta também a comparação arrecadação×custo.

NÃO mexe nas seções 1-5 nem na numeração (o exportador `exportar_anexo.py`
lê especificamente "## 1.", "## 2.", "## 3.", "## 5." por regex — uma seção
SEM número, inserida antes de "## Ligações", não interfere nisso).
IDEMPOTENTE: se a ficha já tem "## Dados quantitativos", a seção antiga é
substituída (não duplicada) — pode rodar de novo com segurança se o banco
mudar.

BRIDGE: usa o frontmatter `municipio:`/`uf:` de cada ficha (já é a grafia
canônica do autor) e casa contra `nome_mun`/`uf` do banco via
UF+nome-normalizado (mesmo padrão de bridge usado em todo o resto do
cofre). Fichas sem match ficam de fora e são listadas no resumo final —
NÃO adivinha correspondência.

USO: python enriquecer_fichas_municipais.py"""
import datetime
import glob
import os
import re
import shutil
import unicodedata

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(HERE, "..", ".."))
V = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..")), "03 - Dados", "_data")
OUT = os.path.join(V, "Base Municipal v3")
BASE_CSV = os.path.join(OUT, "base_municipal_v3.csv")
CUSTO_REAL_CSV = os.path.join(OUT, "serie_ctp_vs_custo_real.csv")

ANALISES = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..")), "04 - Análises")
FICHAS_DIR = os.path.join(ANALISES, "Casos municipais", "Fichas por município")

SECAO_INICIO = "## Dados quantitativos"

# variantes de grafia entre o frontmatter das fichas e nome_mun do banco
# (único candidato por UF, conferido antes de codificar) — mesmo padrão de
# correção usado em todo o resto do cofre (TSE, POLO/RAIS etc.)
CORRECOES_NOME_FICHA = {
    "SP|ARTHURNOGUEIRA": "SP|ARTURNOGUEIRA",  # ficha usa "Arthur" (com h); IBGE/banco usa "Artur"
    "SP|EMBUDASARTES": "SP|EMBU",  # ficha usa o nome oficial pós-2011; banco guarda a grafia anterior "Embu"
}


def log(msg):
    print(msg, flush=True)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def c7(x):
    try:
        return str(int(float(x))).zfill(7)
    except Exception:
        return None


def fmt_num(v, casas=0):
    if pd.isna(v):
        return "—"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(v, casas=1):
    if pd.isna(v):
        return "—"
    return f"{v:.{casas}f}%".replace(".", ",")


def fmt_reais(v):
    if pd.isna(v):
        return "—"
    return f"R$ {v:,.0f}".replace(",", ".")


def montar_secao(row, custo_row):
    linhas = [SECAO_INICIO + " (Banco Municipal v3, jul/2026)"]
    linhas.append(
        f"- **Emprego formal (RAIS 2022):** {fmt_num(row.get('vinculos_formais_rais_2022'))} vínculos formais."
    )
    linhas.append(
        f"- **Salário médio mensal (SIDRA 2024):** {fmt_reais(row.get('salario_medio_mensal_r'))}."
    )
    if pd.notna(row.get("taxa_informalidade_ampla_censo2022_pct")):
        linhas.append(
            f"- **Informalidade (Censo 2022, definição ampla):** "
            f"{fmt_pct(row.get('taxa_informalidade_ampla_censo2022_pct'))} dos ocupados "
            f"({fmt_num(row.get('informais_ampla_censo2022'))} de {fmt_num(row.get('ocupados_total_censo2022'))} pessoas)."
        )
    arrec_ctp_ano = row.get("arrecadacao_ctp_2pct")
    arrec_ctpu_ano = row.get("arrecadacao_ctpu_2pct")
    if pd.notna(arrec_ctp_ano):
        arrec_ctp_ano = arrec_ctp_ano * 12
    if pd.notna(arrec_ctpu_ano):
        arrec_ctpu_ano = arrec_ctpu_ano * 12
    linhas.append(
        f"- **Simulação de financiamento via contribuição sobre a folha (CTP/CTPU, alíquota de referência 2%):** "
        f"base tributável CTP = {fmt_num(row.get('base_tributavel_ctp'))} vínculos, "
        f"CTPU = {fmt_num(row.get('base_tributavel_ctpu'))} vínculos; "
        f"arrecadação simulada anual — CTP {fmt_reais(arrec_ctp_ano)}, CTPU {fmt_reais(arrec_ctpu_ano)}."
    )
    if custo_row is not None:
        linhas.append(
            f"- **Comparação com o custo real do sistema ({custo_row.get('fonte_custo', 'NTU')}):** "
            f"custo anual conhecido {fmt_reais(custo_row.get('custo_anual_r'))}; "
            f"alíquota CTPU necessária para cobrir 100% do custo = "
            f"{fmt_pct(custo_row.get('aliquota_necessaria_ctpu_100pct')*100 if pd.notna(custo_row.get('aliquota_necessaria_ctpu_100pct')) else None)}; "
            f"cobertura a 2% = {fmt_pct(custo_row.get('cobertura_ctpu_2pct_anual')*100 if pd.notna(custo_row.get('cobertura_ctpu_2pct_anual')) else None)}."
        )
    linhas.append(
        "- ⚠️ Ressalvas: mistura de anos-safra (RAIS 2022 / SIDRA salário 2024 / Censo 2022); "
        "\"folha\" aproximada por vínculos × salário médio do município, não soma de salários reais; "
        "informalidade é dado AMOSTRAL preliminar do Censo 2022. Ver "
        "[[Análise - Simulação CTP-CTPU (contribuição sobre a folha)]]."
    )
    return "\n".join(linhas)


_BACKUP_DIR = None  # criado sob demanda no 1º arquivo realmente gravado


def _backup_antes_de_gravar(path):
    """Copia o conteúdo atual de `path` para _meta/_backups/ antes de sobrescrever,
    seguindo o mesmo padrão dos demais scripts enriquecer_*.py."""
    global _BACKUP_DIR
    if _BACKUP_DIR is None:
        _BACKUP_DIR = os.path.join(
            RAIZ, "_meta", "_backups",
            "fichas-municipais-" + datetime.datetime.now().strftime("%Y-%m-%d_%H%M"),
        )
        os.makedirs(_BACKUP_DIR, exist_ok=True)
    shutil.copy2(path, os.path.join(_BACKUP_DIR, os.path.basename(path)))


def atualizar_ficha(path, secao_nova):
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()

    bloco = re.search(r"^## Dados quantitativos.*?(?=^## |\Z)", txt, re.S | re.M)
    if bloco:
        txt_novo = txt[:bloco.start()] + secao_nova + "\n\n" + txt[bloco.end():]
    else:
        marcador = "## Ligações"
        if marcador not in txt:
            return False, "sem seção '## Ligações' para ancorar a inserção"
        txt_novo = txt.replace(marcador, secao_nova + "\n\n" + marcador, 1)

    _backup_antes_de_gravar(path)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt_novo)
    return True, None


def main():
    base = pd.read_csv(BASE_CSV, dtype={"cod_ibge": str}, low_memory=False)
    base["cod_ibge"] = base["cod_ibge"].map(c7)
    base["chave"] = base["uf"].str.upper().str.strip() + "|" + base["nome_mun"].map(norm)

    custo = None
    if os.path.exists(CUSTO_REAL_CSV):
        custo = pd.read_csv(CUSTO_REAL_CSV, dtype={"cod_ibge": str}, low_memory=False)
        custo["cod_ibge"] = custo["cod_ibge"].map(c7)
        log(f"serie_ctp_vs_custo_real.csv: {len(custo)} municípios com custo real conhecido")

    arquivos = sorted(glob.glob(os.path.join(FICHAS_DIR, "Ficha - *.md")))
    log(f"{len(arquivos)} fichas encontradas em {FICHAS_DIR}")

    ok, sem_match, erro = 0, [], []
    for path in arquivos:
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read()
        m_muni = re.search(r"^municipio:\s*(.+)$", txt, re.M)
        m_uf = re.search(r"^uf:\s*(.+)$", txt, re.M)
        if not (m_muni and m_uf):
            erro.append((os.path.basename(path), "sem frontmatter municipio/uf"))
            continue
        chave = m_uf.group(1).strip().upper() + "|" + norm(m_muni.group(1).strip())
        chave = CORRECOES_NOME_FICHA.get(chave, chave)
        linha = base[base["chave"] == chave]
        if linha.empty:
            sem_match.append(f"{m_muni.group(1).strip()} ({m_uf.group(1).strip()})")
            continue
        row = linha.iloc[0]
        custo_row = None
        if custo is not None:
            cl = custo[custo["cod_ibge"] == row["cod_ibge"]]
            if not cl.empty:
                custo_row = cl.iloc[0]

        secao = montar_secao(row, custo_row)
        sucesso, msg = atualizar_ficha(path, secao)
        if sucesso:
            ok += 1
        else:
            erro.append((os.path.basename(path), msg))

    log(f"\n=== Resultado ===")
    log(f"Fichas atualizadas: {ok}/{len(arquivos)}")
    if sem_match:
        log(f"\nSem correspondência no banco ({len(sem_match)}):")
        for m in sem_match:
            log(f"  - {m}")
    if erro:
        log(f"\nErros ({len(erro)}):")
        for nome, msg in erro:
            log(f"  - {nome}: {msg}")


if __name__ == "__main__":
    main()
