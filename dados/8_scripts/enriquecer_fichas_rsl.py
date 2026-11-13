#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""enriquecer_fichas_rsl.py — insere, em cada ficha municipal, a seção
"## Literatura da RSL": o que a literatura lida diz do caso, ou o registro
verificado de que não diz nada.

DECISÕES DO AUTOR (03/09/2026):
  * nível A (objeto) e B (seção substantiva) recebem a seção na ficha;
  * os 9 casos de nível A recebem PROSA CURADA, lida de
    `05 - Referências/Rede bibliométrica/prosa_literatura_municipios.md`;
  * municípios SEM nenhuma menção recebem a linha de ausência verificada —
    é o que separa "não há literatura" de "não procurei";
  * nível C recebe uma linha honesta de menção de passagem. Isso é decisão
    do script, não do autor: sem ela, a ficha de nível C ficaria idêntica à
    de ausência verificada, e a informação se perderia.

ENTRADAS  05 - Referências/Rede bibliométrica/cobertura_literatura_municipios.csv
            (gerado por mapear_rsl_municipios.py)
          05 - Referências/Rede bibliométrica/prosa_literatura_municipios.md
SAÍDA     escreve nas fichas de 04 - Análises/Casos municipais/Fichas por município/

IDEMPOTENTE: a seção é substituída, não duplicada.
NÃO MEXE nas seções numeradas 1-5 nem na numeração — a seção é inserida SEM
número, imediatamente antes de "## Ligações", pelo mesmo padrão de
enriquecer_fichas_municipais.py (o exportador `exportar_anexo.py` lê
"## 1." a "## 5." por regex e não é afetado).

USO   python3 _meta/scripts/enriquecer_fichas_rsl.py            (grava)
      python3 _meta/scripts/enriquecer_fichas_rsl.py --simular  (não grava)
