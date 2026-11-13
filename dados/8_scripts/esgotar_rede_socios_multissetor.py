#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""esgotar_rede_socios_multissetor.py — novo loop, sem filtro de CNAE (24/07/2026).

PERGUNTA (a pedido do autor): para as empresas de transporte que já sabemos
estarem em componentes de 4+ empresas conectadas (sócio em comum), quais
OUTRAS empresas — de QUALQUER setor/CNAE, não só transporte — os sócios delas
também possuem? E quem são OS SÓCIOS dessas outras empresas? Repete em rodadas
sucessivas (sócio -> outras empresas -> sócios dessas empresas -> ...) até 5
rodadas.

DIFERENÇA em relação a `esgotar_cadeia_societaria.py`:
  - Aquele script seguia só a cadeia de sócios-PJ (holdings) DENTRO do universo
    de 6 CNAEs de transporte já filtrado.
  - Este script vira a busca ao contrário e tira o filtro de CNAE: para cada
    sócio (pessoa física OU jurídica) das empresas-semente, varre o dump bruto
    de Sócios da Receita Federal INTEIRO (todas as ~50 milhões de linhas, todos
    os setores) atrás de QUALQUER outra empresa onde aquele mesmo sócio apareça
    — pode ser imobiliária, agropecuária, holding, o que for.

SEMENTE: as 4.129 empresas de transporte que estão em componentes com MAIS DE
3 empresas conectadas por sócio comum (`rede_empresas_6cnaes_componentes.csv`,
coluna `tamanho_componente` > 3) — 662 componentes. Os sócios delas (7.194
identidades distintas, já em `socios_filtrado_6cnaes.csv`) são o ponto de
partida — não precisam ser re-escaneados.

RODADA (1 rodada = 1 ciclo completo):
  1. Busca REVERSA: para os sócios da fronteira atual, varre o dump de Sócios
     inteiro (sem filtro de CNAE) e acha toda empresa (`cnpj_basico`) onde esse
     sócio aparece como sócio — "outras empresas que eles possuem".
  2. Para as empresas NOVAS encontradas no passo 1 (fora do universo já
     conhecido), busca o cadastro delas (razão social, CNAE, natureza jurídica,
     situação, UF/município) e os PRÓPRIOS sócios delas — "quais sócios eles
     têm".
  3. Os sócios novos encontrados no passo 2 viram a fronteira da PRÓXIMA
     rodada.

IDENTIDADE DE SÓCIO: sempre nome + CPF/CNPJ mascarado (não só o identificador
mascarado sozinho, que colide — mesma convenção já usada no resto do cofre).

CICLOS: se uma "empresa nova" já é conhecida (uma das 67.138 do universo de
transporte, ou já descoberta em rodada anterior), o vínculo é registrado mas a
empresa NÃO é reprocessada de novo. Mesma lógica para sócios repetidos.

⚠️ RISCO DE EXPLOSÃO (leia antes de rodar): como não há mais filtro de CNAE,
um sócio muito conectado pode aparecer em dezenas ou centenas de empresas de
setores completamente diferentes (imobiliárias, holdings pessoais etc.). O
script REGISTRA um aviso para qualquer sócio com mais de `AVISO_GRAU_ALTO`
empresas encontradas (não filtra, só avisa) — revise esses casos com calma
antes de interpretar (pode ser sócio genuinamente múltiplo OU colisão de nome
comum apesar do CPF/CNPJ mascarado).

SAÍDAS (em `filtrados (6 CNAEs transporte, 24-07-2026)/rede_socios_multissetor/`):
  - `multissetor_empresas.csv` — cadastro de cada empresa nova (qualquer CNAE),
    com a `rodada` de descoberta e o CNAE principal (para depois analisar em
    que outros setores os sócios do transporte diversificam).
  - `multissetor_vinculos.csv` — todos os vínculos coletados (tanto os da
    busca reversa quanto os das empresas novas), com `rodada`.
  - `estado_multissetor.pkl` — checkpoint, resumível.

USO:
    python "C:\Users\HOME\OneDrive\doutorado\_meta\scripts\esgotar_rede_socios_multissetor.py"

