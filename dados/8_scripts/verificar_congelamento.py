#!/usr/bin/env python3
"""verificar_congelamento.py — compara a base viva com o congelamento vigente (o mais recente em 03 - Dados/_data/congelamento-*) e cobra justificativa.
Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni · escrito em 11/10/2026.

Compara, célula a célula, a aba 'consolidado' da base-mestre e as abas da régua com as cópias em
'03 - Dados/_data/congelamento-<data>/' (o mais recente). Cada diferença em coluna de DADO tem de ter linha no
'03 - Dados/Registro de alterações pós-congelamento.md' (mesmo município/UF, planilha e campo).
Colunas DERIVADAS (geradas por script a partir das outras) aparecem à parte e não exigem registro próprio.
Também confere o SHA-256 das cópias congeladas (MANIFESTO-sha256.txt): se mudou, o congelamento foi violado.
Uso (da raiz do cofre): python _meta/scripts/verificar_congelamento.py   → imprime o relatório; não grava nada."""
import os, re, sys, hashlib, unicodedata, openpyxl
R = os.getcwd()
# 17/10/2026: lê o congelamento mais recente (congelar_base.py grava um novo; os anteriores ficam intactos)
FZ = os.path.join(R, "03 - Dados", "_data", sorted(x for x in os.listdir(os.path.join(R, "03 - Dados", "_data")) if x.startswith("congelamento-"))[-1])
VIVO = {"mestre": os.path.join(R, "03 - Dados", "_data", "casos por fonte", "Municípios TZ - consolidado.xlsx"),
        "régua": os.path.join(R, "03 - Dados", "_data", "casos por fonte", "Tipologias TZ - consolidado.xlsx")}
CONG = {"mestre": os.path.join(FZ, "Municípios TZ - consolidado.xlsx"), "régua": os.path.join(FZ, "Tipologias TZ - consolidado.xlsx")}
REG = os.path.join(R, "03 - Dados", "Registro de alterações pós-congelamento.md")
DERIV = {"Estado terminal (completude)", "Norma lida (A.2e)", "Situação unificada (controle)", "Consolidado em",
         "Ficha — status", "Ficha — completude (0-6)", "Dados operacionais (ficha §2)", "Trajetória (régua descritiva, ficha)",
         # 17/10/2026: as 4 colunas do cruzamento operador × grupo são geradas por cruzar_operador_grupo.py a partir de Operador e Operador — CNPJ
         "Operador × GE — resultado (cruzamento)", "Operador × GE — ligação", "Operador × GE — sugestão por nome (a conferir)", "Operador × GE — data",
         # 17/10/2026: contrapartida em três estados (regra B.1.3), gerada por codificar_contrapartida.py a partir de Contrapartida
         "Contrapartida — estado", "Contrapartida — itens", "Contrapartida — leitura"}
def nz(s): return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()
def tab(p, sh):
    ws = openpyxl.load_workbook(p, read_only=True)[sh]; rows = list(ws.iter_rows(values_only=True))
    h = [str(x) for x in rows[0]]; d = {}
    for r in rows[1:]:
        if not r or not r[0]: continue
        k = (nz(r[0]), str(r[1])); d.setdefault(k, []).append({h[i]: r[i] for i in range(min(len(h), len(r)))})
    return d
# 1. integridade do congelamento
ok = True
for ln in open(os.path.join(FZ, "MANIFESTO-sha256.txt"), encoding="utf-8"):
    hx, nome = ln.strip().split("  ", 1)
    if hashlib.sha256(open(os.path.join(FZ, nome), "rb").read()).hexdigest() != hx: ok = False; print("⚠️ cópia congelada alterada:", nome)
print("Integridade do congelamento:", "OK" if ok else "VIOLADA")
# 2. registro
regs = set()
if os.path.exists(REG):
    for ln in open(REG, encoding="utf-8"):
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        if len(c) >= 7 and re.match(r"\d{2}/\d{2}/\d{4}", c[0]):
            mu, uf = (c[1].rsplit("/", 1) + [""])[:2]
            regs.add((nz(mu), uf.strip(), c[2].strip().lower(), nz(c[3])))
# 3. diferenças
sem, com, der = [], [], []
pares = [("mestre", "consolidado")] + [("régua", s) for s in openpyxl.load_workbook(CONG["régua"], read_only=True).sheetnames if s != "RESUMO"]
for pl, sh in pares:
    a, b = tab(CONG[pl], sh), tab(VIVO[pl], sh)
    for k in sorted(set(a) | set(b)):
        if k not in a: sem.append((pl, sh, k, "(linha nova)", "", "")) if (nz(k[0]), k[1], pl, nz("linha")) not in regs else com.append(k); continue
        if k not in b:  # 16/10/2026: linha MOVIDA (está noutra aba viva e há linha "linha" no Registro) é aceita; apagada segue proibida
            if pl == "régua" and any(k in tab(VIVO[pl], s2) for s2 in openpyxl.load_workbook(VIVO[pl], read_only=True).sheetnames if s2 not in (sh, "RESUMO")) and (nz(k[0]), k[1], pl, nz("linha")) in regs: com.append(k)
            else: sem.append((pl, sh, k, "(linha removida — proibido: mover, nunca apagar)", "", ""))
            continue
        for ra, rb in zip(a[k], b[k]):
            for col in set(ra) | set(rb):
                va, vb = ra.get(col), rb.get(col)
                if str(va if va is not None else "") == str(vb if vb is not None else ""): continue
                item = (pl, sh, k, col, str(va)[:60], str(vb)[:60])
                if col in DERIV: der.append(item)
                elif (k[0], k[1], pl, nz(col)) in regs: com.append(item)
                else: sem.append(item)
print(f"Diferenças registradas: {len(com)} · derivadas: {len(der)} · SEM REGISTRO: {len(sem)}")
for it in sem: print("  SEM REGISTRO →", it[0], "|", it[1], "|", f"{it[2][0]}/{it[2][1]}", "|", it[3], "|", it[4], "→", it[5])
sys.exit(1 if (sem or not ok) else 0)
