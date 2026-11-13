"""
Design System de Figuras — Tarifa Zero e Grupos Econômicos
Tese de doutorado · Thiago Von Zeidler Gomes · Orientadora: Prof.ª Silvana Zioni

Toolkit único para refazer as figuras da tese, do painel e dos artigos.
A especificação em prosa está em `_meta/Design System de Figuras.md`;
este arquivo é a sua implementação — se os dois divergirem, a nota manda.

Uso mínimo
----------
    from estilo_figuras import aplicar_estilo, figura, salvar, cor, paleta

    aplicar_estilo()                       # contexto 'tese' (fundo branco)
    fig, ax = figura('plena', razao=1.9)
    ax.bar(x, y, color=cor('rosa'))
    salvar(fig, '_attachments/fig-04-01-adocoes-por-ano.svg')

Regras que o toolkit impõe (e por quê)
--------------------------------------
* No contexto 'tese' a figura **não** carrega título nem fonte embutidos:
  na ABNT a legenda vem acima e a Fonte abaixo, no corpo do documento, e
  `exportar_tese.py` já as formata. Use `snippet_abnt()` para gerar o bloco.
* Máximo de 4 categorias com cor própria. A quinta vira "Outros" cinza —
  ou a figura vira pequenos múltiplos. Não há 5ª cor a inventar.
* `checar(fig)` roda a auditoria de legibilidade antes de salvar e
  `salvar()` a executa por padrão: ela reclama, não conserta.
"""
from __future__ import annotations

import math
import os
import re
import warnings
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

__all__ = [
    "IDENTIDADE", "RAMPAS", "CATEGORICA", "NEUTROS", "SEMANTICA",
    "FAMILIAS", "PALETA_LIVRE", "CAIXA_DETALHE",
    "PILHA_FONTES", "LARGURAS_CM",
    "aplicar_estilo", "figura", "salvar", "cor", "paleta", "rampa",
    "classes", "legenda", "legenda_escala", "rotulos_diretos", "hachura", "nota",
    "estilo_rede", "snippet_abnt", "checar", "contraste",
]

AQUI = Path(__file__).resolve().parent

# ─────────────────────────────────────────────────────────────────────────────
# 1. Cor
# ─────────────────────────────────────────────────────────────────────────────

#: As cinco cores da Identidade Visual da Pesquisa. Não alterar.
IDENTIDADE = {
    "preto": "#0E0E10",
    "rosa": "#FF2D6B",
    "amarelo": "#F5E400",
    "azul": "#1A54C7",
    "verde": "#6FBE44",
    "papel": "#FAF9F5",
}

#: Rampas derivadas das cores da identidade em OKLCH (matiz preservada,
#: luminosidade e croma escalonados). O passo em **negrito** na nota é o hex
#: da identidade; os demais existem para dar contraste e ordem.
RAMPAS = {
    "rosa": {100: "#FFEAEC", 200: "#FFCED3", 300: "#FFA8B3", 400: "#FF778F",
             500: "#FF2D6B", 600: "#DE0056", 700: "#AF0042", 800: "#7D002C"},
    "azul": {100: "#E8F1FF", 200: "#CADDFF", 300: "#A4C5FF", 400: "#79A8FF",
             500: "#4F8BFF", 600: "#3972E2", 700: "#1A54C7", 800: "#0F398D"},
    "verde": {100: "#D4FFC2", 200: "#B4F198", 300: "#98D979", 400: "#6FBE44",
              500: "#5CA730", 600: "#448E0B", 700: "#326F00", 800: "#204E00"},
    "amarelo": {100: "#FFF586", 200: "#F5E400", 300: "#D5C838", 400: "#BAAD00",
                500: "#9F9400", 600: "#857B00", 700: "#676000", 800: "#484300"},
    "grafite": {100: "#EFEFF8", 200: "#DBDBE4", 300: "#C3C3CC", 400: "#A8A8B1",
                500: "#909098", 600: "#787880", 700: "#5D5D64", 800: "#0E0E10"},
}

