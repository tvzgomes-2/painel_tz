#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Classifica os blocos de Pendências.md por urgência (já marcada pelo autor,
via emoji) e alcance (amplitude no texto + poder de bloqueio de outras
pendências), para priorizar o fechamento de ~30% até 15/09/2026.
Read-only: só lê Pendências.md e escreve um CSV/JSON de saída em outro caminho.
"""
import re, json, sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "Pendências.md"
OUT_JSON = sys.argv[2] if len(sys.argv) > 2 else "classificacao_pendencias.json"

with open(PATH, encoding="utf-8") as f:
    lines = f.read().split("\n")

# localizar o início da seção temática
theme_start = None
for i, l in enumerate(lines):
    if l.strip() == "## Pendências por tema":
        theme_start = i
        break

CANON_KW = re.compile(r"canônic|base-?mestre|universo (canônico|ampliado|mapeado)|régua (descritiva|anal[ií]tica)|propagar|hipótese central|hip[oó]tese e pressupostos", re.I)
DECISAO_KW = re.compile(r"decis[ãa]o do autor", re.I)
BLOCKED_KW = re.compile(r"e-sic|cota esgotada|rodado localmente|aguardando|precisa ser rodado|projeto google cloud pr[oó]prio|cota parece ser compartilhada", re.I)
CAP_KW = re.compile(r"\bCap\.?\s?(\d)\b")

def emoji_urgencia(title):
    # ordem importa: mais emojis de alerta = mais urgente
    if "🚨🚨🚨" in title: return 5
    if "🚨🚨" in title: return 4
    if "🔴" in title: return 3
    if "🚨" in title: return 3
    if "🟠" in title: return 2
    if "⚠️" in title or "⚠" in title: return 2
    if "🔵" in title or "🔎" in title or "🌐" in title or "📄" in title or "📇" in title: return 1
    if "✅" in title or "🟢" in title: return 1
    return 1

def classify_block(title, body_lines):
    body = "\n".join(body_lines)
    n_open = sum(1 for l in body_lines if re.match(r"^\s*- \[ \]", l))
    n_done = sum(1 for l in body_lines if re.match(r"^\s*- \[x\]", l))
    caps = sorted(set(CAP_KW.findall(body)))
    has_canon = bool(CANON_KW.search(body)) or bool(CANON_KW.search(title))
    has_decisao = bool(DECISAO_KW.search(body))
    has_blocked = bool(BLOCKED_KW.search(body))
    n_caps = len(caps)
    if has_canon or n_caps >= 2:
        alcance = "alto"
    elif n_caps == 1:
        alcance = "medio"
    else:
        alcance = "baixo"
    urgencia = emoji_urgencia(title)
    # fechável em ~12 dias: poucos itens, decisão do autor, e não bloqueado por terceiros/externos
    # v2 (corrigido 03/09): "decisão do autor" isolado NAO torna um bloco fechavel
    # -- bloco de 20+ itens com essa frase no corpo era marcado fechavel por engano.
    # fechavel agora e so tamanho (<=5 itens abertos) + sem trava externa.
    fechavel = (not has_blocked) and (n_open <= 5) and n_open > 0
    return {
        "title": title.strip(),
        "n_open": n_open, "n_done": n_done,
        "capitulos": caps, "n_capitulos": n_caps,
        "alcance": alcance, "urgencia": urgencia,
        "tem_decisao_autor": has_decisao, "bloqueado_externo": has_blocked,
        "fechavel_12d": fechavel,
    }

blocks = []

# ---- 1) seção "rodada" (log datado, headers "## ") ----
i = 1
rodada_lines = lines[:theme_start] if theme_start else lines
idx = [n for n, l in enumerate(rodada_lines) if l.startswith("## ")]
for k, start in enumerate(idx):
    end = idx[k+1] if k+1 < len(idx) else len(rodada_lines)
    title = rodada_lines[start][3:]
    body = rodada_lines[start+1:end]
    b = classify_block(title, body)
    b["secao"] = "rodada"
    b["tema"] = None
    blocks.append(b)

# ---- 2) seção temática ("### Tema" > "**status (data) — desc**" batches) ----
if theme_start:
    theme_lines = lines[theme_start:]
    theme_idx = [n for n, l in enumerate(theme_lines) if l.startswith("### ")]
    for tk, tstart in enumerate(theme_idx):
        tend = theme_idx[tk+1] if tk+1 < len(theme_idx) else len(theme_lines)
        tema = theme_lines[tstart][4:].strip()
        sub = theme_lines[tstart+1:tend]
        batch_idx = [n for n, l in enumerate(sub) if l.strip().startswith("**") ]
        if not batch_idx:
            b = classify_block(tema, sub)
            b["secao"] = "tema"; b["tema"] = tema
            blocks.append(b)
            continue
        # conteúdo antes do primeiro batch marcado (ex.: link para histórico) -> ignorar como bloco à parte
        for bk, bstart in enumerate(batch_idx):
            bend = batch_idx[bk+1] if bk+1 < len(batch_idx) else len(sub)
            title = sub[bstart].strip()
            body = sub[bstart+1:bend]
            b = classify_block(title, body)
            b["secao"] = "tema"; b["tema"] = tema
            blocks.append(b)

# ---- prioridade: urgencia desc, depois alcance (alto>medio>baixo), depois fechavel primeiro ----
alcance_rank = {"alto": 3, "medio": 2, "baixo": 1}
for b in blocks:
    b["prioridade"] = b["urgencia"] * 10 + alcance_rank[b["alcance"]] * 3 + (2 if b["fechavel_12d"] else 0)

blocks_com_itens = [b for b in blocks if b["n_open"] > 0]
blocks_com_itens.sort(key=lambda b: -b["prioridade"])

total_open = sum(b["n_open"] for b in blocks_com_itens)
total_done = sum(b["n_done"] for b in blocks)

with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
    json.dump({
        "total_blocos": len(blocks_com_itens),
        "total_open": total_open,
        "total_done": total_done,
        "blocos": blocks_com_itens,
    }, f, ensure_ascii=False, indent=1)

print(f"Blocos com itens abertos: {len(blocks_com_itens)}")
print(f"Total itens abertos (soma dos blocos): {total_open}")
print(f"Total itens concluídos (nos blocos, não migrados p/ Arquivo): {total_done}")

# resumo por alcance x urgencia
from collections import Counter
c = Counter((b["alcance"], b["urgencia"]) for b in blocks_com_itens)
print("\n(alcance, urgencia) -> n_blocos:")
for k in sorted(c, key=lambda x: (-x[1], {"alto":0,"medio":1,"baixo":2}[x[0]])):
    print(f"  {k}: {c[k]}")

print("\nTop 20 blocos por prioridade:")
for b in blocks_com_itens[:20]:
    print(f"  [{b['prioridade']:>3}] urg={b['urgencia']} alc={b['alcance']:<6} abertos={b['n_open']:<3} decisao={'S' if b['tem_decisao_autor'] else '-'} bloq={'S' if b['bloqueado_externo'] else '-'} cap={b['capitulos']}  {b['title'][:90]}")
