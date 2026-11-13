"""
Reconstrução da identificação dos 165 componentes médio/grande (rede v4) — CORRIGE
o bug apontado pelo autor: "tirar vínculos dos grupos segundo a literatura - criá-lo
apenas pelos sócios - seu match está dando muitos problemas (Barata triplicado e
grupo Constantino não atribuído)".

Bug: a versão anterior atribuía um componente a um grupo documentado sempre que
seus CNPJs apareciam na TABELA do grupo no Perfil doc — mas essa tabela mistura
evidência de sócio (rede v4) com evidência documental/histórica (imprensa, NTU),
que é exatamente a categoria de CNPJs "sem vínculo societário" já mapeada nas
auditorias (Teste 8/10). Resultado: fragmentos pequenos e desconexos (sem
nenhum sócio em comum com o núcleo real) herdavam o nome do grupo grande só por
coincidência de CNPJ na tabela — daí "Barata" aparecer em vários componentes
não relacionados, e o componente real do Comporte/Constantino não ficar isolado
com nome próprio.

Correção: atribuir um grupo a um componente SÓ SE o componente contém o
sócio-âncora (1ª linha da tabela "Sócios-chave" de cada grupo/sub-cluster no
Perfil doc) — ou seja, só por vínculo de sócio na rede v4, nunca por overlap de
lista de CNPJ. Isso garante no máximo 1 componente por grupo documentado.
"""
import csv, json, re
from collections import defaultdict, Counter

QUALIF_SOCIEDADE_CONSORCIADA = {"20"}
SOBRENOMES_COMUNS_BR = {
    "silva","santos","souza","sousa","oliveira","pereira","lima","carvalho",
    "gomes","costa","ribeiro","martins","araujo","araújo","melo","barbosa",
    "rocha","dias","monteiro","cardoso","reis","alves","fernandes","freitas",
    "barros","mendes","teixeira","moreira","nascimento","lopes","abrantes",
    "cunha","basilio","basílio","marques","ferreira","almeida","rodrigues",
}
CONECTORES = {"DA","DE","DO","DOS","DAS","E","DI","DELLA","VON","VAN"}
SUFIXOS = {"JUNIOR","JR","NETO","FILHO","SOBRINHO"}

# 1) universo por componente
cnpjs_por_comp = defaultdict(set)
tam_por_comp = {}
for r in csv.DictReader(open("grupos_economicos_v4_componentes_completos.csv", encoding="utf-8-sig")):
    cid = r["componente_id"]
    cnpjs_por_comp[cid].add(r["cnpj_basico"].zfill(8))
    tam_por_comp[cid] = int(r["tamanho_componente"])

# 2) sócios por empresa (método v4)
socios_por_empresa = defaultdict(list)
for r in csv.DictReader(open("socios_filtrado_6cnaes.csv", encoding="utf-8-sig")):
    if r["qualificacao_socio"].strip() in QUALIF_SOCIEDADE_CONSORCIADA:
        continue
    cnpj = r["cnpj_basico"].zfill(8)
    identidade = f'{r["nome_socio_ou_razao_social"].strip()}|{r["cnpj_cpf_socio"].strip()}'
    socios_por_empresa[cnpj].append((identidade, r["tipo_socio"]))

# 3) hubs por componente (sócio em 2+ empresas do mesmo componente)
empresas_por_socio_por_comp = defaultdict(lambda: defaultdict(set))
tipo_por_identidade = {}
for cnpj, socios in socios_por_empresa.items():
    cid = None
    for c, cnpjs in cnpjs_por_comp.items():
        pass
# indexar cnpj->componente diretamente (mais rápido)
comp_de_cnpj = {}
for cid, cnpjs in cnpjs_por_comp.items():
    for c in cnpjs:
        comp_de_cnpj[c] = cid

empresas_por_socio_por_comp = defaultdict(lambda: defaultdict(set))
tipo_por_identidade = {}
nome_para_comps = defaultdict(set)
for cnpj, socios in socios_por_empresa.items():
    cid = comp_de_cnpj.get(cnpj)
    if cid is None:
        continue
    for identidade, tipo in socios:
        empresas_por_socio_por_comp[cid][identidade].add(cnpj)
        tipo_por_identidade[identidade] = tipo
        nome_para_comps[identidade.rsplit("|",1)[0]].add(cid)

hubs_por_comp = {}
for cid, socios_dict in empresas_por_socio_por_comp.items():
    hubs = [ident for ident, empresas in socios_dict.items() if len(empresas) >= 2]
    if hubs:
        hubs_por_comp[cid] = hubs

# 4) atribuição por sócio-âncora (única fonte de nome documental agora)
anchor = json.load(open("/tmp/anchor_por_grupo.json"))
atribuicao_ancora = {}
for grupo, nome_ancora in anchor.items():
    comps = nome_para_comps.get(nome_ancora, set())
    if not comps:
        continue
    melhor = max(comps, key=lambda c: tam_por_comp.get(c, 0))
    atribuicao_ancora[melhor] = grupo

