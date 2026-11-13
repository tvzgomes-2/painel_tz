#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
calcular_grupos_economicos_v2.py

Recalcula os "grupos econômicos" do transporte coletivo a partir da rede
mais nova e mais limpa (núcleo CNAE 4921-3 + empresa ativa + sócio-equity,
recorte "6 CNAEs transporte, 24-07-2026"), isolando os CONSÓRCIOS de
licitação (que contaminavam análises anteriores ao ligar empresas sem
vínculo societário real via um administrador comum de consórcio).

Histórico de decisões do autor (Thiago):
- 03/08/2026: "vamos reescrever o método de cálculo do grupo com a rede
  mais nova e mais limpa, isolando os consórcios. Faça ele gerar uma
  tabela nova de grupos que será o novo cânone da pesquisa." → gerou a
  v2 (sócio-equity, consórcio isolado): excluía TANTO os nós de
  consórcio QUANTO qualquer vínculo de administrador puro.
- 04/08/2026, após ver o achado de que o filtro de administrador puro
  fragmentava demais grupos grandes e reais (Barata, Lessa
  Carvalho/Aguiar-Carvalho): "prefiro manter os consórcios isolados, mas
  incluir os administradores." → método v3: consórcio isolado (nós),
  TODAS as qualificações mantidas nas arestas (inclusive código RFB 20,
  "Sociedade Consorciada", que até então estava junto com o código 05
  no mesmo balde "administrador puro").
- 04/08/2026 (mesmo dia), a partir da pergunta do autor sobre o
  componente "Comporte/Constantino" (rotulado "Barata" pelo cruzamento
  documental, mas na verdade Pekin/Constantino): "Sociedade Consorciada
  — vale a pena retirarmos como os consórcios?" → testado empiricamente
  (ver RESULTADO v4 abaixo): excluir só a qualificação 20 (mantendo a
  05, administrador) tem efeito pequeno mas real e bem direcionado —
  separa ainda mais um cluster de Porto Alegre/RS já sinalizado como
  problemático (item (aa) de Pendências, "Nortran-Trevo"), e não altera
  em nada o componente Comporte/Constantino (sua coesão vem de
  administrador/sócio genuíno, códigos 05/22, não de código 20). Virou
  **método v4, modo padrão deste script a partir de 04/08/2026**. v3 e
  v2 ficam documentados como variantes históricas (ver --modo).

MÉTODO v4 (padrão — consórcio isolado como nó, "Sociedade Consorciada"
isolada como vínculo, administrador mantido):
1. Universo de empresas: `rede_nucleo_ativa_equity_componentes.csv`
   (7.680 empresas — núcleo 4921-3, situação ativa).
2. Exclusão explícita dos CONSÓRCIOS: qualquer empresa cuja razão social
   contenha "CONSORCIO"/"CONSÓRCIO" é removida do universo ANTES de
   montar o grafo (121 das 7.680) — filtro estrutural sobre os NÓS.
3. Exclusão da qualificação RFB **20 (Sociedade Consorciada)** das
   ARESTAS — mesma lógica do item 2, mas para o vínculo (uma empresa
   real que consta como "sócia" de um CONSÓRCIO de licitação, Lei
   8.987/95 art. 19-20, não é vínculo de controle econômico). Mantém-se
   a qualificação **05 (Administrador)**, que o autor pediu para
   restaurar em 04/08/2026 — são papéis distintos na Tabela IV da RFB,
   antes tratados juntos por engano (`QUALIFICACOES_ADMIN_PURO = {05,20}`).
4. Arestas: duas empresas se ligam se compartilham o MESMO sócio,
   identificado por (nome do sócio + CPF/CNPJ mascarado) — não só o
   identificador mascarado isolado, que colide entre sócios distintos
   (bug corrigido em 24/07/2026, ver `pesquisa dos CNPJs.md`).
