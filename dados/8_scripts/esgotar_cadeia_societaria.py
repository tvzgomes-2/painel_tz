#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""esgotar_cadeia_societaria.py — continuação em loop do Passo 7 (24/07/2026).

PERGUNTA: o Passo 7 (`filtrar_segunda_camada_societaria.py`) achou os sócios
dos 1.769 sócios-PJ diretos das empresas de transporte (2ª camada). Mas e os
sócios DESSES sócios — e os sócios dos sócios dos sócios? Este script repete
a busca em RODADAS sucessivas, sempre avançando para os sócios-PJ novos
encontrados na rodada anterior, até não sobrar nenhum PJ novo para investigar
(a cadeia "se esgota" — chegou a pessoas físicas, empresas já conhecidas, ou
CNPJs fora da base) ou até um teto de segurança de rodadas.

NÃO REPROCESSA o que já foi feito: usa `socios_filtrado_6cnaes.csv` (rodada 0
-> rodada 1, já pronto) e `socios_segunda_camada.csv` (rodada 1 -> rodada 2,
já pronto pelo Passo 7) como ponto de partida. Só escaneia os dumps brutos a
partir da rodada 2 em diante (os sócios-PJ que ainda não têm cadastro/sócios
próprios levantados).

CAMADAS (rodada = distância até a empresa de transporte original):
  rodada 0 = as próprias empresas de transporte (6 CNAEs)
  rodada 1 = sócios-PJ diretos delas (1.769 — já levantado, Passo 7)
  rodada 2 = sócios-PJ dos sócios da rodada 1 (já apurados em
             socios_segunda_camada.csv — este script busca o CADASTRO deles
             e os SEUS PRÓPRIOS sócios, ambos ainda não levantados)
  rodada 3, 4, ... = e assim por diante, até esgotar.

CICLOS: se um sócio-PJ "novo" já é conhecido (é uma das próprias empresas de
transporte, ou um sócio-PJ de rodada anterior), o vínculo é registrado
normalmente (mostra a ligação/ciclo) mas ele NÃO é reprocessado de novo —
evita loop infinito.

SAÍDAS (em `filtrados (6 CNAEs transporte, 24-07-2026)/cadeia_societaria/`):
  - `cadeia_cadastro.csv` — cadastro (razão social, natureza jurídica, porte,
    CNAE, situação, município) de cada CNPJ descoberto a partir da rodada 2,
    com a coluna `rodada` = em que rodada ele foi descoberto.
  - `cadeia_vinculos.csv` — todos os vínculos societários coletados a partir
    da rodada 2 (sócio de cada CNPJ investigado), com `rodada_do_dono` = a
    rodada do CNPJ dono (a empresa/holding cujo sócio está naquela linha).
  - `estado_cadeia.pkl` — checkpoint (visitados, fronteira, rodada atual) —
    permite retomar se o script travar ou for interrompido.

USO:
    python "C:\Users\HOME\OneDrive\doutorado\_meta\scripts\esgotar_cadeia_societaria.py"

Resumível: rode de novo a qualquer momento — retoma da última rodada
concluída. Para forçar mais rodadas além do teto de segurança, aumente
MAX_RODADAS abaixo e rode de novo.

