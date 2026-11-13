#!/usr/bin/env python3
"""cruzar_pdmu.py — cruza a obrigatoriedade e o levantamento de Plano de
Mobilidade Urbana (PDMU) com o `munic_plano_transp_2020` já presente no
Banco Municipal v3. Pendência aberta desde a Fase 3 (ver Auditoria de dados,
20/07/2026, item 2).

FONTES (`03 - Dados/_data/Planos de Mobilidade Urbana/`), ambas do MESMO
levantamento oficial — Ministério das Cidades / SEMOB / DEREG / CGPM,
atualizado jun-jul/2025 (rodapé da própria planilha; NÃO é dado da pesquisa,
é dado de fonte):
  A) `Obrigados_PlanosdeMobilidadeUrbana.xlsx` — relação de municípios
     OBRIGADOS a elaborar PDMU nos termos da Lei 12.587/2012 e da Lei
     14.000/2020 (por população e/ou por integrar RM/RIDE/Aglomeração
     Urbana). 1.910 municípios (as 2 últimas linhas são rodapé de fonte/data,
     descartadas).
  B) `planosdemobilidadeurbana.xlsx` — para TODOS os 5.570 municípios, se
     possuem PDMU, ano de elaboração, se foi aprovado em lei/ato normativo e
     qual o instrumento legal. Categorias de resposta: Sim / Não / Não
     respondeu / Não foi enviado ofício (as 2 últimas são as mesmas
     categorias "sem resposta" — o "envio de ofício" é uma etapa processual
     do próprio levantamento do MCID, não uma resposta do município).

O QUE ESTE SCRIPT FAZ:
  1. Carrega as duas planilhas, limpa rodapé, junta por `cod_ibge` (7 dígitos).
  2. Adiciona ao base_municipal_v3.csv: `pdmu_obrigado_2025`,
     `pdmu_obrigado_criterio_2025` (RM/RIDE/AU quando o critério for esse;
     em branco quando o critério for só população), `pdmu_possui_2025`,
     `pdmu_ano_elaboracao`, `pdmu_aprovado_lei_2025`,
     `pdmu_instrumento_legal_2025`.
  3. VALIDA contra `munic_plano_transp_2020` (MUNIC/IBGE, autodeclarado,
     pergunta mais genérica sobre "plano de transporte", não
     necessariamente o PDMU da Lei 12.587) — não assume que as duas fontes
     deveriam concordar (são levantamentos diferentes, com 5 anos de
     distância e perguntas diferentes); só descreve o grau de concordância e
     salva as discordâncias para inspeção, sem decidir qual está "certa".
  4. Não decide "canônica" nenhuma das duas — registra as duas variáveis
     lado a lado, com a ressalva de que medem coisas ligeiramente diferentes.

USO:  python cruzar_pdmu.py
Requer: pandas, openpyxl. Não acessa rede.
"""
import os, sys, traceback
import pandas as pd
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..")), "03 - Dados", "_data")
PDMU_DIR = os.path.join(V, "Planos de Mobilidade Urbana")
OUT = os.path.join(V, "Base Municipal v3")
BASE_CSV = os.path.join(OUT, "base_municipal_v3.csv")

F_OBRIGADOS = os.path.join(PDMU_DIR, "Obrigados_PlanosdeMobilidadeUrbana.xlsx")
F_POSSUI = os.path.join(PDMU_DIR, "planosdemobilidadeurbana.xlsx")


def c7(x):
    try:
        return str(int(float(x))).zfill(7)
    except Exception:
        return None


def log(msg):
    print(msg, flush=True)


def carrega_obrigados():
    log("=== A) Obrigados_PlanosdeMobilidadeUrbana.xlsx ===")
    d = pd.read_excel(F_OBRIGADOS, header=1)
    d = d.rename(columns={
        "Código do Município - IBGE": "cod_ibge_raw",
        "RIDE, RM, Aglomeração Urbana (AU) - IBGE 2024": "pdmu_obrigado_criterio_2025",
    })
    # descarta rodapé (linhas "Fonte: ..." / "Data de atualização: ...")
    d["cod_ibge"] = d["cod_ibge_raw"].astype(str).str.strip()
    d = d[d["cod_ibge"].str.len() == 7].copy()
    d["cod_ibge"] = d["cod_ibge"].map(c7)
    d["pdmu_obrigado_2025"] = 1
    d = d[["cod_ibge", "pdmu_obrigado_2025", "pdmu_obrigado_criterio_2025"]]
    log(f"  {len(d)} municípios obrigados (Lei 12.587/2012 + Lei 14.000/2020)")
    return d