#: Ordem categórica fixa. Nunca reciclar, nunca reordenar por valor.
#: Validada em par-a-par (protanopia/deuteranopia, Machado 2009, severidade 1.0)
#: sobre branco e sobre papel: pior ΔE CVD 10,8 · pior ΔE visão normal 26,7.
CATEGORICA = ["#FF2D6B", "#1A54C7", "#326F00", "#BAAD00"]

#: Variante de traço do slot 4: #BAAD00 tem 2,3:1 sobre branco e só é legal
#: em preenchimento com rótulo direto. Linha, texto e marcador usam este.
CATEGORICA_TRACO = ["#FF2D6B", "#1A54C7", "#326F00", "#9F9400"]

NEUTROS = {
    "papel": "#FAF9F5",
    "branco": "#FFFFFF",
    "tinta": "#0E0E10",
    "tinta_secundaria": "#2E2E34",
    "tinta_fraca": "#5D5D64",
    "eixo": "#C3C3CC",
    "grade": "#DBDBE4",
    "outros": "#787880",       # 5ª categoria em diante, sempre rotulada
    "sem_dado": "#C3C3CC",     # ausência de medição — sempre com hachura
    "ressalva": "#BAAD00",     # dado não apurado / supressão amostral
}

#: Ligação entre categoria da pesquisa e cor. Esta é a camada que faz a
#: identidade significar alguma coisa: nenhuma cor entra numa figura sem
#: uma função declarada aqui.  ⚠️ A REVISAR com o autor.
SEMANTICA = {
    # a política
    "tarifa_zero": "#FF2D6B",
    "tarifado": "#DBDBE4",
    "reversao": "#FF2D6B",          # mesmo preenchimento + hachura 135°
    # camadas da régua (ordinal: tarifado → universal)
    "camada_4_grupo_social": "#FF778F",
    "camada_3_espacial": "#FF2D6B",
    "camada_2_temporal": "#DE0056",
    "camada_1_universal": "#7D002C",
    # o capital
    "grupo_economico": "#1A54C7",
    "empresa": "#79A8FF",
    "socio": "#909098",
    # estado da política (família de ESTADO, não de série)
    "ativa": "#326F00",          # ativa · decreto confirmado · dado verificado
    "candidata": "#BAAD00",      # anunciada, ainda não confirmada
    "encerrada": "#FFA8B3",      # + hachura 135°: a camada que a política tinha
    # avisos
    "nao_apurado": "#C3C3CC",
    "suprimido": "#C3C3CC",
}

# ─────────────────────────────────────────────────────────────────────────────
# 1b. Sistema de três níveis (r79, 21/10/2026 — aprovado pelo autor)
# ─────────────────────────────────────────────────────────────────────────────
# Nível 1 · ÂNCORAS: valem em toda a tese e não mudam de sentido.
#   rosa  = Tarifa Zero / transporte público coletivo (o objeto)
#   azul  = grupos econômicos, empresas, operador privado
#   cinza + hachura = sem dado / não apurado (NA ≠ 0)
# Nível 2 · FAMÍLIAS POR TEMA: cada tema tem uma chave de cores fixa
#   (FAMILIAS abaixo), impressa na legenda. Dentro do tema a cor é estável
#   de figura a figura; entre temas, a mesma matiz pode voltar com outra
#   função, porque a legenda diz qual.
# Nível 3 · PALETA LIVRE: figura que não pertence a um tema usa até 8 cores
#   (PALETA_LIVRE), sempre com rótulo direto.
# Regras transversais: a cor nunca trabalha sozinha (forma, rótulo ou
# posição repetem a informação); estado se marca pela forma (cheio = ativa,
# vazado = encerrada, tracejado = previsto/por hipótese); amarelo puro só em
# área grande com contorno, âmbar nas marcas; uma mensagem → cinza + 1 ou 2
# destaques. O petróleo #0F6B6E é das caixas de destaque e nunca entra em
# figura.

RAMPAS["ambar"] = {100: "#FFF3D6", 200: "#FFE2A8", 300: "#FFC95C", 400: "#F5B120",
                   500: "#E39B00", 600: "#B87C00", 700: "#8A5C00", 800: "#5C3D00"}