Resumível: rode de novo a qualquer momento — retoma da última rodada
concluída. MAX_RODADAS = 5 por pedido do autor; para continuar além disso,
aumente a constante abaixo e rode de novo.

⚠️⚠️ CORREÇÃO IMPORTANTE (25/07/2026) — 2 bugs achados na 1ª rodada real:
  1. `cnae_fiscal_principal` lia a coluna errada do ESTABELECIMENTOS
     (campos[10] = DATA DE INÍCIO ATIVIDADE, não o CNAE — conferido contra
     o leiaute oficial da Receita Federal). Corrigido para campos[11].
  2. SEM filtro de qualificação de sócio, a 1ª rodada real explodiu para
     882 mil empresas em 5 rodadas SEM convergir — os "hubs" de maior grau
     eram administradores profissionais (despachantes, contadores) ligando
     dezenas/centenas de empresas de setores sem nenhuma relação com
     transporte (MRV Engenharia, Cyrela, Rossi Residencial, Oi S.A.,
     clínicas médicas...). Adicionado o mesmo filtro de qualificação-equity
     já usado no recorte núcleo limpo (`QUALIF_EQUITY`, Tabela IV da RFB) —
     agora só conta como "sócio" quem tem participação societária real,
     não administrador/diretor/presidente sem equity, nas DUAS pontas da
     busca (reversa E direta).
  **Se você já rodou a versão anterior:** apague a pasta
  `rede_socios_multissetor/` inteira (estado + rodadas + CSVs finais) antes
  de rodar de novo — o checkpoint antigo tem sócios não-equity na fronteira
  e não dá para simplesmente continuar de onde parou.