# 5) montar identificação completa (médio+grande, tam>=3)
def tipo_pj(nome):
    n = nome.upper()
    holding_kw = ["PARTICIPACOES","PARTICIPAÇÕES","HOLDING","EMPREENDIMENTOS","ADMINISTRACAO","NEGOCIOS","GESTAO","INVESTIMENTOS"]
    return "Holding/Participações" if any(k in n for k in holding_kw) else None

def sobrenome_familia(hubs_pf_nomes):
    candidatos = Counter()
    pessoa_por_candidato = defaultdict(set)
    for nome in hubs_pf_nomes:
        tokens = [t for t in nome.split() if t not in CONECTORES and t not in SUFIXOS]
        for t in tokens[-2:]:
            pessoa_por_candidato[t.title()].add(nome)
    recorrentes = {k: v for k, v in pessoa_por_candidato.items() if len(v) >= 2}
    if recorrentes:
        melhor = max(recorrentes.items(), key=lambda kv: len(kv[1]))
        return melhor[0]
    if hubs_pf_nomes:
        tokens = [t for t in hubs_pf_nomes[0].split() if t not in CONECTORES and t not in SUFIXOS]
        return tokens[-1].title() if tokens else hubs_pf_nomes[0].title()
    return None

resultado = []
for cid, tam in tam_por_comp.items():
    if tam < 3:
        continue
    hubs = hubs_por_comp.get(cid, [])
    n_hubs = len(hubs)
    grupo_ancora = atribuicao_ancora.get(cid)
    if grupo_ancora:
        nome, origem, status = grupo_ancora.split(" :: ")[-1] if " :: " in grupo_ancora else grupo_ancora, "sócio-âncora", f"confirmado por sócio-âncora: {grupo_ancora}"
    else:
        pj_holdings = []
        pf_nomes = []
        for h in hubs:
            nome_h, doc_h = h.rsplit("|", 1)
            if tipo_por_identidade.get(h) == "PJ" and tipo_pj(nome_h) == "Holding/Participações":
                n_emp = len(empresas_por_socio_por_comp[cid][h])
                pj_holdings.append((n_emp, nome_h))
            elif tipo_por_identidade.get(h) == "PF":
                pf_nomes.append(nome_h)
        if pj_holdings:
            pj_holdings.sort(reverse=True)
            nome, origem, status = pj_holdings[0][1].title(), "holding", "não identificado"
        elif pf_nomes:
            nome, origem, status = sobrenome_familia(pf_nomes), "família", "não identificado"
        else:
            nome, origem, status = None, None, "não identificado (sem 2º hub)"
    resultado.append({
        "componente_id": cid, "tamanho": tam, "n_hubs": n_hubs,
        "grupo_ancora": grupo_ancora or "", "nome_sugerido": nome or "",
        "origem_nome": origem or "", "status": status,
        "top_hubs": "; ".join(h.split("|")[0] for h in sorted(hubs, key=lambda h: -len(empresas_por_socio_por_comp[cid][h]))[:4]),
    })

resultado.sort(key=lambda r: -r["tamanho"])
for i, r in enumerate(resultado, 1):
    r["id_grupo"] = f"GE-{i:03d}"

print(f"{len(resultado)} componentes médio+grande identificados.")
print(f"Com grupo por sócio-âncora: {sum(1 for r in resultado if r['grupo_ancora'])}")
print(f"Sem 2º hub (não desenháveis): {sum(1 for r in resultado if r['status']=='não identificado (sem 2º hub)')}")

# checar duplicação (agora deve ser zero SEMPRE para grupo_ancora)
by_grupo = defaultdict(list)
for r in resultado:
    if r["grupo_ancora"]:
        by_grupo[r["grupo_ancora"]].append(r["componente_id"])
dups = {g: c for g, c in by_grupo.items() if len(c) > 1}
print(f"Grupos-âncora atribuídos a 2+ componentes (deve ser 0): {len(dups)} {dups if dups else ''}")

json.dump(resultado, open("/tmp/identificacao_v2.json", "w"), ensure_ascii=False, indent=1)

with open("identificacao_componentes_medios_grandes_v4.csv", "w", newline="", encoding="utf-8") as f:
    campos = ["id_grupo","componente_id","tamanho","n_hubs","grupo_ancora","nome_sugerido","origem_nome","status","top_hubs"]
    w = csv.DictWriter(f, fieldnames=campos)
    w.writeheader()
    for r in resultado:
        w.writerow({k: r[k] for k in campos})
print("CSV salvo: identificacao_componentes_medios_grandes_v4.csv (SUBSTITUÍDO)")