"""
import collections, csv, datetime, glob, os, re, shutil, sys, unicodedata

R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FICHAS = os.path.join(R, "04 - Análises", "Casos municipais", "Fichas por município")
REDE   = os.path.join(R, "05 - Referências", "Rede bibliométrica")
CSV_IN = os.path.join(REDE, "cobertura_literatura_municipios.csv")
PROSA  = os.path.join(REDE, "prosa_literatura_municipios.md")

SECAO = "## Literatura da RSL"
DATA  = datetime.date.today().strftime("%d/%m/%Y")  # antes fixo em 03/09/2026; passou a ser a data da rodada (25/09/2026)
SIMULAR = "--simular" in sys.argv
# 30/09/2026: --so "Município" UF [--so ...] restringe a fichas específicas; grava só o que mudou além da data
SO = set(); _a = sys.argv
for _i, _x in enumerate(_a):
    if _x == "--so" and _i + 2 <= len(_a) - 1: SO.add((_a[_i + 1], _a[_i + 2]))
DATA_RE = r"(?i)verificad[ao] em \d{2}/\d{2}/\d{4}"
_SEMDATA = lambda x: re.sub(r"\n{2,}", "\n\n", re.sub(DATA_RE, "", x)).strip()
GRAV = []

def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()

def curto(arq):
    return arq.replace("Fichamento - ", "").replace(".md", "").split(" — ")[0].strip()

def ler_cobertura():
    reg = collections.defaultdict(list)
    nivel = {}
    if not os.path.exists(CSV_IN):
        sys.exit("faltando %s — rodar mapear_rsl_municipios.py primeiro" % os.path.basename(CSV_IN))
    for r in csv.DictReader(open(CSV_IN, encoding="utf-8"), delimiter=";"):
        k = (norm(r["municipio"]), norm(r["uf"]))
        reg[k].append((r["fichamento"], int(r["mencoes"]), r["nivel_par"]))
        nivel[k] = r["nivel_municipio"]
    return reg, nivel

def ler_prosa():
    if not os.path.exists(PROSA): return {}
    txt = open(PROSA, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"^###\s+(.+?)\s*\((\w{2})\)\s*$", txt, re.M):
        ini = m.end()
        nxt = txt.find("\n### ", ini)
        corpo = txt[ini: nxt if nxt != -1 else len(txt)].strip()
        if corpo: out[(norm(m.group(1)), norm(m.group(2)))] = corpo
    return out

def bloco(k, reg, nivel, prosa, total_fich):
    itens = sorted(reg.get(k, []), key=lambda x: -x[1])
    nv = nivel.get(k)
    L = [SECAO + f" (cobertura verificada em {DATA})", ""]
    if not itens:
        L += ["⚠️ **Nenhuma literatura acadêmica localizada trata deste caso.** "
              f"Verificado em {DATA} contra os **{total_fich} fichamentos** da revisão "
              "sistemática — o nome do município não aparece uma única vez.",
              "",
              "🔴 **A ausência é achado, não lacuna de registro:** dos municípios em escopo da "
              "base-mestre, a maioria não é mencionada por nenhuma obra lida. ➡️ Ver "
              "[[Cobertura da literatura por município (gerado)]].",
              "",
              "⚠️ Isso mede a literatura **lida até aqui** (fichamentos). Os estratos da RSL — bases indexadas e "
              "acervo técnico-setorial (ANTP) — foram executados e fechados em 12/09/2026, com limitações de acesso "
              "declaradas — ver [[Saneamento das pendências da RSL — 12-09-2026]]."]
        return "\n".join(L) + "\n"
    if nv == "C":
        nomes = "; ".join(f"{curto(a)}" for a, c, _l in itens[:6])
        L += [f"⚠️ **Citado de passagem, sem análise do caso.** O município aparece em "
              f"**{len(itens)} fichamento(s)** com 1-2 menções cada — o suficiente para constar de "
              f"uma lista, não para caracterizar tratamento: {nomes}.",
              "",
              "🔴 **Nível pouco confiável por construção:** uma ou duas ocorrências não distinguem "
              "caso analisado de nome em enumeração. **Conferir antes de citar.** ➡️ "
              "[[Cobertura da literatura por município (gerado)]]."]
        return "\n".join(L) + "\n"
    rot = {"A": "**objeto** de pelo menos uma obra", "B": "**seção substantiva** de pelo menos uma obra"}[nv]
    L += [f"**Cobertura:** nível **{nv}** — {rot} · aparece em **{len(itens)} dos {total_fich} fichamentos**.", ""]
    p = prosa.get(k)
    if p: L += [p, ""]
    L += ["**Onde aparece** — obra (menções no fichamento):", ""]
    for a, c, lv in itens:
        marca = {"A": "🔴", "B": "✅", "C": "·"}[lv]
        L.append(f"- {marca} {curto(a)} — {c}")
    L += ["",
          "⚠️ **O que a contagem é e o que não é:** ela conta menções nos **fichamentos**, que são "
          "notas de leitura do autor, não nos textos originais. Um caso pode aparecer muito na nota "
          "porque interessou ao leitor. **Indício de cobertura, não prova dela.** ➡️ "
          "[[Cobertura da literatura por município (gerado)]] · "
          "[[Revisão sistemática — base, corpus e revisão crítica]]."]
    return "\n".join(L) + "\n"

_BACKUP_DIR = None  # criado sob demanda no 1º arquivo realmente gravado


def _backup_antes_de_gravar(path):
    """Copia o conteúdo atual de `path` para _meta/_backups/ antes de sobrescrever,
    seguindo o mesmo padrão dos demais scripts enriquecer_*.py."""
    global _BACKUP_DIR
    if _BACKUP_DIR is None:
        _BACKUP_DIR = os.path.join(
            R, "_meta", "_backups",
            "fichas-rsl-" + datetime.datetime.now().strftime("%Y-%m-%d_%H%M"),
        )
        os.makedirs(_BACKUP_DIR, exist_ok=True)
    shutil.copy2(path, os.path.join(_BACKUP_DIR, os.path.basename(path)))


def main():
    reg, nivel = ler_cobertura()
    prosa = ler_prosa()
    total_fich = len(glob.glob(os.path.join(R, "05 - Referências", "Nota de leitura", "Fichamento*.md"))) or \
                 len(glob.glob(os.path.join(R, "05 - Referências", "Notas de leitura", "Fichamento*.md")))
    cont = collections.Counter(); semfm = []
    usados = set()
    for p in sorted(glob.glob(os.path.join(FICHAS, "*.md"))):
        if "BACKUP" in os.path.basename(p): continue
        t = open(p, encoding="utf-8").read(); orig = t
        m = re.search(r"^municipio:\s*(.+)$", t, re.M); u = re.search(r"^uf:\s*(.+)$", t, re.M)
        if not m:
            semfm.append(os.path.basename(p)); continue
        if SO and (norm(m.group(1)), norm(u.group(1)) if u else "") not in {(norm(x), norm(y)) for x, y in SO}: continue
        k = (norm(m.group(1)), norm(u.group(1)) if u else "")
        nv = nivel.get(k)
        if nv == "C": cont["C"] += 1
        elif nv in ("A", "B"): cont[nv] += 1
        else: cont["ausente"] += 1
        usados.add(k)
        novo = bloco(k, reg, nivel, prosa, total_fich)
        # remove seção anterior (idempotência)
        t = re.sub(r"\n" + re.escape(SECAO) + r".*?(?=\n## |\Z)", "\n", t, flags=re.S)
        if "\n## Ligações" in t:
            t = t.replace("\n## Ligações", "\n" + novo + "\n## Ligações", 1)
        else:
            t = t.rstrip() + "\n\n" + novo
        t = re.sub(r"\n{4,}", "\n\n\n", t)
        # 30/09/2026: só grava se algo além do carimbo de data mudou (a rodada reescrevia as fichas todas só pela data)
        if _SEMDATA(t) == _SEMDATA(orig): continue
        GRAV.append(os.path.basename(p))
        if os.environ.get("RSL_DIFF") and len(GRAV) <= 2:
            import difflib; print("".join(list(difflib.unified_diff(orig.splitlines(1), t.splitlines(1), n=1))[:40]))
        if not SIMULAR:
            _backup_antes_de_gravar(p)
            open(p, "w", encoding="utf-8", newline="\n").write(t)
    print(("SIMULAÇÃO — nada gravado. " if SIMULAR else "") +
          f"fichas: A {cont['A']} · B {cont['B']} · C {cont['C']} · ausência verificada {cont['ausente']}" + f" · alteradas: {len(GRAV)} {GRAV[:8]}")
    print("prosa curada aplicada em", len([k for k in prosa if k in usados]), "de", len(prosa), "blocos")
    faltam = [k for k in prosa if k not in usados]
    if faltam: print("AVISO: prosa sem ficha correspondente:", faltam)
    if semfm: print("AVISO: fichas sem frontmatter municipio:", semfm)
    print("fichamentos contados:", total_fich)

if __name__ == "__main__":
    main()
