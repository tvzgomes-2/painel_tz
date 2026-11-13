# -*- coding: utf-8 -*-
"""
8.4 — extrai a legislacao da TZ por municipio do cofre para scripts/legislacao_tz.json

Fontes (cofre, 04 - Analises/Pesquisa legal/):
  Analise Legislacao Tarifa Zero.md      -> levantamento: 137 municipios, 62 com norma
  Analise das Legislacoes de Tarifa Zero.md -> analise de conteudo dos 62 (mecanismo, fundo)

Chave de saida: codigo IBGE (mesma dos crosswalks novos de Fase 11).

Exposicao: entra a norma, o ano, a confiabilidade, o mecanismo de gratuidade, o fundo
municipal e a ressalva de leitura. NAO entra a coluna "Zotero" (controle bibliografico
interno) nem os fragmentos de tarefa das observacoes ("consultar Camara", "ver .ris").
A ressalva em si ENTRA — diferente das notas de bibliografia que sairam em 11.3, aqui
ela e uma ressalva sobre o proprio dado exibido: mostrar "Lei 2.185/2006" para Marica
sem dizer que a fonte diverge seria pior que nao mostrar nada.
"""
# Fonte: cofre da tese (fora do git). Rode a partir da raiz do repositorio:
#   python3 scripts/build_legislacao.py
# Depois, para embutir no painel: python3 scripts/remontar_de_painel.py

import json, re, unicodedata
from pathlib import Path

VAULT = Path.home() / "mnt" / "doutorado" / "04 - Análises" / "Pesquisa legal"
REPO = Path.home() / "mnt" / "painel TZ"
OUT = REPO / "scripts" / "legislacao_tz.json"

def norm(s):
    s = unicodedata.normalize("NFD", (s or "").strip().lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

# ---------- 1. codigo IBGE a partir da base do painel ----------
html = (REPO / "painel.html").read_text(encoding="utf-8")
muni = json.loads(re.search(r'<script id="data-muni"[^>]*>(.*?)</script>', html, re.S).group(1))
idx = {c: n for n, c in enumerate(muni["cols"])}
por_nome = {}
for r in muni["data"]:
    por_nome[(norm(r[idx["nome"]]), r[idx["uf"]])] = str(r[idx["id"]])

# grafias que divergem entre o levantamento legal e a base municipal do painel
ALIAS = {
    ("arthur nogueira", "SP"): ("artur nogueira", "SP"),
    ("embu das artes", "SP"): ("embu", "SP"),
    ("santa isabel", "SP"): ("santa isabel", "SP"),
}

# ---------- 2. levantamento: tabela de 137 ----------
txt = (VAULT / "Analise Legislacao Tarifa Zero.md").read_text(encoding="utf-8")
linhas = [l for l in txt.splitlines() if l.startswith("|")]

LIXO = [
    r"\s*Consultar\s+C[âa]mara[^.]*\.?", r"\s*Verificar\s+C[âa]mara[^.]*\.?",
    r"\s*Confirmar em arquivo municipal\.?", r"\s*\(pendente\s*[–-]\s*ver \.ris\)",
    r"\s*Candidata:\s*verificar[^.]*\.?", r"\s*Rever\.\s*",
]

registros, sem_match = {}, []
for l in linhas:
    c = [x.strip() for x in l.strip().strip("|").split("|")]
    if len(c) != 8 or not c[0].isdigit():
        continue
    _, municipio, uf, ano, lei, conf, _zotero, obs = c   # coluna Zotero descartada
    chave = ALIAS.get((norm(municipio), uf), (norm(municipio), uf))
    cod = por_nome.get(chave)
    if not cod:
        sem_match.append(f"{municipio}/{uf}")
        continue
    lei = re.sub(r"\s+", " ", lei).strip()
    tem_norma = bool(lei) and norm(lei) != "nao encontrei"
    for p in LIXO:
        obs = re.sub(p, "", obs, flags=re.I)
    # "Confirmado (alta)" repete o que a etiqueta de confiabilidade ja diz
    obs = re.sub(r"^\s*Confirmado\s*\((alta|m[ée]dia|baixa)\)\.?\s*", "", obs, flags=re.I)
    obs = re.sub(r"\s+", " ", obs).strip(" .;") or None
    reg = {"norma": lei if tem_norma else None,
           "ano": int(ano) if ano.isdigit() else None,
           "conf": (conf if conf and conf != "—" else None),
           "nota": obs}
    registros[cod] = {k: v for k, v in reg.items() if v is not None}

# ---------- 3. analise de conteudo: mecanismo e fundo ----------
txt2 = (VAULT / "Analise das Legislacoes de Tarifa Zero.md").read_text(encoding="utf-8")

def cidades_da_lista(trecho):
    trecho = re.sub(r"\([^)]*\)", "", trecho)          # tira parenteses explicativos
    trecho = re.sub(r"\*\*|\*|_", "", trecho)
    partes = re.split(r"[,;.]| e ", trecho)
    return [p.strip() for p in partes if p.strip()]

MECANISMOS = [
    (r"\*\*Subvenção/subsídio econômico à operadora\*\*[^:]*:([^\n]+)", "Subvenção à operadora"),
    (r"\*\*Tarifa fixada em R\$ ?0,00 por decreto tarifário\*\*[^:]*:([^\n]+)", "Tarifa fixada em R$ 0,00"),
    (r"\*\*Custeio integral / gestão direta com vedação de cobrança\*\*[^:]*:([^\n]+)", "Custeio integral / gestão direta"),
]
achou_mec = 0
for pat, rotulo in MECANISMOS:
    m = re.search(pat, txt2)
    if not m:
        print(f"  [aviso] lista de mecanismo nao encontrada: {rotulo}")
        continue
    for cidade in cidades_da_lista(m.group(1)):
        for (n_, uf_), cod in por_nome.items():
            if n_ == norm(cidade) and cod in registros:
                registros[cod]["mecanismo"] = rotulo
                achou_mec += 1
                break

m = re.search(r"\*\*Fundo municipal criado/vinculado NA PRÓPRIA LEI:\*\*([^\n]+)", txt2)
achou_fundo = 0
if m:
    for cidade in cidades_da_lista(m.group(1)):
        for (n_, uf_), cod in por_nome.items():
            if n_ == norm(cidade) and cod in registros:
                registros[cod]["fundo"] = True
                achou_fundo += 1
                break

OUT.write_text(json.dumps(registros, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
                encoding="utf-8")

com_norma = sum(1 for v in registros.values() if v.get("norma"))
print(f"legislacao_tz.json: {len(registros)} municipios casados por codigo IBGE "
      f"({com_norma} com norma identificada, {len(registros)-com_norma} sem)")
print(f"  mecanismo de gratuidade: {achou_mec} | fundo criado na lei: {achou_fundo}")
print(f"  confiabilidade: " + ", ".join(
    f"{c}={sum(1 for v in registros.values() if v.get('conf')==c)}" for c in ("alta","média","baixa")))
if sem_match:
    print(f"  NAO casados ({len(sem_match)}): {', '.join(sem_match)}")
print(f"  tamanho: {OUT.stat().st_size/1024:.0f} KB")