RAMPAS["verde"][25] = "#F1F8EC"   # fundos claros da régua analítica (só área, nunca série)
RAMPAS["verde"][50] = "#E3F3D9"

CAIXA_DETALHE = "#0F6B6E"   # reservado às caixas (Análise, Estudo de caso, Teste)

FAMILIAS = {
    # régua descritiva: matiz = camada, tom (e forma) = subtipo
    "camada_1": {"1a": RAMPAS["rosa"][500], "1b": RAMPAS["rosa"][800],
                 "1c": RAMPAS["rosa"][300], "1d": RAMPAS["rosa"][600],
                 "_marcador": {"1a": "o", "1b": "s", "1c": "p", "1d": "^"},
                 # r81 (pedido do autor): o losango parecia maior que os outros símbolos; 1c passa ao pentágono (a casa da
                 # residência) e as formas têm a mesma área do círculo (fator sobre s do scatter)
                 "_escala": {"o": 1.0, "s": 0.785, "p": 1.32, "^": 1.57},
                 "_cor": RAMPAS["rosa"][500]},
    "camada_2": {"2a": RAMPAS["ambar"][700], "2b": RAMPAS["ambar"][500],
                 "2c": RAMPAS["ambar"][300], "2d": RAMPAS["ambar"][800],
                 "2e": RAMPAS["ambar"][600], "_cor": RAMPAS["ambar"][500]},
    "encerrada": {"_cor": RAMPAS["grafite"][800], "_marcador": "X"},
    "hipotese": {"_cor": RAMPAS["grafite"][800], "_marcador": "anel"},
    # modos de transporte
    "modos": {"auto": RAMPAS["grafite"][800], "moto": RAMPAS["ambar"][500],
              "tpc": RAMPAS["rosa"][500], "ativo": RAMPAS["verde"][700],
              "outros": RAMPAS["grafite"][300]},
    # arranjo da prestação (A1–A6): público → privado
    # r81 (regra do autor): nunca verde + amarelo + azul sozinhos ("brasileirinho"); o meio da escala é cinza
    "arranjo": {"A1": RAMPAS["verde"][700], "A2": RAMPAS["verde"][300],
                "A3": RAMPAS["grafite"][400], "A4": RAMPAS["azul"][400],
                "A5": RAMPAS["azul"][700], "A6": RAMPAS["grafite"][200]},
    # esfera do arranjo (D1–D5)
    "esfera": {"prefeitura": RAMPAS["verde"][700], "empresa": RAMPAS["azul"][700],
               "varia": RAMPAS["grafite"][400]},
    # régua analítica (proximidade ao comum): verde → cinza → azul (o subsídio que serve ao operador)
    "regua_analitica": {"comum": RAMPAS["verde"][700], "parcial": RAMPAS["verde"][300],
                        "sem": RAMPAS["grafite"][200], "bolsa": RAMPAS["azul"][700],
                        "_fundo": [RAMPAS["verde"][50], RAMPAS["verde"][25], RAMPAS["grafite"][100], RAMPAS["azul"][100]]},
    # efeito com sinal (mapas de coeficiente local)
    "divergente": {"negativo": RAMPAS["azul"][700], "positivo": RAMPAS["ambar"][600],
                   "nulo": RAMPAS["grafite"][200]},
}

#: Paleta livre (nível 3): até 8 cores, só com rótulo direto.
PALETA_LIVRE = [RAMPAS["rosa"][500], RAMPAS["azul"][700], RAMPAS["verde"][700],
                RAMPAS["ambar"][500], RAMPAS["grafite"][800], RAMPAS["azul"][400],
                RAMPAS["rosa"][300], RAMPAS["verde"][300]]

