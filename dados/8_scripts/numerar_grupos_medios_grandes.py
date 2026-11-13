"""
Numera cada componente médio/grande da rede de sócios (recorte 6 CNAEs, método v4)
com um ID único (GE-001..GE-165, por tamanho decrescente) e sinaliza colisões de
nome (mesmo "nome_sugerido" em componentes distintos).

Entrada: identificacao_componentes.json (/tmp, gerado na rodada de rotulagem de 04/08/2026)
Saída: identificacao_componentes_medios_grandes_v4.csv (atualizado, com id_grupo,
       nome_sugerido_unico, alerta_colisao_nome) + grafo rotulado com ID por cluster.

Critério de colisão: dois ou mais componentes com nome_sugerido idêntico.
- origem "família" + sobrenome entre os 20 mais comuns do Brasil (IBGE) -> colisão
  tratada como coincidência de sobrenome (grupos prováveis DIFERENTES); sufixo (A),(B)...
  por tamanho decrescente, maior = A.
- origem "holding" ou "documental" (não deveria ocorrer, pois nome documental é
  case-a-case) -> alerta forte, exige checagem manual (poderia indicar o mesmo grupo
  fragmentado em 2+ componentes desconexos, como já ocorre com "Felício" mas com
  nomes de holding distintos entre si).
"""
import json, csv
from collections import defaultdict

SOBRENOMES_COMUNS_BR = {
    "silva","santos","souza","sousa","oliveira","pereira","lima","carvalho",
    "gomes","costa","ribeiro","martins","araujo","araújo","melo","barbosa",
    "rocha","dias","monteiro","cardoso","reis","alves","fernandes","freitas",
    "barros","mendes","teixeira","moreira","nascimento","lopes","abrantes",
    "cunha","basilio","basílio","marques","ferreira","almeida","rodrigues",
}

ident = json.load(open("/tmp/identificacao_componentes.json"))
ident_por_id = {r["id"]: r for r in ident}

# ordenar por tamanho decrescente para atribuir sufixo A/B/C.. às colisões
por_nome = defaultdict(list)
for r in ident:
    por_nome[r["nome_sugerido"].strip()].append(r)

nome_unico = {}
alerta = {}
for nome, rs in por_nome.items():
    rs_sorted = sorted(rs, key=lambda r: -r["tamanho"])
    if len(rs_sorted) == 1:
        r = rs_sorted[0]
        nome_unico[r["id"]] = nome
        alerta[r["id"]] = ""
        continue
    origens = {r["origem_nome"] for r in rs_sorted}
    sobrenome_comum = nome.lower().split()[-1] in SOBRENOMES_COMUNS_BR
    for i, r in enumerate(rs_sorted):
        suf = chr(ord('A') + i)
        nome_unico[r["id"]] = f"{nome} ({suf})"
        if origens == {"família"} and sobrenome_comum:
            alerta[r["id"]] = (f"colisão de nome — sobrenome comum ({len(rs_sorted)} componentes); "
                                f"provável coincidência, não indício de vínculo real")
        elif origens == {"família"}:
            alerta[r["id"]] = (f"colisão de nome — sobrenome repetido em {len(rs_sorted)} componentes "
                                f"(não é sobrenome muito comum; vale checar se há vínculo perdido)")
        else:
            alerta[r["id"]] = (f"⚠️ colisão entre origem '{origens}' — checar manualmente, "
                                f"pode indicar o mesmo grupo fragmentado")

# reescrever CSV com as novas colunas
path = "/sessions/kind-sleepy-feynman/mnt/doutorado/03 - Dados/_data/CNPJ/filtrados (6 CNAEs transporte, 24-07-2026)/identificacao_componentes_medios_grandes_v4.csv"
rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
fieldnames = ["id_grupo","componente_id","tamanho","n_hubs","status_documental","cobertura",
              "nome_sugerido","nome_sugerido_unico","alerta_colisao_nome","origem_nome","top_hubs"]
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        cid = int(r["componente_id"])
        r["id_grupo"] = f"GE-{cid:03d}"
        r["nome_sugerido_unico"] = nome_unico.get(cid, r["nome_sugerido"])
        r["alerta_colisao_nome"] = alerta.get(cid, "")
        w.writerow({k: r[k] for k in fieldnames})

n_colisoes = sum(1 for v in alerta.values() if v)
print(f"linhas: {len(rows)} | componentes com colisão de nome: {n_colisoes} | grupos de colisão: {sum(1 for rs in por_nome.values() if len(rs)>1)}")

# salvar mapping id->nome_unico para uso no script do grafo
json.dump(nome_unico, open("/tmp/nome_unico_por_id.json","w"), ensure_ascii=False)