5. Componentes conexos calculados com NetworkX.
6. Validação cruzada: cada componente é comparado contra os CNPJs já
   documentados nos 11 grupos confirmados em `Perfil dos Grupos
   Econômicos - CNPJs e Sócios.md` (Barata, Lessa Carvalho/Aguiar-
   Carvalho, Belarmino, Gulin+Corleto, Baltazar, Nova Suissa, 1001,
   Ruas, Pekin/Constantino, Gammbus, Andorinha).

RESULTADO v4 vs. v3 (04/08/2026): efeito pequeno e localizado. Porte
grande: idêntico (11 componentes, mesmos tamanhos 51-25-22-20-14-13-12-
11-10-10-10). Porte médio: 153→154 (+1). Um cluster de Porto Alegre/RS
de 8 empresas (Estrela Sul, Gramado, MOB-Mobilidade, Restinga,
Sociedade de Ônibus Porto Alegrense, Sudeste) se parte em 2 (5+3) ao
excluir a qualificação 20 — consistente com o mecanismo de artefato de
consórcio municipal já documentado no item (y) de Pendências, e
possivelmente relacionado ao caso "Nortran-Trevo/Porto Alegre" (item
(aa), ainda em aberto). O componente Comporte/Constantino (20 empresas)
**não muda nada** — checado linha a linha, sua coesão vem de
administrador (05) e sócio-PJ (22) genuínos entre famílias Constantino,
não de "Sociedade Consorciada".

RESULTADO v3 vs. v2 (04/08/2026, histórico): incluir administradores
recupera boa parte da fragmentação do método anterior sem reabrir a
contaminação por consórcio. Barata sobe de 30→51+20 empresas nos 2
maiores componentes (66% do total documentado, era 28%); Lessa
Carvalho/Aguiar-Carvalho sobe para 14+10 (41%, era 19%); Gulin+Corleto,
Nova Suissa, "1001" e Pekin/Constantino melhoram a cobertura mas
continuam sem atingir 10 empresas no maior fragmento (permanecem
"médios"). Ainda restam 3 componentes "grandes" não identificados
(12, 10, 10 empresas) — ver saída v3.

MODO="equity" (variante histórica v2, 03/08/2026): reproduz o método
antigo (exclui também administrador puro — códigos 05 e 20 juntos) caso
seja necessário comparar ou auditar a decisão. Inalterado pela mudança
de 04/08/2026, pois já excluía a qualificação 20.

MODO="v3" (variante histórica, mesmo dia): reproduz o método v3 (inclui
05 e 20 juntos) para comparação directa com o v4 adotado.

Uso:
    python3 calcular_grupos_economicos_v2.py                 # modo v4 (padrão, 04/08/2026)
    python3 calcular_grupos_economicos_v2.py --modo v3        # modo v3 (histórico, 04/08/2026)
    python3 calcular_grupos_economicos_v2.py --modo equity    # modo v2 (histórico, 03/08/2026)

Saídas (na mesma pasta do recorte "6 CNAEs transporte, 24-07-2026"), sufixo conforme o modo:
    - grupos_economicos_{sufixo}_componentes_completos.csv  (todos os componentes, tamanho>=2)
    - grupos_economicos_{sufixo}_tabela_canonica.csv        (componentes com 10+ empresas, com status/match)
    - grupos_economicos_{sufixo}_tabela_por_porte.csv        (todos os componentes 2+, com porte grande/médio/pequeno)
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx
import pandas as pd

BASE = Path(__file__).resolve()
# Pasta de dados do recorte (ajustar se o cofre for movido)
PASTA_DADOS = Path(
    r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\CNPJ"
    r"\filtrados (6 CNAEs transporte, 24-07-2026)"
)
PERFIL_GRUPOS_MD = Path(
    r"C:\Users\HOME\OneDrive\doutorado\03 - Dados"
    r"\Perfil dos Grupos Econômicos - CNPJs e Sócios.md"
)