SEMANTICA.update({
    "coletivo": RAMPAS["rosa"][500],
    "automovel": FAMILIAS["modos"]["auto"],
    "motocicleta": FAMILIAS["modos"]["moto"],
    "camada_1": FAMILIAS["camada_1"]["_cor"],
    "camada_2": FAMILIAS["camada_2"]["_cor"],
    "publico": FAMILIAS["esfera"]["prefeitura"],
})
# ⚠ Superados (numeração de "4 camadas" até 13/09/2026): mantidos só para que
# scripts antigos rodem; não usar em figura nova.
_SUPERADOS = ("camada_4_grupo_social", "camada_3_espacial", "camada_2_temporal",
              "camada_1_universal", "ativa", "candidata")

#: Regra de colisão: verde e amarelo têm DUAS funções possíveis. Quando a figura
#: codifica estado (ativa/candidata/encerrada), eles vestem os tokens de estado
#: acima e NÃO entram como série; quando a figura só distingue categorias, eles
#: são os slots 3 e 4. Nunca os dois papéis na mesma figura.

PILHA_FONTES = "Poppins, 'Segoe UI', Calibri, sans-serif"

#: Largura útil da mancha na ABNT/UFABC (A4, margens 3-2-3-2 cm) = 16 cm.
LARGURAS_CM = {"plena": 16.0, "dois_tercos": 10.6, "meia": 7.7, "coluna": 7.7}


def cor(nome: str, passo: int | None = None) -> str:
    """Devolve um hex do sistema.

    cor('rosa')            → passo 500 (o hex da identidade)
    cor('azul', 300)       → passo da rampa
    cor('grupo_economico') → token semântico
    cor('grade')           → neutro
    """
    if nome in SEMANTICA and passo is None:
        return SEMANTICA[nome]
    if nome in NEUTROS and passo is None:
        return NEUTROS[nome]
    if nome in RAMPAS:
        padrao = {"rosa": 500, "azul": 700, "verde": 700, "amarelo": 400, "grafite": 700, "ambar": 500}
        return RAMPAS[nome][passo or padrao[nome]]
    if nome in IDENTIDADE:
        return IDENTIDADE[nome]
    raise KeyError(f"cor desconhecida: {nome!r}")


def paleta(n: int, traco: bool = False) -> list[str]:
    """Os n primeiros slots categóricos, na ordem fixa.

    n > 4 não é erro de cor, é erro de figura: dobre o excedente em
    'Outros' ou vá para pequenos múltiplos. O 5º slot vem cinza de
    propósito, para que a figura denuncie o problema.
    """
    base = CATEGORICA_TRACO if traco else CATEGORICA
    if n <= len(base):
        return base[:n]
    warnings.warn(
        f"{n} categorias pedidas; o sistema tem 4. Os slots 5+ saem em cinza "
        "'Outros'. Agrupe o excedente ou use pequenos múltiplos.",
        stacklevel=2,
    )
    return base + [NEUTROS["outros"]] * (n - len(base))


def rampa(familia: str, n: int, tipo: str = "ordinal") -> list[str]:
    """Rampa de uma matiz só, clara → escura.

    tipo='ordinal'    → n passos entre 400 e 800 (classes discretas; o passo
                        mais claro ainda se separa do fundo, ≥ 2:1).
    tipo='sequencial' → n passos entre 200 e 800 (magnitude contínua; o passo
                        mais claro pode recuar para o fundo = "perto de zero").
    """
    if familia not in RAMPAS:
        raise KeyError(f"rampa desconhecida: {familia!r}")
    ini, fim = (400, 800) if tipo == "ordinal" else (200, 800)
    passos = sorted(RAMPAS[familia])
    disp = [p for p in passos if ini <= p <= fim]
    if n > len(disp):
        raise ValueError(f"rampa {familia}/{tipo} comporta no máximo {len(disp)} classes")
    if n == 1:
        idx = [len(disp) - 1]
    else:
        idx = [round(i * (len(disp) - 1) / (n - 1)) for i in range(n)]
    return [RAMPAS[familia][disp[i]] for i in idx]