def carrega_possui():
    log("=== B) planosdemobilidadeurbana.xlsx ===")
    d = pd.read_excel(F_POSSUI)
    d.columns = [c.strip() for c in d.columns]
    d = d.rename(columns={
        "código do município - IBGE": "cod_ibge_raw",
        "Possui Plano de Mobilidade Urbana": "pdmu_possui_2025",
        "Ano de elaboração": "pdmu_ano_elaboracao",
        "Aprovado em lei ou ato normativo": "pdmu_aprovado_lei_2025",
        "Instrumento Legal": "pdmu_instrumento_legal_2025",
    })
    d["cod_ibge"] = d["cod_ibge_raw"].astype(str).str.strip()
    d = d[d["cod_ibge"].str.len() == 7].copy()
    d["cod_ibge"] = d["cod_ibge"].map(c7)
    # normaliza "SIM"/"Sim" -> "Sim"
    d["pdmu_possui_2025"] = d["pdmu_possui_2025"].astype(str).str.strip().replace(
        {"SIM": "Sim", "nan": np.nan})
    cols = ["cod_ibge", "pdmu_possui_2025", "pdmu_ano_elaboracao",
            "pdmu_aprovado_lei_2025", "pdmu_instrumento_legal_2025"]
    d = d[cols]
    log(f"  {len(d)} municípios no levantamento | "
        f"distribuição: {d['pdmu_possui_2025'].value_counts(dropna=False).to_dict()}")
    return d


def valida_contra_munic2020(base):
    log("\n=== C) Validação contra munic_plano_transp_2020 (MUNIC 2020, IBGE) ===")
    sub = base[["cod_ibge", "nome_mun", "nome_uf", "munic_plano_transp_2020",
                "pdmu_possui_2025", "pdmu_obrigado_2025"]].copy()
    sub = sub[sub["pdmu_possui_2025"].notna() & sub["munic_plano_transp_2020"].notna()]
    sub["munic_2020_sim"] = sub["munic_plano_transp_2020"] == 1
    sub["mcid_2025_sim"] = sub["pdmu_possui_2025"] == "Sim"
    concorda = (sub["munic_2020_sim"] == sub["mcid_2025_sim"]).sum()
    total = len(sub)
    log(f"  {total} municípios com as duas respostas preenchidas (MUNIC 2020 e MCID 2025)")
    log(f"  concordância simples: {concorda}/{total} ({100*concorda/total:.1f}%)")
    log("  (não é medida de erro — os levantamentos são de anos e perguntas diferentes; "
        "MUNIC pergunta 'tem plano de transporte', MCID pergunta especificamente sobre o "
        "PDMU da Lei 12.587. Discordância pode refletir elaboração do plano ENTRE 2020 e 2025, "
        "não necessariamente erro de uma das fontes.)")

    discorda = sub[sub["munic_2020_sim"] != sub["mcid_2025_sim"]].copy()
    rel_path = os.path.join(OUT, "validacao_pdmu_munic2020_vs_mcid2025.csv")
    discorda.to_csv(rel_path, index=False)
    log(f"  {len(discorda)} discordâncias salvas em {rel_path} (para inspeção, não decide qual fonte usar)")

    # obrigados sem plano (achado potencialmente relevante p/ Cap 4/Cap 6 — não interpretado aqui)
    obrig = base[(base["pdmu_obrigado_2025"] == 1)]
    obrig_sem_plano = obrig[obrig["pdmu_possui_2025"].isin(["Não", "Nao"])]
    obrig_sem_resposta = obrig[obrig["pdmu_possui_2025"].isin(
        ["Não respondeu", "Nao respondeu", "Não foi enviado ofício", "Nao foi enviado oficio"])]
    log(f"\n  Dos {len(obrig)} municípios OBRIGADOS por lei: "
        f"{len(obrig_sem_plano)} declaram NÃO possuir PDMU, "
        f"{len(obrig_sem_resposta)} sem resposta/ofício não enviado "
        f"(não interpretado — só descrito; checar antes de usar como 'descumprimento').")


def main():
    log(f"_data em: {V}")
    if not os.path.exists(BASE_CSV):
        log(f"ERRO: {BASE_CSV} não encontrado."); sys.exit(1)
    if not (os.path.exists(F_OBRIGADOS) and os.path.exists(F_POSSUI)):
        log("ERRO: planilhas de PDMU não encontradas em "
            f"'{PDMU_DIR}'."); sys.exit(1)

    obrigados = carrega_obrigados()
    possui = carrega_possui()

    base = pd.read_csv(BASE_CSV, dtype={"cod_ibge": str}, low_memory=False)
    base["cod_ibge"] = base["cod_ibge"].map(c7)

    antes = base.shape[1]
    base = base.merge(obrigados, on="cod_ibge", how="left")
    base["pdmu_obrigado_2025"] = base["pdmu_obrigado_2025"].fillna(0).astype(int)
    base = base.merge(possui, on="cod_ibge", how="left")
    log(f"\nColunas adicionadas: {base.shape[1] - antes} "
        f"(pdmu_obrigado_2025, pdmu_obrigado_criterio_2025, pdmu_possui_2025, "
        f"pdmu_ano_elaboracao, pdmu_aprovado_lei_2025, pdmu_instrumento_legal_2025)")

    valida_contra_munic2020(base)

    # escrita atômica: grava em .tmp e só substitui o arquivo final depois de
    # completo (se o processo for interrompido no meio, o original fica
    # intacto) — ver incidente de 22/07/2026 documentado em corrige_nomes_tse_2024.py
    tmp = BASE_CSV + ".tmp"
    base.to_csv(tmp, index=False)
    os.replace(tmp, BASE_CSV)
    log(f"\nOK — base_municipal_v3.csv atualizado: {base.shape[0]} x {base.shape[1]}.")
    log("Lembrete: atualizar metadados.csv, Auditoria de dados e Mapa de Dados; "
        "rodar auditar_cofre.py.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
