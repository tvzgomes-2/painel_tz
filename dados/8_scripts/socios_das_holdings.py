"""
Quem são os sócios das holdings identificadas como hubs na rede de sócios
médio/grande (método v4)? Se adicionarmos essa camada (sócio DA holding, não só
sócio DA empresa de transporte), algum par de componentes hoje separados se
funde (isto é, compartilha um sócio em comum uma vez que a holding é "aberta")?

Fonte da 2ª camada: socios_segunda_camada.csv (sócios dos sócios-PJ diretos das
empresas de transporte — já levantado no Passo 7, 24/07/2026). Cobre exatamente
os hubs PJ do grafo atual, que são todos sócios diretos (rodada 1).
"""
import json, csv
from collections import defaultdict

data = json.load(open("/tmp/grafo_medios_grandes.json"))
ident = json.load(open("/tmp/identificacao_componentes.json"))
nodes = data["nodes"]
componentes = [c for c in data["componentes"] if c["tamanho"] >= 3]

# mapear componente -> id_grupo (mesmo critério de before: tamanho+hubs)
ident_por_chave = {(r["tamanho"], tuple(sorted(r["hubs_todos_identidade"]))): r for r in ident}
def id_de(comp):
    chave = (comp["tamanho"], tuple(sorted(comp["hubs"])))
    r = ident_por_chave.get(chave)
    return r["id"] if r else None

# identidade -> lista de componente_id onde aparece como HUB
identidade_para_componentes = defaultdict(set)
comp_id_map = {}
for comp in componentes:
    cid = id_de(comp)
    comp_id_map[cid] = comp
    for h in comp["hubs"]:
        identidade_para_componentes[h].add(cid)

# holdings: nós PJ classificados como Holding/Participações, que são hub de algum componente
def tipo_pj(nome):
    n = nome.upper()
    holding_kw = ["PARTICIPACOES","PARTICIPAÇÕES","HOLDING","EMPREENDIMENTOS","ADMINISTRACAO","NEGOCIOS","GESTAO","INVESTIMENTOS"]
    if any(k in n for k in holding_kw): return "Holding/Participações"
    return None

holdings_por_componente = defaultdict(list)  # cid -> [(identidade, cnpj_basico)]
for cid, comp in comp_id_map.items():
    for h in comp["hubs"]:
        info = nodes.get(h, {})
        if info.get("tipo_socio") == "PJ":
            nome, cnpjfull = h.rsplit("|", 1)
            if tipo_pj(nome) == "Holding/Participações":
                cnpj_basico = cnpjfull.zfill(14)[:8]
                holdings_por_componente[cid].append((h, cnpj_basico))

total_holdings = sum(len(v) for v in holdings_por_componente.values())
print(f"Holdings-hub encontradas em {len(holdings_por_componente)} componentes ({total_holdings} holdings no total).")

# carregar sócios da 2a camada (sócios das holdings/PJs de rodada 1)
socios_2cam = defaultdict(list)  # cnpj_basico da holding -> lista de (identidade do sócio, tipo)
with open("socios_segunda_camada.csv", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        cnpj_basico = row["cnpj_basico"].zfill(8)
        nome = row["nome_socio_ou_razao_social"].strip()
        cpf_cnpj = row["cnpj_cpf_socio"].strip()
        identidade = f"{nome}|{cpf_cnpj}"
        socios_2cam[cnpj_basico].append((identidade, row["tipo_socio"]))

print(f"Holdings com sócios levantados na 2ª camada: {len(socios_2cam)} CNPJs distintos.")

# checar pontes
pontes = []
holdings_sem_2cam = []
holdings_sem_ponte = []
for cid, holdings in holdings_por_componente.items():
    for identidade_holding, cnpj_basico in holdings:
        socios = socios_2cam.get(cnpj_basico)
        if not socios:
            holdings_sem_2cam.append((cid, identidade_holding, cnpj_basico))
            continue
        achou_ponte = False
        for identidade_socio, tipo in socios:
            outros = identidade_para_componentes.get(identidade_socio, set()) - {cid}
            if outros:
                pontes.append((cid, identidade_holding, cnpj_basico, identidade_socio, tipo, sorted(outros)))
                achou_ponte = True
        if not achou_ponte:
            holdings_sem_ponte.append((cid, identidade_holding, cnpj_basico, len(socios)))

print(f"\nHoldings sem dado de 2ª camada (não achamos o cadastro): {len(holdings_sem_2cam)}")
print(f"Holdings com sócios levantados mas SEM ponte para outro componente: {len(holdings_sem_ponte)}")
print(f"PONTES ENCONTRADAS (sócio da holding também é hub de outro componente): {len(pontes)}")
for p in pontes:
    cid, ident_h, cnpj, ident_s, tipo, outros = p
    print(f"  componente {cid} <- holding {ident_h} <- sócio {ident_s} ({tipo}) -> também hub em componente(s) {outros}")

json.dump({"pontes": pontes, "holdings_sem_2cam": holdings_sem_2cam, "holdings_sem_ponte": holdings_sem_ponte,
           "total_holdings": total_holdings}, open("/tmp/resultado_socios_holdings.json","w"), ensure_ascii=False, indent=2)
