#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Organiza a saida de classificar_pendencias.py em tiers de trabalho para o
sprint de fechamento (meta: 30% dos itens abertos ate uma data-alvo).
Read-only: le o JSON gerado por classificar_pendencias.py, nao altera nada.
"""
import json, sys, re

IN_JSON = sys.argv[1] if len(sys.argv) > 1 else "classificacao_pendencias.json"
with open(IN_JSON, encoding="utf-8") as f:
    data = json.load(f)

blocos = data["blocos"]
total_open = data["total_open"]

DONE_KW = re.compile(r"✅|🟢|📄|Conclu[íi]do", re.I)

def is_tier_a(b):
    return bool(DONE_KW.search(b["title"])) and b["n_open"] <= 3

tiers = {"A": [], "B": [], "C": [], "D": [], "frentes": [], "resto": []}
for b in blocos:
    if is_tier_a(b):
        tiers["A"].append(b)
    elif b["alcance"] == "alto" and b["fechavel_12d"]:
        tiers["B"].append(b)
    elif b["alcance"] == "medio" and b["fechavel_12d"]:
        tiers["C"].append(b)
    elif b["alcance"] == "baixo" and b["fechavel_12d"]:
        tiers["D"].append(b)
    elif b["alcance"] == "alto" and b["urgencia"] >= 3 and not b["fechavel_12d"]:
        tiers["frentes"].append(b)
    else:
        tiers["resto"].append(b)

order = ["A", "B", "C", "D", "frentes", "resto"]
sprint_items = sum(sum(x["n_open"] for x in tiers[t]) for t in ["A", "B", "C", "D"])
sprint_blocks = sum(len(tiers[t]) for t in ["A", "B", "C", "D"])

print(f"Total aberto: {total_open} em {len(blocos)} blocos\n")
for t in order:
    n_blocks = len(tiers[t])
    n_items = sum(x["n_open"] for x in tiers[t])
    print(f"Tier {t}: {n_blocks} blocos, {n_items} itens")
print(f"\nSprint (A+B+C+D): {sprint_blocks} blocos, {sprint_items} itens = {sprint_items/total_open*100:.1f}% de {total_open}")

# resto: destacar os 2 maiores blocos sem emoji de alarme (alto alcance)
resto_sorted = sorted(tiers["resto"], key=lambda b: -b["n_open"])
print("\nMaiores blocos do resto (sem emoji de alarme, alto alcance):")
for b in resto_sorted[:6]:
    print(f"  {b['n_open']:>3} itens | alc={b['alcance']:<6} urg={b['urgencia']} | {b['title'][:80]}")

out = {"generated_from": IN_JSON, "tiers": tiers, "sprint_blocks": sprint_blocks, "sprint_items": sprint_items, "total_open": total_open}
with open(sys.argv[2] if len(sys.argv) > 2 else "tiers_sprint.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