QUALIFICACOES_ADMIN_PURO = {"05", "20"}  # histórico (v2/v3): administrador + sociedade consorciada juntos
QUALIF_ADMINISTRADOR = {"05"}  # Administrador (RFB Tabela IV) — mantido desde 04/08/2026 (v3+)
QUALIF_SOCIEDADE_CONSORCIADA = {"20"}  # Sociedade Consorciada (RFB Tabela IV) — excluído desde 04/08/2026 (v4)


def carregar_universo():
    comp = pd.read_csv(PASTA_DADOS / "rede_nucleo_ativa_equity_componentes.csv", dtype=str)
    comp["cnpj_basico"] = comp["cnpj_basico"].astype(str).str.zfill(8)
    razao = dict(zip(comp["cnpj_basico"], comp["razao_social"]))
    return set(comp["cnpj_basico"]), razao


def carregar_grupos_documentados():
    """Extrai, do Perfil dos Grupos Econômicos, a lista de CNPJs de cada
    um dos 11 grupos já confirmados (tabela '### CNPJs do grupo')."""
    with open(PERFIL_GRUPOS_MD, encoding="utf-8") as f:
        linhas = f.readlines()

    headers = []
    for i, l in enumerate(linhas):
        if l.startswith("## ") and "Método" not in l:
            headers.append((i, l.strip("# \n")))
    headers.append((len(linhas), "FIM"))

    grupos = {}
    for (ini, nome), (fim, _) in zip(headers, headers[1:]):
        cnpjs = []
        for l in linhas[ini:fim]:
            m = re.match(r"^\|\s*(\d{7,8})\s*\|\s*([^|]+)\|", l)
            if m:
                cnpjs.append(m.group(1).zfill(8))
        grupos[nome] = cnpjs
    return grupos


def montar_grafo(universo_sem_consorcio, modo="v4"):
    soc = pd.read_csv(PASTA_DADOS / "socios_filtrado_6cnaes.csv", dtype=str)
    soc.columns = [c.strip() for c in soc.columns]
    soc["cnpj_basico"] = soc["cnpj_basico"].astype(str).str.zfill(8)
    soc_u = soc[soc["cnpj_basico"].isin(universo_sem_consorcio)].copy()
    if modo == "equity":
        # v2 histórica (03/08/2026): exclui também vínculo de administrador puro (05+20)
        soc_u = soc_u[~soc_u["qualificacao_socio"].isin(QUALIFICACOES_ADMIN_PURO)].copy()
    elif modo == "v3":
        # v3 histórica (04/08/2026, manhã): mantém todas as qualificações, inclusive
        # 05 (administrador) e 20 (sociedade consorciada) juntas.
        pass
    else:
        # modo "v4" (padrão desde 04/08/2026, tarde): mantém administrador (05),
        # exclui sociedade consorciada (20) — mesma lógica do isolamento de nós
        # de consórcio, aplicada agora ao vínculo societário equivalente.
        soc_u = soc_u[~soc_u["qualificacao_socio"].isin(QUALIF_SOCIEDADE_CONSORCIADA)].copy()
    soc_u["identidade"] = (
        soc_u["nome_socio_ou_razao_social"].str.strip().str.upper()
        + "|"
        + soc_u["cnpj_cpf_socio"].astype(str).str.strip()
    )

    G = nx.Graph()
    G.add_nodes_from(universo_sem_consorcio)
    for _, grupo in soc_u.groupby("identidade"):
        empresas = [e for e in grupo["cnpj_basico"].unique() if e in universo_sem_consorcio]
        for i in range(len(empresas)):
            for j in range(i + 1, len(empresas)):
                G.add_edge(empresas[i], empresas[j])
    return G


def bucket(n):
    if n == 1:
        return "isolada"
    if n == 2:
        return "par"
    if 3 <= n <= 5:
        return "3-5"
    if 6 <= n <= 10:
        return "6-10"
    if 11 <= n <= 20:
        return "11-20"
    if 21 <= n <= 50:
        return "21-50"
    return "50+"