def classes(valores, k: int = 5, familia: str = "rosa", metodo: str = "quantil"):
    """Classifica valores e devolve (cortes, cores, rotulos).

    metodo: 'quantil' (padrão, robusto a cauda longa — o caso dos municípios)
            ou 'igual' (intervalos iguais, só quando a distribuição é simétrica).
    Valores None/NaN não entram na classificação: vão para 'sem_dado'.
    """
    vals = sorted(v for v in valores if v is not None and not (isinstance(v, float) and math.isnan(v)))
    if not vals:
        raise ValueError("nenhum valor válido para classificar")
    if metodo == "quantil":
        cortes = [vals[0]] + [vals[min(len(vals) - 1, round(i * len(vals) / k))] for i in range(1, k)] + [vals[-1]]
    elif metodo == "igual":
        lo, hi = vals[0], vals[-1]
        cortes = [lo + i * (hi - lo) / k for i in range(k + 1)]
    else:
        raise ValueError("metodo deve ser 'quantil' ou 'igual'")
    cores = rampa(familia, k, tipo="sequencial")
    rotulos = [f"{cortes[i]:,.0f} – {cortes[i+1]:,.0f}".replace(",", ".") for i in range(k)]
    return cortes, cores, rotulos


def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def contraste(a: str, b: str = "#FFFFFF") -> float:
    """Razão de contraste WCAG entre dois hex. Marca ≥ 3:1, texto ≥ 4,5:1."""
    def lum(h):
        h = h.lstrip("#")
        r, g, bb = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(bb)
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Estilo e figura
# ─────────────────────────────────────────────────────────────────────────────

_CONTEXTO = "tese"


def aplicar_estilo(contexto: str = "tese") -> None:
    """Carrega tz.mplstyle e ajusta ao destino.

    'tese'  — fundo branco, sem título na figura (a legenda ABNT fica no texto).
    'web'   — fundo papel #FAF9F5, título dentro da figura (o painel não tem legenda).
    'slide' — fundo branco, tipografia 2 pt maior.
    """
    global _CONTEXTO
    _CONTEXTO = contexto
    plt.style.use(str(AQUI / "tz.mplstyle"))
    if contexto == "web":
        mpl.rcParams.update({"figure.facecolor": NEUTROS["papel"],
                            "axes.facecolor": NEUTROS["papel"],
                            "savefig.facecolor": NEUTROS["papel"]})
    elif contexto == "slide":
        for k in ("font.size", "axes.labelsize", "axes.titlesize"):
            mpl.rcParams[k] = mpl.rcParams[k] + 2
        for k in ("xtick.labelsize", "ytick.labelsize", "legend.fontsize"):
            mpl.rcParams[k] = mpl.rcParams[k] + 2
    if "Poppins" not in {f.name for f in mpl.font_manager.fontManager.ttflist}:
        warnings.warn("Poppins não encontrada — o SVG sairá com a pilha de fontes "
                      "correta, mas a prévia local usará a fonte substituta.", stacklevel=2)


def figura(largura="plena", razao: float = 1.618, altura_cm: float | None = None, **kw):
    """Cria fig, ax no tamanho final impresso (em cm, não em polegadas).

    largura: 'plena' (16 cm), 'dois_tercos' (10,6), 'meia' (7,7) ou cm.
    razao:   largura/altura. 1.618 para gráficos gerais; 1.0–1.2 para mapas;
             2.2–2.6 para séries longas; 0.8 para barras horizontais longas.
    """
    l_cm = LARGURAS_CM.get(largura, largura) if isinstance(largura, str) else float(largura)
    a_cm = altura_cm if altura_cm else l_cm / razao
    fig, ax = plt.subplots(figsize=(l_cm / 2.54, a_cm / 2.54), **kw)
    fig.set_layout_engine("constrained")
    return fig, ax


