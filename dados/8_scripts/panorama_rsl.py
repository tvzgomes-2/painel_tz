#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
panorama_rsl.py — panorama do ACERVO completo da RSL (183 registros),
antes do recorte para o corpus estrito de 81 itens (RSL1-4).

Complementa rede_bibliometrica.py (que opera só sobre o corpus de 81): aqui a
população é o acervo inteiro, tal como veio da busca — todo procedimento de
entrada (busca em base, bola de neve, dossiê temático, acervo prévio) e todo
desfecho (fichado, excluído, reclassificado, indisponível).

ENTRADA   05 - Referências/Rede bibliométrica/corpus_rsl.csv
SAÍDAS    _attachments/rsl_achados_por_ano.svg
          _attachments/rsl_funil_identificacao.svg

Estilo: SVG escrito à mão, cores fixas em hex, fundo branco, sem título nem
Fonte embutidos (Design System das Figuras, claude/design-system-figuras-
2026-09-16) — mesma convenção de rede_bibliometrica.py. Paleta categórica
validada do design system: #FF2D6B (rosa) · #1A54C7 (azul) · #326F00 (verde
escuro) · #BAAD00 (amarelo escuro) · #787880 (cinza, "outros"/fora do fluxo
principal) — teto de 4 categorias por medição de contraste/daltonismo.
"""
import csv, io, sys

CSV = "05 - Referências/Rede bibliométrica/corpus_rsl.csv"
OUT_ANO = "_attachments/rsl_achados_por_ano.svg"
OUT_FUNIL = "_attachments/rsl_funil_identificacao.svg"

AZUL = "#1A54C7"
ROSA = "#FF2D6B"
VERDE = "#326F00"
AMARELO = "#BAAD00"
CINZA = "#787880"
CINZA_CLARO = "#e4e4e4"

FONTE_CSS = '<style>text{font-family:Aptos,Calibri,Helvetica,Arial,sans-serif}</style>'


def carregar():
    with open(CSV, "rb") as f:
        raw = f.read()
    txt = raw.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(txt), delimiter=";"))


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
# Figura 1 — achados por ano (183 itens, todo o acervo)
# ---------------------------------------------------------------------------
def fig_achados_por_ano(rows):
    anos = {}
    for r in rows:
        a = (r.get("ano") or "").strip()
        if not a.isdigit():
            continue
        anos[int(a)] = anos.get(int(a), 0) + 1
    assert sum(anos.values()) == len([r for r in rows if (r.get("ano") or "").strip().isdigit()])

    ano_min, ano_max = min(anos), max(anos)
    serie = [(y, anos.get(y, 0)) for y in range(ano_min, ano_max + 1)]
    total = sum(c for _, c in serie)

    W, H, M_L, M_R, M_T, M_B = 1400, 560, 70, 30, 30, 110
    plot_w, plot_h = W - M_L - M_R, H - M_T - M_B
    n = len(serie)
    bw = plot_w / n
    ymax = max(c for _, c in serie)
    ymax_axis = ((ymax // 5) + 1) * 5

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>', FONTE_CSS]

    # grade horizontal + rótulos do eixo Y
    passos_y = 5
    for i in range(passos_y + 1):
        val = ymax_axis * i / passos_y
        y = M_T + plot_h - (val / ymax_axis) * plot_h
        o.append(f'<line x1="{M_L}" y1="{y:.1f}" x2="{W-M_R}" y2="{y:.1f}" stroke="{CINZA_CLARO}" stroke-width="1"/>')
        o.append(f'<text x="{M_L-10}" y="{y+4:.1f}" font-size="12" text-anchor="end" fill="#555555">{val:.0f}</text>')

    # barras
    for i, (ano, c) in enumerate(serie):
        x = M_L + i * bw
        h = (c / ymax_axis) * plot_h if ymax_axis else 0
        y = M_T + plot_h - h
        o.append(f'<rect x="{x+bw*0.12:.2f}" y="{y:.1f}" width="{bw*0.76:.2f}" height="{h:.1f}" fill="{AZUL}"/>')
        rotulo = str(ano) if ano % 5 == 0 or ano in (ano_min, ano_max) else ""
        if rotulo:
            cx = x + bw / 2
            o.append(f'<text x="{cx:.1f}" y="{M_T+plot_h+18}" font-size="11" text-anchor="end" '
                      f'fill="#333333" transform="rotate(-45 {cx:.1f} {M_T+plot_h+18})">{rotulo}</text>')

    o.append(f'<line x1="{M_L}" y1="{M_T+plot_h:.1f}" x2="{W-M_R}" y2="{M_T+plot_h:.1f}" stroke="#999999" stroke-width="1"/>')
    o.append(f'<text x="{M_L}" y="{H-16}" font-size="10.5" fill="#777777">'
              f'{total} registros do acervo, todos com ano preenchido — cada barra é um ano de publicação, '
              f'inclui itens depois excluídos, reclassificados ou fora do corpus estrito (ver funil ao lado).</text>')

    o.append("</svg>")
    with open(OUT_ANO, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(o))
    print(f"[ano] {total} itens, {ano_min}-{ano_max}, pico em {max(serie, key=lambda t: t[1])}")


# ---------------------------------------------------------------------------
# Figura 2 — funil de identificação (PRISMA-like), 183 -> 81
# ---------------------------------------------------------------------------
def fig_funil(rows):
    total = len(rows)

    proc = {}
    for r in rows:
        p = (r.get("procedimento") or "").strip() or "(vazio)"
        proc[p] = proc.get(p, 0) + 1
    principais = ["busca_de_base", "bola_de_neve", "enumeracao_de_volume"]
    outros_proc = total - sum(proc.get(p, 0) for p in principais)
    assert outros_proc == proc.get("acervo_previo", 0) + proc.get("decisao_documentada", 0) + \
           proc.get("contato_direto", 0) + proc.get("capes_legado_1987_2012", 0) + proc.get("(vazio)", 0)

    estado = {}
    for r in rows:
        e = (r.get("estado") or "").strip()
        estado[e] = estado.get(e, 0) + 1
    fichado = estado.get("fichado", 0)
    excluido = estado.get("excluido_apos_leitura", 0)
    reclass = estado.get("reclassificado_db", 0)
    indisp = estado.get("indisponivel", 0)
    assert fichado + excluido + reclass + indisp == total

    corpus = [r for r in rows if r.get("estrato") in ("RSL1", "RSL2", "RSL3", "RSL4") and r.get("estado") == "fichado"]
    n_corpus = len(corpus)
    fichado_fora = fichado - n_corpus
    assert n_corpus == 81, n_corpus

    W, H = 1180, 600
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>', FONTE_CSS,
         '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
         'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#555555"/></marker></defs>']

    def box(x, y, w, h, fill, stroke, linhas, fs_top=15, fs_rest=12.5, text_color="#1a1a1a"):
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>')
        cy = y + 30
        for i, (txt, fs, bold, col) in enumerate(linhas):
            weight = ' font-weight="700"' if bold else ""
            o.append(f'<text x="{x+w/2:.1f}" y="{cy:.1f}" font-size="{fs}"{weight} text-anchor="middle" fill="{col}">{esc(txt)}</text>')
            cy += fs + 10

    def seta(x1, y1, x2, y2):
        o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#555555" stroke-width="1.6" marker-end="url(#a)"/>')

    CW, CX = 580, 40              # coluna principal (fluxo)
    SW, SX = 460, CX + CW + 50    # coluna lateral (excluídos a cada etapa)

    # Etapa 1 — identificação
    y1 = 30
    box(CX, y1, CW, 110, "#eef2fb", AZUL, [
        (f"Identificados — {total} registros", 16, True, AZUL),
        ("todo o acervo lido pela revisão, qualquer desfecho", 12.5, False, "#333333"),
        (f"busca em base {proc.get('busca_de_base',0)} · bola de neve {proc.get('bola_de_neve',0)} · "
         f"dossiês temáticos {proc.get('enumeracao_de_volume',0)} · outros {outros_proc}", 11.5, False, "#555555"),
    ])
    y2 = y1 + 110 + 70
    seta(CX + CW/2, y1+110, CX + CW/2, y2)

    # Etapa 2 — desfecho (estado)
    box(CX, y2, CW, 110, "#eef2fb", AZUL, [
        (f"Fichados — {fichado}", 16, True, AZUL),
        ("texto lido e registrado, qualquer estrato", 12.5, False, "#333333"),
    ])
    # lateral: removidos do acervo
    box(SX, y2, SW, 130, "#f2f2f4", CINZA, [
        (f"Não seguem — {excluido+reclass+indisp}", 15, True, CINZA),
        (f"excluídos com motivo registrado: {excluido}", 12, False, "#444444"),
        (f"reclassificados p/ banco de dados: {reclass}", 12, False, "#444444"),
        (f"indisponível (acesso): {indisp}", 12, False, "#444444"),
    ])
    seta(CX + CW, y2 + 55, SX, y2 + 55)

    y3 = y2 + 110 + 70
    seta(CX + CW/2, y2+110, CX + CW/2, y3)

    # Etapa 3 — corpus da revisão
    box(CX, y3, CW, 120, "#ffe6ee", ROSA, [
        (f"Corpus da revisão (RSL1-4) — {n_corpus} itens", 17, True, "#9E1B42"),
        ("pertence a um dos 4 estratos declarados — população", 12.5, False, "#333333"),
        ("citada no resto deste anexo e no Cap 5", 12.5, False, "#333333"),
    ])
    box(SX, y3, SW, 100, "#f2f2f4", CINZA, [
        (f"Fichado fora dos 4 estratos — {fichado_fora}", 14.5, True, CINZA),
        ("bola de neve / acervo prévio sem estrato atribuído;", 11.5, False, "#444444"),
        ("não entra na contagem do corpus", 11.5, False, "#444444"),
    ])
    seta(CX + CW, y3 + 50, SX, y3 + 50)

    y_rod = y3 + 150
    o.append(f'<text x="{CX}" y="{y_rod}" font-size="10.5" fill="#777777">'
              f'Elaboração própria a partir de `corpus_rsl.csv` ({total} registros). "Outros" procedimentos: '
              f'acervo prévio, decisão documentada, contato direto, legado CAPES 1987-2012 e 1 sem procedimento preenchido.</text>')

    o.append("</svg>")
    with open(OUT_FUNIL, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(o))
    print(f"[funil] {total} -> fichado {fichado} (+{excluido} exc, {reclass} reclass, {indisp} indisp) "
          f"-> corpus {n_corpus} (+{fichado_fora} fichado fora dos estratos)")


def main():
    rows = carregar()
    assert len(rows) == 183, len(rows)
    fig_achados_por_ano(rows)
    fig_funil(rows)


if __name__ == "__main__":
    main()
