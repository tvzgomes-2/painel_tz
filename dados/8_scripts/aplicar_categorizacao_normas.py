#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aplica às notas de norma padronizada a categorização de 23/09/2026 (eixo 1 — instrumento da gratuidade).
Idempotente: pula nota que já tem 'categorizado_em:'. Backup em _meta/_backups/normas-categorizacao-<ts>/.
Fonte: _meta/scripts/_scratch/instrumentos/plano_correcao_normas.json."""
import json, os, re, shutil, datetime, sys, time
ND = "04 - Análises/Pesquisa legal/Normas padronizadas"
PLANO = "_meta/scripts/_scratch/instrumentos/plano_correcao_normas.json"
ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
BK = f"_meta/_backups/normas-categorizacao-{ts}"
MARK = {"direto": "✅ direto", "parcial": "🟡 parcial", "nao": "⬜ não"}
q = lambda s: json.dumps(s, ensure_ascii=False)
t0 = time.time(); feitos = pulados = mudou = 0
os.makedirs(BK, exist_ok=True)
for p in json.load(open(PLANO, encoding="utf-8")):
    if time.time() - t0 > 150: print("tempo — rodar de novo para continuar"); break
    f = os.path.join(ND, p["arquivo"])
    if not os.path.exists(f): print("AUSENTE", p["arquivo"]); continue
    t = open(f, encoding="utf-8").read()
    if "\ncategorizado_em:" in t: pulados += 1; continue
    assert t.startswith("---\n"), p["arquivo"]
    end = t.index("\n---", 4)
    fm, body = t[:end], t[end:]
    novos = [f"instrumento: {q(p['instrumento'])}", f"funcao_gratuidade: {q(p['funcao'])}", f"concede_gratuidade: {q(p['concede'])}"]
    if p["autorizativa"]: novos.append("autorizativa: true")
    if p["portao"]: novos.append(f"portao_no_texto: {q(p['portao'])}")
    novos.append("categorizado_em: 2026-09-23")
    nv = p["vinculo_new"]; old = (p["vinculo_old"] or "").strip()
    if nv:
        assert re.search(r"^vinculo_tz:.*$", fm, re.M), p["arquivo"]
        fm = re.sub(r"^vinculo_tz:.*$", f"vinculo_tz: {nv}  # corrigido em 23/09/2026 (era {old})", fm, count=1, flags=re.M)
        fm = re.sub(r"vinculo-(direto|parcial|nao|não|indireto)", f"vinculo-{nv}", fm, count=1)
        body, k = re.subn(r"^(\| \*\*Vínculo[^|]*\*\* \| ).*$", lambda m: m.group(1) + f"{MARK[nv]} (corrigido em 23/09/2026 — era {old}; ver Releitura) |", body, count=1, flags=re.M)
        mudou += 1
    fm = fm + "\n" + "\n".join(novos)
    linhas = [f"- **Instrumento:** {p['instrumento']} · **Função:** {p['funcao']} · **Concede gratuidade ao usuário:** {p['concede']} · **Leitura:** {p['leitura']}"]
    desc = [x for x in [("autorizativa" if p["autorizativa"] else ""), (f"prazo/condição: {p['prazo']}" if p["prazo"] else ""), (f"origem: {p['origem']}" if p["origem"] else ""), (f"portão no texto: {p['portao']}" if p["portao"] else "")] if x]
    if desc: linhas.append("- **Descrição:** " + "; ".join(desc))
    if p["trecho"]: linhas.append(f"- **Trecho decisivo:** \"{p['trecho']}\"")
    if nv: linhas.append(f"- ✅ **Correção aplicada:** `vinculo_tz` {old} → **{nv}** — a função do ato ({p['funcao']}) contradizia o vínculo registrado." + (f" Motivo apontado na releitura: {p['divergencia']}" if p["divergencia"] else ""))
    elif p["divergencia"]: linhas.append(f"- ⚠️ **A conferir:** {p['divergencia']}")
    sec = "## Releitura de 23/09/2026 (categorização — eixo 1)\n\n> Regra: [[Regras de classificacao das reguas]], Parte E. Categorização por releitura da própria nota, sem nova busca.\n\n" + "\n".join(linhas) + "\n\n"
    i = body.rfind("\n## Ligações")
    body = body[:i+1] + sec + body[i+1:] if i >= 0 else body.rstrip("\n") + "\n\n" + sec
    shutil.copy2(f, os.path.join(BK, p["arquivo"]))
    open(f, "w", encoding="utf-8", newline="\n").write(fm + body); feitos += 1
print(f"feitos {feitos} · já feitos {pulados} · vínculo corrigido {mudou} · backup {BK}")