⚠️ CORREÇÃO (25/07/2026): `cnae_fiscal_principal` estava lendo a coluna
errada do arquivo ESTABELECIMENTOS (campos[10] = DATA DE INÍCIO ATIVIDADE,
não o CNAE — conferido contra o leiaute oficial da Receita Federal,
`cnpj-metadados (dicionário).pdf`). Corrigido para campos[11]. Isso só
afeta a coluna `cnae_fiscal_principal` de `cadeia_cadastro.csv` (rodadas
2-5) — razão social, natureza jurídica, situação, UF e município nunca
estiveram errados. Nenhuma afirmação já registrada no cofre usou o CNAE
das rodadas 2-5, então não há achado a corrigir — só o dado em si, se for
usado dali pra frente.
"""
import csv
import glob
import os
import pickle

RAIZ = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\CNPJ"
PASTA_BRUTOS = os.path.join(RAIZ, "Receita Federal - dados brutos")
PASTA_SAIDA = os.path.join(RAIZ, "filtrados (6 CNAEs transporte, 24-07-2026)")
PASTA_CADEIA = os.path.join(PASTA_SAIDA, "cadeia_societaria")
ESTADO_PATH = os.path.join(PASTA_CADEIA, "estado_cadeia.pkl")

MAX_RODADAS = 15  # teto de segurança — se atingir sem esgotar, aumentar e rodar de novo


def log(msg):
    print(msg, flush=True)


def salva_estado(estado):
    tmp = ESTADO_PATH + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(estado, f)
    os.replace(tmp, ESTADO_PATH)


def constroi_estado_inicial():
    """Rodada 0 (empresas de transporte) e rodada 1 (seus sócios-PJ diretos) já
    estão prontas de rodadas anteriores — carrega sem re-escanear dumps brutos.
    A fronteira inicial para ESTE script é a rodada 2: os sócios-PJ encontrados
    dentro de `socios_segunda_camada.csv` (sócios dos sócios-PJ de rodada 1)."""
    os.makedirs(PASTA_CADEIA, exist_ok=True)

    rodada_de = {}
    log("Carregando rodada 0 (empresas de transporte, 6 CNAEs)...")
    with open(os.path.join(PASTA_SAIDA, "socios_filtrado_6cnaes.csv"), encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rodada_de.setdefault(row["cnpj_basico"].zfill(8), 0)
    log(f"  {sum(1 for v in rodada_de.values() if v == 0):,} CNPJs BASE em rodada 0.")

    log("Carregando rodada 1 (sócios-PJ diretos, já levantados no Passo 7)...")
    with open(os.path.join(PASTA_SAIDA, "socios_pj_completo.csv"), encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            cnpj = row["cnpj_basico_socio_pj"].strip().zfill(8)
            rodada_de.setdefault(cnpj, 1)
    log(f"  {sum(1 for v in rodada_de.values() if v == 1):,} CNPJs BASE em rodada 1.")

    log("Lendo sócios da rodada 1 (socios_segunda_camada.csv) para achar a fronteira da rodada 2...")
    fronteira_r2 = set()
    with open(os.path.join(PASTA_SAIDA, "socios_segunda_camada.csv"), encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["tipo_socio"] != "PJ":
                continue
            cnpj = row["cnpj_cpf_socio"].strip()[:8].zfill(8)
            if cnpj not in rodada_de:
                fronteira_r2.add(cnpj)
    log(f"  {len(fronteira_r2):,} sócios-PJ novos (candidatos à rodada 2).")

    estado = {
        "rodada_de": rodada_de,          # cnpj_basico -> rodada em que foi descoberto
        "fronteira": fronteira_r2,        # CNPJs a investigar na PRÓXIMA rodada a rodar
        "rodada_atual": 1,                # última rodada já com cadastro+sócios levantados
        "cadastro_arquivos": [],          # lista de arquivos parciais de cadastro por rodada
        "vinculos_arquivos": [],          # lista de arquivos parciais de vínculos por rodada
    }
    return estado


def escaneia_rodada(cnpjs_alvo, rodada, pasta_rodada):
    """Escaneia os 3 conjuntos de dumps brutos (Estabelecimentos, empresas, Sócio)
    filtrando por cnpjs_alvo. Devolve (cadastro: list[dict], vinculos: list[dict])."""
    os.makedirs(pasta_rodada, exist_ok=True)
    cadastro_path = os.path.join(pasta_rodada, "cadastro.csv")
    vinculos_path = os.path.join(pasta_rodada, "vinculos.csv")

    if os.path.exists(cadastro_path) and os.path.exists(vinculos_path):
        log(f"  Rodada {rodada}: já escaneada — reaproveitando {pasta_rodada}")
    else:
        # --- ESTABELECIMENTOS (matriz: razão via nome_fantasia não é razão social;
        #     razão social vem do arquivo empresas — aqui só CNAE/situação/município) ---
        cadastro_estab = {}
        partes = sorted(glob.glob(os.path.join(PASTA_BRUTOS, "ESTABELECIMENTOS*.csv")))
        log(f"  [Rodada {rodada}] Estabelecimentos: {len(partes)} partes, {len(cnpjs_alvo):,} CNPJs-alvo...")
        for caminho in partes:
            with open(caminho, "r", encoding="latin1", errors="replace", newline="") as fin:
                leitor = csv.reader(fin, delimiter=";", quotechar='"')
                for campos in leitor:
                    if len(campos) < 21:
                        continue
                    cnpj = campos[0].strip()
                    if cnpj not in cnpjs_alvo or campos[3].strip() != "1":  # só matriz
                        continue
                    cadastro_estab[cnpj] = {
                        "situacao_cadastral": campos[5], "cnae_fiscal_principal": campos[11],
                        "uf": campos[19], "municipio_codigo_rfb": campos[20],
                    }
        log(f"    {len(cadastro_estab):,} matrizes encontradas.")

        # --- empresas (razão social, natureza jurídica, porte, capital) ---
        cadastro_emp = {}
        partes = sorted(glob.glob(os.path.join(PASTA_BRUTOS, "empresas*.csv")))
        log(f"  [Rodada {rodada}] Empresas: {len(partes)} partes...")
        for caminho in partes:
            with open(caminho, "r", encoding="latin1", errors="replace", newline="") as fin:
                leitor = csv.reader(fin, delimiter=";", quotechar='"')
                for campos in leitor:
                    if len(campos) < 6:
                        continue
                    cnpj = campos[0].strip()
                    if cnpj not in cnpjs_alvo:
                        continue
                    cadastro_emp[cnpj] = {
                        "razao_social": campos[1], "natureza_juridica": campos[2],
                        "capital_social": campos[4], "porte_empresa": campos[5],
                    }
        log(f"    {len(cadastro_emp):,} empresas encontradas.")

        cadastro = []
        for cnpj in cnpjs_alvo:
            linha = {"cnpj_basico": cnpj, "rodada": rodada}
            linha.update(cadastro_emp.get(cnpj, {}))
            linha.update(cadastro_estab.get(cnpj, {}))
            cadastro.append(linha)

        # --- SOCIO (sócios de cada CNPJ-alvo) ---
        vinculos = []
        partes = sorted(glob.glob(os.path.join(PASTA_BRUTOS, "SOCIO*.csv")))
        log(f"  [Rodada {rodada}] Sócios: {len(partes)} partes...")
        for caminho in partes:
            with open(caminho, "r", encoding="latin1", errors="replace", newline="") as fin:
                leitor = csv.reader(fin, delimiter=";", quotechar='"')
                for campos in leitor:
                    if len(campos) < 11:
                        continue
                    cnpj = campos[0].strip()
                    if cnpj not in cnpjs_alvo:
                        continue
                    tipo = "PJ" if campos[1].strip() == "1" else ("PF" if campos[1].strip() == "2" else "estrangeiro")
                    vinculos.append({
                        "cnpj_basico_dono": cnpj, "tipo_socio": tipo,
                        "nome_socio_ou_razao_social": campos[2], "cnpj_cpf_socio": campos[3],
                        "qualificacao_socio": campos[4], "data_entrada_sociedade": campos[5],
                        "rodada_do_dono": rodada,
                    })
        log(f"    {len(vinculos):,} vínculos encontrados.")

        with open(cadastro_path, "w", encoding="utf-8-sig", newline="") as f:
            campos_cad = ["cnpj_basico", "rodada", "razao_social", "natureza_juridica",
                          "capital_social", "porte_empresa", "situacao_cadastral",
                          "cnae_fiscal_principal", "uf", "municipio_codigo_rfb"]
            w = csv.DictWriter(f, fieldnames=campos_cad)
            w.writeheader()
            w.writerows(cadastro)
        with open(vinculos_path, "w", encoding="utf-8-sig", newline="") as f:
            campos_vinc = ["cnpj_basico_dono", "tipo_socio", "nome_socio_ou_razao_social",
                           "cnpj_cpf_socio", "qualificacao_socio", "data_entrada_sociedade",
                           "rodada_do_dono"]
            w = csv.DictWriter(f, fieldnames=campos_vinc)
            w.writeheader()
            w.writerows(vinculos)

    with open(cadastro_path, encoding="utf-8-sig", newline="") as f:
        cadastro = list(csv.DictReader(f))
    with open(vinculos_path, encoding="utf-8-sig", newline="") as f:
        vinculos = list(csv.DictReader(f))
    return cadastro, vinculos


def consolida_saida_final(estado):
    log("\nConsolidando cadeia_cadastro.csv e cadeia_vinculos.csv finais...")
    cad_final = os.path.join(PASTA_CADEIA, "cadeia_cadastro.csv")
    vinc_final = os.path.join(PASTA_CADEIA, "cadeia_vinculos.csv")
    tmp_cad, tmp_vinc = cad_final + ".tmp", vinc_final + ".tmp"

    total_cad = total_vinc = 0
    with open(tmp_cad, "w", encoding="utf-8-sig", newline="") as fout:
        w = None
        for pasta in estado["cadastro_arquivos"]:
            with open(os.path.join(pasta, "cadastro.csv"), encoding="utf-8-sig", newline="") as fin:
                r = csv.DictReader(fin)
                if w is None:
                    w = csv.DictWriter(fout, fieldnames=r.fieldnames)
                    w.writeheader()
                for row in r:
                    w.writerow(row)
                    total_cad += 1
    os.replace(tmp_cad, cad_final)

    with open(tmp_vinc, "w", encoding="utf-8-sig", newline="") as fout:
        w = None
        for pasta in estado["vinculos_arquivos"]:
            with open(os.path.join(pasta, "vinculos.csv"), encoding="utf-8-sig", newline="") as fin:
                r = csv.DictReader(fin)
                if w is None:
                    w = csv.DictWriter(fout, fieldnames=r.fieldnames)
                    w.writeheader()
                for row in r:
                    w.writerow(row)
                    total_vinc += 1
    os.replace(tmp_vinc, vinc_final)

    log(f"  {total_cad:,} linhas de cadastro -> {cad_final}")
    log(f"  {total_vinc:,} linhas de vínculo -> {vinc_final}")


def main():
    if os.path.exists(ESTADO_PATH):
        log(f"Retomando checkpoint existente: {ESTADO_PATH}")
        with open(ESTADO_PATH, "rb") as f:
            estado = pickle.load(f)
    else:
        estado = constroi_estado_inicial()
        salva_estado(estado)

    while estado["fronteira"] and estado["rodada_atual"] < MAX_RODADAS:
        rodada = estado["rodada_atual"] + 1
        alvo = estado["fronteira"]
        log(f"\n{'='*70}\nRODADA {rodada} — investigando {len(alvo):,} CNPJs novos\n{'='*70}")

        pasta_rodada = os.path.join(PASTA_CADEIA, f"rodada_{rodada:02d}")
        cadastro, vinculos = escaneia_rodada(alvo, rodada, pasta_rodada)

        for cnpj in alvo:
            estado["rodada_de"].setdefault(cnpj, rodada)
        estado["cadastro_arquivos"].append(pasta_rodada)
        estado["vinculos_arquivos"].append(pasta_rodada)

        nova_fronteira = set()
        for v in vinculos:
            if v["tipo_socio"] != "PJ":
                continue
            cnpj_socio = v["cnpj_cpf_socio"].strip()[:8].zfill(8)
            if cnpj_socio not in estado["rodada_de"] and cnpj_socio not in alvo:
                nova_fronteira.add(cnpj_socio)

        log(f"\nRodada {rodada} concluída: {len(cadastro):,} cadastros, {len(vinculos):,} vínculos, "
            f"{len(nova_fronteira):,} sócios-PJ novos para a próxima rodada.")

        estado["fronteira"] = nova_fronteira
        estado["rodada_atual"] = rodada
        salva_estado(estado)

    if not estado["fronteira"]:
        log(f"\n✅ Cadeia esgotada na rodada {estado['rodada_atual']} — nenhum sócio-PJ novo encontrado.")
    else:
        log(f"\n⚠️ Teto de segurança ({MAX_RODADAS} rodadas) atingido, ainda restam "
            f"{len(estado['fronteira']):,} CNPJs na fronteira. Aumente MAX_RODADAS no script e rode de novo "
            f"para continuar de onde parou (o checkpoint já está salvo).")

    consolida_saida_final(estado)

    log("\nResumo por rodada (nº de CNPJs descobertos em cada uma):")
    from collections import Counter
    c = Counter(estado["rodada_de"].values())
    for r in sorted(c):
        log(f"  rodada {r}: {c[r]:,} CNPJs")

    log("\nCole a saída deste script aqui para eu montar o grafo com todas as rodadas.")


if __name__ == "__main__":
    main()