def legenda(ax, itens=None, ncol: int | None = None, **kw):
    """Legenda do sistema: acima da área de plotagem, sem moldura, alinhada à
    esquerda.

    `itens` é uma lista de tuplas:
        (rotulo, cor)                     → chapa
        (rotulo, cor, hachura)            → chapa hachurada
        (rotulo, cor, None, 'linha')      → traço (aresta, série de linha)
        (rotulo, cor, None, 'contorno')   → círculo vazado (nó aberto)
    """
    handles = None
    if itens:
        handles = []
        for i in itens:
            rot, c = i[0], i[1]
            hat = i[2] if len(i) > 2 else None
            forma = i[3] if len(i) > 3 else "chapa"
            if forma == "linha":
                handles.append(Line2D([], [], color=c, linewidth=1.8, label=rot))
            elif forma == "contorno":
                handles.append(Line2D([], [], color="none", marker="o", markersize=7,
                                      markerfacecolor="white", markeredgecolor=c,
                                      markeredgewidth=1.1, label=rot))
            else:
                borda = NEUTROS["tinta_fraca"] if (hat or contraste(c, "#FFFFFF") < 1.3) else "none"
                handles.append(Patch(facecolor=c, hatch=hat, edgecolor=borda,
                                     linewidth=0.6, label=rot))
    n = ncol or min(4, len(handles) if handles else len(ax.get_legend_handles_labels()[0]))
    leg = ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0, 1.01),
                    ncol=n, frameon=False, handlelength=1.1, **kw)
    for t in leg.get_texts():
        t.set_color(NEUTROS["tinta_secundaria"])
    return leg


def legenda_escala(ax, cores, rotulos, titulo: str | None = None,
                   sem_dado: bool = False, largura: float = 0.62, altura: float = 0.05):
    """Legenda de escala ordinal/sequencial: faixa CONTÍGUA acima do gráfico,
    não chapas soltas. A escala é ordenada; a legenda tem de mostrar a ordem.

    `rotulos` traz k rótulos (um por classe) ou k+1 cortes.
    """
    cax = ax.inset_axes([0.0, 1.03, largura, altura], transform=ax.transAxes)
    k = len(cores)
    for i, c in enumerate(cores):
        cax.add_patch(plt.Rectangle((i / k, 0), 1 / k, 1, facecolor=c, edgecolor="none"))
    cax.set_xlim(0, 1); cax.set_ylim(0, 1)
    cax.set_yticks([])
    for s in cax.spines.values():
        s.set_visible(False)
    if len(rotulos) == k + 1:
        cax.set_xticks([i / k for i in range(k + 1)])
    else:
        cax.set_xticks([(i + 0.5) / k for i in range(k)])
    cax.set_xticklabels(rotulos, fontsize=7.5, color=NEUTROS["tinta_secundaria"])
    if len(rotulos) == k + 1:   # rótulos nos cortes: puxar as pontas para dentro
        etiquetas = cax.get_xticklabels()
        etiquetas[0].set_ha("left")
        etiquetas[-1].set_ha("right")
    cax.tick_params(length=0, pad=2)
    cax.xaxis.set_ticks_position("bottom")
    if titulo:
        cax.set_title(titulo, fontsize=8, loc="left", pad=4,
                      color=NEUTROS["tinta_secundaria"], fontweight="normal")
    if sem_dado:
        sax = ax.inset_axes([largura + 0.12, 1.03, 0.055, altura], transform=ax.transAxes)
        sax.add_patch(plt.Rectangle((0, 0), 1, 1, facecolor=NEUTROS["sem_dado"],
                                    hatch=hachura("sem_dado"),
                                    edgecolor=NEUTROS["tinta_fraca"], linewidth=0.6))
        sax.set_xlim(0, 1); sax.set_ylim(0, 1); sax.set_yticks([])
        sax.set_xticks([0.5]); sax.set_xticklabels(["sem dado"], fontsize=7.5,
                                                   color=NEUTROS["tinta_secundaria"])
        sax.tick_params(length=0, pad=2)
        for s in sax.spines.values():
            s.set_visible(False)
    return cax


def rotulos_diretos(ax, xs, ys, textos, dy: float = 0.0, cor_texto: str | None = None, **kw):
    """Rótulos no fim da marca. Regra: rotular o que carrega o argumento —
    extremos, viradas, o caso citado no texto — nunca todos os pontos."""
    for x, y, t in zip(xs, ys, textos):
        ax.annotate(t, (x, y), textcoords="offset points", xytext=(0, 4 + dy),
                    ha="center", va="bottom", fontsize=8,
                    color=cor_texto or NEUTROS["tinta_secundaria"], **kw)