"""
import csv
import glob
import os
import pickle

RAIZ = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\CNPJ"
PASTA_BRUTOS = os.path.join(RAIZ, "Receita Federal - dados brutos")
PASTA_SAIDA = os.path.join(RAIZ, "filtrados (6 CNAEs transporte, 24-07-2026)")
PASTA_MULTI = os.path.join(PASTA_SAIDA, "rede_socios_multissetor")
ESTADO_PATH = os.path.join(PASTA_MULTI, "estado_multissetor.pkl")

MIN_TAMANHO_COMPONENTE = 3   # "acima de 3 empresas conectadas" => > 3
MAX_RODADAS = 5              # pedido do autor
AVISO_GRAU_ALTO = 80         # só loga aviso, não filtra

# Qualificações de sócio que representam participação societária real
# (Tabela IV da Receita Federal). Fora dessa lista: Administrador (05),
# Conselheiro (08), Diretor (10), Presidente (16), Cotas em Tesouraria (63)
# e afins — papéis de gestão/formais, sem equity. Ver `pesquisa dos
# CNPJs.md` § "Remapeamento a partir da base limpa" para a fonte e a
# justificativa. CORREÇÃO (25/07/2026): a 1ª rodada deste script (sem esse
# filtro) explodiu para 882 mil empresas em 5 rodadas sem convergir — os
# maiores "hubs" eram administradores profissionais/despachantes ligando
# empresas de setores sem nenhuma relação (MRV, Cyrela, Rossi Residencial,
# Oi S.A., clínicas médicas...), não sócios reais do setor de transporte.
QUALIF_EQUITY = {"22", "49", "20", "30", "37", "38", "29", "31", "65", "52"}


def log(msg):
    print(msg, flush=True)


def salva_estado(estado):
    tmp = ESTADO_PATH + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(estado, f)
    os.replace(tmp, ESTADO_PATH)


def constroi_estado_inicial():
    os.makedirs(PASTA_MULTI, exist_ok=True)

    log(f"Carregando componentes com mais de {MIN_TAMANHO_COMPONENTE} empresas conectadas...")
    empresas_semente = set()
    componentes = set()
    with open(os.path.join(PASTA_SAIDA, "rede_empresas_6cnaes_componentes.csv"), encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if int(row["tamanho_componente"]) > MIN_TAMANHO_COMPONENTE:
                cnpj = row["cnpj_basico"].strip().zfill(8)
                empresas_semente.add(cnpj)
                componentes.add(row["componente_id"])
    log(f"  {len(empresas_semente):,} empresas-semente em {len(componentes):,} componentes.")

    log("Carregando universo completo de 6 CNAEs (para não redescobrir o que já conhecemos)...")
    empresas_conhecidas = set()
    with open(os.path.join(PASTA_SAIDA, "socios_filtrado_6cnaes.csv"), encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            empresas_conhecidas.add(row["cnpj_basico"].strip().zfill(8))
    log(f"  {len(empresas_conhecidas):,} empresas já conhecidas (universo de transporte).")

    log("Extraindo sócios-equity das empresas-semente (fronteira inicial de sócios, rodada 1)...")
    fronteira_socios = set()
    socios_conhecidos = set()
    excluidos_qualif = 0
    with open(os.path.join(PASTA_SAIDA, "socios_filtrado_6cnaes.csv"), encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["cnpj_basico"].strip().zfill(8) not in empresas_semente:
                continue
            if row["qualificacao_socio"].strip() not in QUALIF_EQUITY:
                excluidos_qualif += 1
                continue
            chave = (row["nome_socio_ou_razao_social"].strip(), row["cnpj_cpf_socio"].strip())
            fronteira_socios.add(chave)
    socios_conhecidos |= fronteira_socios
    log(f"  {len(fronteira_socios):,} sócios-equity distintos na fronteira inicial "
        f"({excluidos_qualif:,} vínculos excluídos por qualificação não-societária).")

    estado = {
        "empresas_conhecidas": empresas_conhecidas,   # cnpj_basico já visto (não reprocessar)
        "socios_conhecidos": socios_conhecidos,       # (nome, cnpj_cpf_socio) já visto
        "fronteira_socios": fronteira_socios,         # sócios a investigar na PRÓXIMA rodada
        "rodada_atual": 0,
        "empresas_arquivos": [],
        "vinculos_arquivos": [],
        "rodada_de_empresa": {},   # cnpj_basico novo -> rodada de descoberta
    }
    return estado


def escaneia_socios_para_empresas(socios_alvo, rodada, pasta_rodada):
    """Busca REVERSA: acha toda empresa onde os sócios de `socios_alvo` aparecem
    (qualquer CNAE). Devolve lista de vínculos (cnpj_basico_dono = a empresa
    encontrada) e o set de cnpj_basico encontrados."""
    os.makedirs(pasta_rodada, exist_ok=True)
    reverso_path = os.path.join(pasta_rodada, "reverso.csv")

    if os.path.exists(reverso_path):
        log(f"  Rodada {rodada} (busca reversa): já escaneada — reaproveitando {pasta_rodada}")
    else:
        vinculos_reversos = []
        partes = sorted(glob.glob(os.path.join(PASTA_BRUTOS, "SOCIO*.csv")))
        log(f"  [Rodada {rodada}] Busca reversa (sócio -> empresas): {len(partes)} partes, "
            f"{len(socios_alvo):,} sócios-alvo...")
        for caminho in partes:
            with open(caminho, "r", encoding="latin1", errors="replace", newline="") as fin:
                leitor = csv.reader(fin, delimiter=";", quotechar='"')
                for campos in leitor:
                    if len(campos) < 11:
                        continue
                    chave = (campos[2].strip(), campos[3].strip())
                    if chave not in socios_alvo:
                        continue
                    if campos[4].strip() not in QUALIF_EQUITY:
                        continue  # ex.: administrador profissional de empresa não relacionada — não é participação real
                    tipo = "PJ" if campos[1].strip() == "1" else ("PF" if campos[1].strip() == "2" else "estrangeiro")
                    vinculos_reversos.append({
                        "cnpj_basico_dono": campos[0].strip(), "tipo_socio": tipo,
                        "nome_socio_ou_razao_social": campos[2], "cnpj_cpf_socio": campos[3],
                        "qualificacao_socio": campos[4], "data_entrada_sociedade": campos[5],
                        "rodada": rodada,
                    })
        log(f"    {len(vinculos_reversos):,} vínculos encontrados (empresas onde esses sócios aparecem).")
        with open(reverso_path, "w", encoding="utf-8-sig", newline="") as f:
            campos_v = ["cnpj_basico_dono", "tipo_socio", "nome_socio_ou_razao_social",
                        "cnpj_cpf_socio", "qualificacao_socio", "data_entrada_sociedade", "rodada"]
            w = csv.DictWriter(f, fieldnames=campos_v)
            w.writeheader()
            w.writerows(vinculos_reversos)

    with open(reverso_path, encoding="utf-8-sig", newline="") as f:
        vinculos_reversos = list(csv.DictReader(f))
    return vinculos_reversos


def escaneia_empresas_para_socios(cnpjs_alvo, rodada, pasta_rodada):
    """Mesma lógica de `esgotar_cadeia_societaria.py`: cadastro + sócios das
    empresas em `cnpjs_alvo` (aqui, SEM filtro de CNAE)."""
    cadastro_path = os.path.join(pasta_rodada, "cadastro.csv")
    vinculos_path = os.path.join(pasta_rodada, "vinculos.csv")

    if os.path.exists(cadastro_path) and os.path.exists(vinculos_path):
        log(f"  Rodada {rodada} (cadastro+sócios das empresas novas): já escaneada — reaproveitando {pasta_rodada}")
    else:
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

        vinculos = []
        partes = sorted(glob.glob(os.path.join(PASTA_BRUTOS, "SOCIO*.csv")))
        log(f"  [Rodada {rodada}] Sócios das empresas novas: {len(partes)} partes...")
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
                        "rodada": rodada,
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
                           "cnpj_cpf_socio", "qualificacao_socio", "data_entrada_sociedade", "rodada"]
            w = csv.DictWriter(f, fieldnames=campos_vinc)
            w.writeheader()
            w.writerows(vinculos)

    with open(cadastro_path, encoding="utf-8-sig", newline="") as f:
        cadastro = list(csv.DictReader(f))
    with open(vinculos_path, encoding="utf-8-sig", newline="") as f:
        vinculos = list(csv.DictReader(f))
    return cadastro, vinculos


def consolida_saida_final(estado):
    log("\nConsolidando multissetor_empresas.csv e multissetor_vinculos.csv finais...")
    emp_final = os.path.join(PASTA_MULTI, "multissetor_empresas.csv")
    vinc_final = os.path.join(PASTA_MULTI, "multissetor_vinculos.csv")
    tmp_emp, tmp_vinc = emp_final + ".tmp", vinc_final + ".tmp"

    total_emp = 0
    with open(tmp_emp, "w", encoding="utf-8-sig", newline="") as fout:
        w = None
        for pasta in estado["empresas_arquivos"]:
            caminho = os.path.join(pasta, "cadastro.csv")
            if not os.path.exists(caminho):
                continue
            with open(caminho, encoding="utf-8-sig", newline="") as fin:
                r = csv.DictReader(fin)
                if w is None:
                    w = csv.DictWriter(fout, fieldnames=r.fieldnames)
                    w.writeheader()
                for row in r:
                    w.writerow(row)
                    total_emp += 1
    os.replace(tmp_emp, emp_final)

    total_vinc = 0
    with open(tmp_vinc, "w", encoding="utf-8-sig", newline="") as fout:
        w = None
        for pasta, tipo in estado["vinculos_arquivos"]:
            nome_arq = "reverso.csv" if tipo == "reverso" else "vinculos.csv"
            caminho = os.path.join(pasta, nome_arq)
            if not os.path.exists(caminho):
                continue
            with open(caminho, encoding="utf-8-sig", newline="") as fin:
                r = csv.DictReader(fin)
                campos = r.fieldnames + (["origem"] if "origem" not in r.fieldnames else [])
                if w is None:
                    w = csv.DictWriter(fout, fieldnames=campos)
                    w.writeheader()
                for row in r:
                    row["origem"] = tipo
                    w.writerow(row)
                    total_vinc += 1
    os.replace(tmp_vinc, vinc_final)

    log(f"  {total_emp:,} linhas de empresas -> {emp_final}")
    log(f"  {total_vinc:,} linhas de vínculo -> {vinc_final}")


def main():
    if os.path.exists(ESTADO_PATH):
        log(f"Retomando checkpoint existente: {ESTADO_PATH}")
        with open(ESTADO_PATH, "rb") as f:
            estado = pickle.load(f)
    else:
        estado = constroi_estado_inicial()
        salva_estado(estado)

    while estado["fronteira_socios"] and estado["rodada_atual"] < MAX_RODADAS:
        rodada = estado["rodada_atual"] + 1
        socios_alvo = estado["fronteira_socios"]
        log(f"\n{'='*70}\nRODADA {rodada} — {len(socios_alvo):,} sócios na fronteira\n{'='*70}")

        pasta_rodada = os.path.join(PASTA_MULTI, f"rodada_{rodada:02d}")
        os.makedirs(pasta_rodada, exist_ok=True)

        # 1) busca reversa: sócio -> outras empresas
        vinculos_reversos = escaneia_socios_para_empresas(socios_alvo, rodada, pasta_rodada)
        estado["vinculos_arquivos"].append((pasta_rodada, "reverso"))

        # diagnóstico de grau alto (possível colisão de nome ou hub genuíno)
        grau = {}
        for v in vinculos_reversos:
            chave = (v["nome_socio_ou_razao_social"], v["cnpj_cpf_socio"])
            grau[chave] = grau.get(chave, 0) + 1
        altos = sorted([(k, n) for k, n in grau.items() if n > AVISO_GRAU_ALTO], key=lambda kv: -kv[1])
        if altos:
            log(f"  ⚠️ {len(altos)} sócio(s) com grau > {AVISO_GRAU_ALTO} (revisar antes de interpretar):")
            for (nome, ident), n in altos[:15]:
                log(f"      {nome} ({ident}): {n} empresas")

        empresas_novas = {v["cnpj_basico_dono"].strip() for v in vinculos_reversos}
        empresas_novas -= estado["empresas_conhecidas"]
        log(f"  {len(empresas_novas):,} empresas novas (fora do universo já conhecido) para investigar.")

        # 2) para as empresas novas: cadastro + seus próprios sócios
        if empresas_novas:
            cadastro, vinculos_forward = escaneia_empresas_para_socios(empresas_novas, rodada, pasta_rodada)
            estado["empresas_arquivos"].append(pasta_rodada)
            estado["vinculos_arquivos"].append((pasta_rodada, "forward"))
        else:
            cadastro, vinculos_forward = [], []

        for cnpj in empresas_novas:
            estado["rodada_de_empresa"].setdefault(cnpj, rodada)
        estado["empresas_conhecidas"] |= empresas_novas

        # 3) sócios-equity novos das empresas novas viram a fronteira da próxima rodada
        # (vinculos_forward é salvo por completo no CSV, com todas as qualificações —
        # só a FRONTEIRA de busca é restrita a sócio de fato, não administrador puro)
        nova_fronteira = set()
        for v in vinculos_forward:
            if v["qualificacao_socio"].strip() not in QUALIF_EQUITY:
                continue
            chave = (v["nome_socio_ou_razao_social"].strip(), v["cnpj_cpf_socio"].strip())
            if chave not in estado["socios_conhecidos"]:
                nova_fronteira.add(chave)
        estado["socios_conhecidos"] |= nova_fronteira

        log(f"\nRodada {rodada} concluída: {len(empresas_novas):,} empresas novas, "
            f"{len(cadastro):,} cadastros, {len(vinculos_forward):,} vínculos próprios, "
            f"{len(nova_fronteira):,} sócios novos para a próxima rodada.")

        estado["fronteira_socios"] = nova_fronteira
        estado["rodada_atual"] = rodada
        salva_estado(estado)

    if not estado["fronteira_socios"]:
        log(f"\n✅ Rede esgotada na rodada {estado['rodada_atual']} — nenhum sócio novo encontrado.")
    elif estado["rodada_atual"] >= MAX_RODADAS:
        log(f"\n⚠️ Teto de {MAX_RODADAS} rodadas atingido (pedido do autor), ainda restam "
            f"{len(estado['fronteira_socios']):,} sócios na fronteira. Aumente MAX_RODADAS no script "
            f"e rode de novo para continuar de onde parou (checkpoint já salvo).")

    consolida_saida_final(estado)

    log("\nResumo por rodada (nº de empresas novas descobertas em cada uma):")
    from collections import Counter
    c = Counter(estado["rodada_de_empresa"].values())
    for r in sorted(c):
        log(f"  rodada {r}: {c[r]:,} empresas novas")

    log("\nCole a saída deste script aqui para eu analisar os setores/CNAEs encontrados.")


if __name__ == "__main__":
    main()