def porte(n):
    """Classificação por porte pedida pelo autor (04/08/2026):
    grandes = 10+ empresas · médios = 3-9 · pequenos = 2 (isoladas, 1 empresa, não contam como 'grupo')."""
    if n >= 10:
        return "grande"
    if 3 <= n <= 9:
        return "médio"
    if n == 2:
        return "pequeno"
    return "isolada (não é grupo)"


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--modo", choices=["v4", "v3", "equity"], default="v4",
        help="v4 = padrão (04/08/2026, tarde): consórcio isolado (nó) + sociedade "
             "consorciada isolada (aresta, qualif. 20), administrador (05) mantido. "
             "v3 = histórica (04/08/2026, manhã): consórcio isolado, TODAS as "
             "qualificações mantidas (05 e 20 juntas). "
             "equity = v2 histórica (03/08/2026): consórcio isolado E administrador "
             "puro (05+20) excluído."
    )
    args = parser.parse_args()
    sufixo = {"v4": "v4", "v3": "v3", "equity": "v2"}[args.modo]

    universo, razao = carregar_universo()
    consorcios = {c for c, r in razao.items() if "CONSORCIO" in r.upper() or "CONSÓRCIO" in r.upper()}
    universo_limpo = universo - consorcios
    print(f"Modo: {args.modo} (saídas com sufixo '{sufixo}')")
    print(f"Universo total (núcleo+ativa+equity): {len(universo)} empresas")
    print(f"Consórcios isolados/excluídos: {len(consorcios)}")
    print(f"Universo depois de isolar consórcios: {len(universo_limpo)} empresas")

    grupos_doc = carregar_grupos_documentados()
    cnpj_to_grupo = defaultdict(list)
    for grupo, cnpjs in grupos_doc.items():
        for c in cnpjs:
            cnpj_to_grupo[c].append(grupo)

    G = montar_grafo(universo_limpo, modo=args.modo)
    componentes = list(nx.connected_components(G))
    print(f"Total de componentes (>=1 empresa): {len(componentes)}")
    print("Distribuição de tamanho:", Counter(bucket(len(c)) for c in componentes))

    # ---- saída 1: todos os componentes com 2+ empresas ----
    linhas_completas = []
    for cid, c in enumerate(componentes):
        if len(c) < 2:
            continue
        matches = Counter()
        for cnpj in c:
            for g in cnpj_to_grupo.get(cnpj, []):
                matches[g] += 1
        grupo_dominante = matches.most_common(1)[0][0] if matches else ""
        for cnpj in sorted(c):
            linhas_completas.append(
                {
                    "componente_id": cid,
                    "tamanho_componente": len(c),
                    "cnpj_basico": cnpj,
                    "razao_social": razao.get(cnpj, ""),
                    "grupo_documentado_dominante": grupo_dominante,
                    "match_grupos_documentados": ";".join(sorted(matches)) if matches else "",
                }
            )
    df_completo = pd.DataFrame(linhas_completas)
    saida1 = PASTA_DADOS / f"grupos_economicos_{sufixo}_componentes_completos.csv"
    df_completo.to_csv(saida1, index=False, encoding="utf-8-sig")
    print(f"Salvo: {saida1} ({len(df_completo)} linhas)")

    # ---- saída 2: tabela canônica (componentes 10+) ----
    grandes = sorted([c for c in componentes if len(c) >= 10], key=len, reverse=True)
    linhas_canon = []
    for idx, c in enumerate(grandes, 1):
        matches = Counter()
        for cnpj in c:
            for g in cnpj_to_grupo.get(cnpj, []):
                matches[g] += 1
        if matches:
            grupo, n_match = matches.most_common(1)[0]
            cobertura = n_match / len(c)
            status = f"confirmado = {grupo} ({n_match}/{len(c)} empresas batem, {cobertura:.0%})"
        else:
            grupo = ""
            status = "não identificado — candidato a grupo novo, pesquisa histórica pendente"
        exemplos = ", ".join(sorted(razao.get(e, "") for e in c)[:5])
        linhas_canon.append(
            {
                "componente_id_novo": idx,
                "tamanho": len(c),
                "grupo_atribuido": grupo,
                "status": status,
                "exemplos_razao_social": exemplos,
            }
        )
    df_canon = pd.DataFrame(linhas_canon)
    saida2 = PASTA_DADOS / f"grupos_economicos_{sufixo}_tabela_canonica.csv"
    df_canon.to_csv(saida2, index=False, encoding="utf-8-sig")
    print(f"Salvo: {saida2} ({len(df_canon)} linhas)")

    # ---- saída 3: tabela por porte (grande 10+ / médio 3-9 / pequeno 2) ----
    # Decisão do autor (04/08/2026): dividir em 3 partes por tamanho do componente,
    # em vez de um único número "canônico". Isoladas (1 empresa) não contam como
    # grupo econômico (não há relação societária a mapear).
    todos_multi = sorted([c for c in componentes if len(c) >= 2], key=len, reverse=True)
    linhas_porte = []
    for idx, c in enumerate(todos_multi, 1):
        matches = Counter()
        for cnpj in c:
            for g in cnpj_to_grupo.get(cnpj, []):
                matches[g] += 1
        if matches:
            grupo, n_match = matches.most_common(1)[0]
            cobertura = n_match / len(c)
            status = f"confirmado = {grupo} ({n_match}/{len(c)} empresas batem, {cobertura:.0%})"
        else:
            grupo = ""
            status = "não identificado"
        exemplos = ", ".join(sorted(razao.get(e, "") for e in c)[:5])
        linhas_porte.append(
            {
                "componente_id_novo": idx,
                "porte": porte(len(c)),
                "tamanho": len(c),
                "grupo_atribuido": grupo,
                "status": status,
                "exemplos_razao_social": exemplos,
            }
        )
    df_porte = pd.DataFrame(linhas_porte)
    saida3 = PASTA_DADOS / f"grupos_economicos_{sufixo}_tabela_por_porte.csv"
    df_porte.to_csv(saida3, index=False, encoding="utf-8-sig")
    print(f"Salvo: {saida3} ({len(df_porte)} linhas)")

    print("\n=== Resumo por porte (componentes com 2+ empresas; isoladas excluídas) ===")
    resumo_porte = df_porte.groupby("porte").agg(
        n_componentes=("componente_id_novo", "count"),
        n_confirmados=("status", lambda s: (s.str.startswith("confirmado")).sum()),
    )
    print(resumo_porte)
    print(f"\nEmpresas isoladas (1 empresa, não contam como grupo): {sum(1 for c in componentes if len(c) == 1)}")

    # ---- resumo de fragmentação por grupo já documentado ----
    print("\n=== Fragmentação dos grupos já documentados nesta rede (equity, sem consórcio) ===")
    comp_id_of = {}
    for i, c in enumerate(componentes):
        for e in c:
            comp_id_of[e] = i
    for grupo, cnpjs in grupos_doc.items():
        no_universo = [c for c in cnpjs if c in universo_limpo]
        if not no_universo:
            print(f"{grupo}: 0 empresas no universo (sem consórcio)")
            continue
        ids = Counter(comp_id_of[c] for c in no_universo)
        maior_id, maior_n = ids.most_common(1)[0]
        tam_maior = len(componentes[maior_id])
        print(
            f"{grupo}: {len(no_universo)} empresas documentadas no universo | "
            f"maior componente concentra {maior_n} delas (tamanho do componente: {tam_maior}) | "
            f"{len(ids)} componente(s) distintos no total"
        )


if __name__ == "__main__":
    main()