def hachura(tipo: str = "sem_dado") -> str:
    """Hachuras reservadas. Só três, cada uma com significado fixo:
    'sem_dado'  '///'  ausência de medição (≠ zero)
    'reversao'  '\\\\\\'  política revogada/encerrada
    'estimado'  '...'  valor estimado ou suprimido por sigilo amostral
    """
    return {"sem_dado": "///", "reversao": "\\\\\\", "estimado": "..."}[tipo]


def nota(fig, texto: str) -> None:
    """Nota curta dentro da figura (supressão amostral, recorte, n).
    NÃO é a Fonte ABNT: essa vai no texto, via snippet_abnt()."""
    fig.text(0.0, -0.01, texto, ha="left", va="top", fontsize=7.5,
             color=NEUTROS["tinta_fraca"], wrap=True)


def estilo_rede() -> dict:
    """Especificação dos grafos da ARS (networkx/graphviz).

    O grafo tem três tipos de nó e eles não são categorias comparáveis:
    grupo, empresa e sócio se distinguem por **forma e tamanho** antes de cor.
    """
    return {
        "no": {
            "grupo":   dict(node_color=SEMANTICA["grupo_economico"], node_shape="s",
                            node_size=560, edgecolors="white", linewidths=1.2),
            "empresa": dict(node_color=SEMANTICA["empresa"], node_shape="o",
                            node_size=120, edgecolors="white", linewidths=0.8),
            "socio":   dict(node_color="white", node_shape="o", node_size=60,
                            edgecolors=SEMANTICA["socio"], linewidths=0.9),
        },
        "aresta": dict(edge_color="#C3C3CC", width=0.7, alpha=0.9),
        "aresta_destaque": dict(edge_color=SEMANTICA["grupo_economico"], width=1.6),
        "rotulo": dict(font_family="Poppins", font_size=7.5,
                       font_color=NEUTROS["tinta_secundaria"]),
        "regra": ("Rotular só os nós citados no texto. Peso da aresta pela raiz "
                  "do valor, nunca linear. Layout com semente fixa e registrada "
                  "na legenda, para a figura ser reproduzível."),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Auditoria e gravação
# ─────────────────────────────────────────────────────────────────────────────

def checar(fig, verboso: bool = True) -> list[str]:
    """Roda as travas do sistema sobre a figura pronta. Reclama, não conserta."""
    avisos = []
    fundo = mpl.colors.to_hex(fig.get_facecolor())
    for ax in fig.axes:
        artistas = list(ax.patches) + list(ax.lines) + list(ax.collections)
        cores_usadas = set()
        for a in artistas:
            try:
                c = a.get_facecolor()
                c = c[0] if hasattr(c, "__len__") and len(c) and hasattr(c[0], "__len__") else c
                if c is not None and (not hasattr(c, "__len__") or len(c) < 4 or c[3] > 0):
                    cores_usadas.add(mpl.colors.to_hex(c))
            except Exception:
                pass
        conhecidas = {c.upper() for f in RAMPAS.values() for c in f.values()} | \
                     {c.upper() for c in NEUTROS.values()} | {"#FFFFFF", "#000000"}
        fora = {c for c in cores_usadas if c.upper() not in conhecidas}
        if fora:
            avisos.append(f"cores fora do sistema: {sorted(fora)}")
        if CAIXA_DETALHE.upper() in {c.upper() for c in cores_usadas}:
            avisos.append("petróleo #0F6B6E é das caixas de destaque — não usar em figura")
        vivas = {c for c in cores_usadas if c.upper() in {x.upper() for x in CATEGORICA}}
        if len(vivas) > 4:
            avisos.append("mais de 4 categorias com cor própria — agrupe em 'Outros'")
        # Contraste: só as cores de SÉRIE precisam de 3:1. Os passos claros de
        # uma rampa sequencial podem recuar para o fundo — é o que significam.
        # Abaixo de 3:1 a regra de alívio exige rótulo visível ou tabela.
        cat = {c.upper() for c in CATEGORICA}
        if not ax.texts:
            for c in cores_usadas:
                if c.upper() in cat and contraste(c, fundo) < 3:
                    avisos.append(
                        f"{c} tem {contraste(c, fundo):.2f}:1 sobre o fundo e a figura "
                        "não traz rótulo direto — acrescente rótulo ou tabela de apoio")
        n_series = len(ax.get_legend_handles_labels()[0])
        if n_series >= 2 and ax.get_legend() is None:
            avisos.append("2+ séries sem legenda — identidade ficando só na cor")
        if _CONTEXTO == "tese" and ax.get_title():
            avisos.append("título dentro da figura no contexto 'tese' — a legenda "
                          "ABNT vai no texto (ver snippet_abnt)")
    # regra do autor (r81): verde + amarelo/âmbar + azul, sem outra cor viva, lê como bandeira — proibido
    usadas = set()
    for ax in fig.axes:
        for a in list(ax.patches) + list(ax.lines) + list(ax.collections):
            for getter in ("get_facecolor", "get_color", "get_edgecolor"):
                try:
                    c = getattr(a, getter)()
                    cs = c if (hasattr(c, "__len__") and len(c) and hasattr(c[0], "__len__")) else [c]
                    for x in cs:
                        if x is not None and (isinstance(x, str) or len(x) < 4 or x[3] > 0): usadas.add(mpl.colors.to_hex(x).upper())
                except Exception:
                    pass
    fam = {nome for nome, r in RAMPAS.items() if nome != "grafite" for c in r.values() if c.upper() in usadas}
    if {"verde", "azul"} <= fam and fam & {"ambar", "amarelo"} and not fam - {"verde", "azul", "ambar", "amarelo"}:
        avisos.append("verde + amarelo + azul sozinhos (regra do autor: nada de bandeira) — troque o meio por cinza ou acrescente o rosa")
    if verboso:
        for a in dict.fromkeys(avisos):
            print(f"  ⚠ {a}")
        if not avisos:
            print("  ✓ figura conforme o design system")
    return avisos


def salvar(fig, caminho, png: bool = False, auditar: bool = True, fechar: bool = True):
    """Grava SVG (e opcionalmente PNG 300 dpi), com a pilha de fontes correta.

    O SVG sai com texto vivo (svg.fonttype='none'): pesa pouco, é pesquisável
    e reflui no Obsidian. Para depósito em repositório onde a Poppins pode não
    existir, gere também o PNG.
    """
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if auditar:
        print(f"{caminho.name}:")
        checar(fig)
    # tela exata (diagramas.tela): a figura já tem o tamanho e a margem finais;
    # o recorte 'tight' do estilo a encostaria na borda.
    rc = {"savefig.bbox": "standard"} if getattr(fig, "_tela_exata", False) else {}
    with mpl.rc_context(rc):
        fig.savefig(caminho, format="svg")
        if png:
            fig.savefig(caminho.with_suffix(".png"), dpi=300)
    svg = caminho.read_text(encoding="utf-8")
    svg = re.sub(r"font-family:\s*[^;\"']+", f"font-family: {PILHA_FONTES}", svg)
    svg = re.sub(r"<metadata>.*?</metadata>\s*", "", svg, flags=re.S)  # tira o blob C2PA
    svg = svg.replace("<svg ", '<svg style="background:%s" ' % mpl.colors.to_hex(fig.get_facecolor()), 1)
    caminho.write_text(svg, encoding="utf-8")
    if fechar:
        plt.close(fig)
    return caminho


def snippet_abnt(arquivo: str, numero: str, titulo: str, fonte: str,
                 nota_rodape: str | None = None) -> str:
    """Devolve o bloco markdown para colar no capítulo: designativo + número +
    travessão + título ACIMA, figura, Fonte ABAIXO. É esse bloco que
    `exportar_tese.py` reconhece e formata."""
    nome = Path(arquivo).name
    bloco = f"**Figura {numero} — {titulo}**\n\n![[{nome}]]\n\nFonte: {fonte}"
    if nota_rodape:
        bloco += f"\n\nNota: {nota_rodape}"
    return bloco + "\n"
