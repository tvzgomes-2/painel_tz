"""Diagramas conceituais — tela exata, texto medido e setas por caminho.

Complementa estilo_figuras.py para figuras que NÃO são gráficos (ciclos,
fluxos, bifurcações). Três defeitos que o caminho padrão do matplotlib produz
e que este módulo elimina:

1. Cortes. Patches são recortados pelos limites do eixo e o `bbox: tight`
   encosta o conteúdo na borda. Aqui a tela é em centímetros (1 unidade = 1 cm
   impresso), nada é recortado e `ajustar()` redimensiona a figura ao conteúdo
   com a mesma margem nos quatro lados.
2. Texto descentrado. `va='center'` centra pela caixa de métricas da fonte e o
   espaçamento entre linhas varia com parênteses e descendentes. Aqui cada linha
   é posta na sua linha de base, com passo fixo, e o bloco é centrado
   opticamente (topo da versal da 1ª linha ↔ linha de base da última).
3. Setas imprecisas. `arc3`/`angle` decidem a curva sozinhos. Aqui a seta segue
   uma poligonal com cantos arredondados de raio dado — o traçado é o desenhado.

Uso mínimo:
    fig, ax = tela()
    bloco_texto(ax, 8, 5, "texto com **negrito** e //secundário//", 9, largura_cm=5)
    seta(ax, [(1, 1), (4, 1), (4, 3)], raio=0.6)
    ajustar(fig, ax, margem=0.3)
    salvar(fig, "fig.svg")
"""
from __future__ import annotations

import re
import math
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path
from matplotlib.patches import FancyArrowPatch, Circle, Rectangle

from estilo_figuras import NEUTROS, cor

CM = 1 / 2.54
LARGURA_TEXTO_CM = 16.0


# ── tela ───────────────────────────────────────────────────────────────────
def tela(largura_cm: float = LARGURA_TEXTO_CM, altura_cm: float = 10.0):
    """Figura cujo eixo ocupa 100% da área, em coordenadas de centímetro."""
    fig = plt.figure(figsize=(largura_cm * CM, altura_cm * CM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, largura_cm)
    ax.set_ylim(-altura_cm, 0)
    ax.axis('off')
    fig._tela_exata = True          # salvar() grava sem recorte 'tight'
    fig._largura_cm = largura_cm
    return fig, ax


def _extensoes_cm(fig, ax):
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    inv = ax.transData.inverted()
    caixas = []
    for a in list(ax.patches) + list(ax.texts) + list(ax.lines):
        if not a.get_visible() or getattr(a, '_fora_da_medida', False):
            continue
        bb = a.get_window_extent(r)
        if bb.width == 0 and bb.height == 0:
            continue
        (x0, y0), (x1, y1) = inv.transform([(bb.x0, bb.y0), (bb.x1, bb.y1)])
        caixas.append((x0, y0, x1, y1))
    return (min(c[0] for c in caixas), min(c[1] for c in caixas),
            max(c[2] for c in caixas), max(c[3] for c in caixas))


def ajustar(fig, ax, margem: float = 0.3, centrar_x: bool = True):
    """Recorta a tela ao conteúdo: margem igual em cima e embaixo; na
    horizontal mantém a largura da mancha (16 cm) e centra o conteúdo."""
    for a in list(ax.patches) + list(ax.texts) + list(ax.lines):
        a.set_clip_on(False)
    x0, y0, x1, y1 = _extensoes_cm(fig, ax)
    L = fig._largura_cm
    if x1 - x0 + 2 * margem > L:
        L = x1 - x0 + 2 * margem
    cx = (x0 + x1) / 2 if centrar_x else L / 2
    H = y1 - y0 + 2 * margem
    ax.set_xlim(cx - L / 2, cx + L / 2)
    ax.set_ylim(y0 - margem, y1 + margem)
    fig.set_size_inches(L * CM, H * CM)
    return L, H


def margens_png(caminho_png: str, limiar: int = 250):
    """Margens (px) de tinta de um PNG: esq, dir, topo, base. Para conferir."""
    from PIL import Image
    import numpy as np
    im = np.asarray(Image.open(caminho_png).convert('L'))
    ys, xs = np.where(im < limiar)
    h, w = im.shape
    return xs.min(), w - 1 - xs.max(), ys.min(), h - 1 - ys.max()


# ── texto ──────────────────────────────────────────────────────────────────
def _prop(tamanho, peso='regular'):
    return FontProperties(family='Poppins', size=tamanho, weight=peso)


def _medir(fig, s, prop):
    """Largura, altura e descendente em cm da string renderizada."""
    r = fig.canvas.get_renderer()
    w, h, d = r.get_text_width_height_descent(s, prop, ismath=False)
    f = 2.54 / fig.dpi
    return w * f, h * f, d * f


def _tokens(texto):
    """'a **b c** //d//' → [(palavra, estilo)], '\\n' vira ('\\n', None)."""
    saida, anterior = [], ''
    for parte in re.split(r'(\*\*.+?\*\*|//.+?//|\n)', texto):
        if not parte:
            continue
        if parte == '\n':
            saida.append(('\n', None)); anterior = '\n'
            continue
        estilo = 'normal'
        if parte.startswith('**'):
            estilo, parte = 'negrito', parte[2:-2]
        elif parte.startswith('//'):
            estilo, parte = 'secundario', parte[2:-2]
        # pontuação colada à corrida anterior ("**heterodoxas**, onde") não
        # ganha espaço antes: o 1º token vem marcado com '\x00'
        cola = (bool(anterior) and not anterior[-1].isspace()
                and not parte[0].isspace())
        for i, p in enumerate(parte.split()):
            saida.append(('\x00' + p if (i == 0 and cola) else p, estilo))
        anterior = parte
    return saida


def bloco_texto(ax, x, y, texto, tamanho=9, largura_cm=None, alinhar='center',
                ancora='centro', entrelinha=1.5, cor_texto=None, peso='regular',
                cor_negrito=None, cor_secundaria=None, escala_secundaria=0.9,
                zorder=5):
    """Bloco de texto com linhas em passo fixo e centragem óptica.

    ancora: 'centro' — (x, y) é o centro óptico do bloco;
            'topo'   — y é o topo das versais da 1ª linha.
    Marcação: **negrito** (peso medium, `cor_negrito`), //secundário//
    (`cor_secundaria`, corpo × `escala_secundaria`, para apostos e parênteses).
    '\\n' força quebra.
    Devolve dict com topo, base (linha de base da última linha), base_tinta
    (com descendente), largura máxima e as linhas [(texto, y_base, x0, x1)].
    """
    fig = ax.figure
    cor_texto = cor_texto or NEUTROS['tinta']
    cor_negrito = cor_negrito or cor_texto
    cor_secundaria = cor_secundaria or NEUTROS['tinta_fraca']
    estilos = {
        'normal': (_prop(tamanho, peso), cor_texto),
        'negrito': (_prop(tamanho, 'medium'), cor_negrito),
        'secundario': (_prop(tamanho * escala_secundaria, peso), cor_secundaria),
    }
    espaco = _medir(fig, 'a a', estilos['normal'][0])[0] - _medir(fig, 'aa', estilos['normal'][0])[0]

    # quebra gulosa por largura medida
    linhas, atual, w_atual = [], [], 0.0
    for palavra, est in _tokens(texto):
        if palavra == '\n':
            linhas.append(atual); atual, w_atual = [], 0.0
            continue
        cola = palavra.startswith('\x00')
        palavra = palavra.lstrip('\x00')
        w = _medir(fig, palavra, estilos[est][0])[0]
        novo = w if not atual else w_atual + (0 if cola else espaco) + w
        if largura_cm and atual and novo > largura_cm and not cola:
            linhas.append(atual); atual, w_atual = [(palavra, est, w, False)], w
        else:
            atual.append((palavra, est, w, cola and bool(atual))); w_atual = novo
    if atual:
        linhas.append(atual)

    passo = tamanho * entrelinha * 2.54 / 72
    versal = _medir(fig, 'H', estilos['normal'][0])[1]
    n = len(linhas)
    if ancora == 'centro':
        b0 = y + ((n - 1) * passo - versal) / 2
    else:
        b0 = y - versal

    info = {'linhas': [], 'topo': b0 + versal, 'base': b0 - (n - 1) * passo,
            'largura': 0.0, 'artistas': []}
    for i, linha in enumerate(linhas):
        # agrupa palavras consecutivas do mesmo estilo em corridas
        corridas = []          # [palavras, estilo, colada_à_anterior]
        for palavra, est, w, cola in linha:
            if corridas and corridas[-1][1] == est and not cola:
                corridas[-1][0].append(palavra)
            else:
                corridas.append(([palavra], est, cola))
        partes = [(' '.join(p), est, cola) for p, est, cola in corridas]
        larguras = [_medir(fig, s, estilos[est][0])[0] for s, est, _ in partes]
        total = sum(larguras) + espaco * sum(1 for _, _, c in partes[1:] if not c)
        x0 = {'center': x - total / 2, 'left': x, 'right': x - total}[alinhar]
        yb = b0 - i * passo
        xc = x0
        for j, ((s, est, cola), w) in enumerate(zip(partes, larguras)):
            if j and not cola:
                xc += espaco
            prop, c = estilos[est]
            t = ax.text(xc, yb, s, fontproperties=prop, color=c, ha='left',
                        va='baseline', zorder=zorder, clip_on=False)
            info['artistas'].append(t)
            xc += w
        info['linhas'].append((' '.join(s for s, _, _ in partes), yb, x0, x0 + total))
        info['largura'] = max(info['largura'], total)
    desc = _medir(fig, 'gjpq', estilos['normal'][0])[2]
    info['base_tinta'] = info['base'] - desc
    info['versal'] = versal
    return info


def folga_no_circulo(info, cx, cy, r):
    """Menor distância (cm) entre o texto e a borda do círculo — conferência."""
    folga = r
    for _, yb, x0, x1 in info['linhas']:
        for yy in (yb + info['versal'], yb):
            dy = abs(yy - cy)
            if dy >= r:
                return -1
            meia_corda = math.sqrt(r * r - dy * dy)
            folga = min(folga, meia_corda - max(cx - x0, x1 - cx))
    return folga


# ── setas ──────────────────────────────────────────────────────────────────
def caminho_arredondado(pontos, raio):
    """Poligonal com cantos arredondados (quadrática) de raio `raio`."""
    verts, codes = [pontos[0]], [Path.MOVETO]
    for a, v, b in zip(pontos, pontos[1:], pontos[2:]):
        da = math.hypot(a[0] - v[0], a[1] - v[1])
        db = math.hypot(b[0] - v[0], b[1] - v[1])
        rr = min(raio, da / 2, db / 2)
        p = (v[0] + (a[0] - v[0]) / da * rr, v[1] + (a[1] - v[1]) / da * rr)
        q = (v[0] + (b[0] - v[0]) / db * rr, v[1] + (b[1] - v[1]) / db * rr)
        verts += [p, v, q]
        codes += [Path.LINETO, Path.CURVE3, Path.CURVE3]
    verts.append(pontos[-1]); codes.append(Path.LINETO)
    return Path(verts, codes)


def seta(ax, pontos, raio=0.5, cor_traco=None, espessura=1.8, cabeca=(0.55, 0.45),
         zorder=1):
    """Seta que segue `pontos` (cm). A ponta fica no último ponto e aponta na
    direção do último segmento. cabeca = (comprimento, largura) em mm×10⁻¹…
    na prática: múltiplos da espessura via mutation_scale."""
    cor_traco = cor_traco or cor('grafite', 500)
    comp, larg = cabeca
    p = FancyArrowPatch(
        path=caminho_arredondado(pontos, raio),
        arrowstyle=f"-|>,head_length={comp},head_width={larg}",
        mutation_scale=espessura * 6, linewidth=espessura, color=cor_traco,
        joinstyle='round', capstyle='round', zorder=zorder, clip_on=False)
    ax.add_patch(p)
    return p


def linha(ax, pontos, raio=0.5, cor_traco=None, espessura=1.8, zorder=1):
    """Mesmo traçado da seta, sem ponta (tronco de bifurcação)."""
    from matplotlib.patches import PathPatch
    cor_traco = cor_traco or cor('grafite', 500)
    p = PathPatch(caminho_arredondado(pontos, raio), facecolor='none',
                  edgecolor=cor_traco, linewidth=espessura, capstyle='round',
                  joinstyle='round', zorder=zorder, clip_on=False)
    ax.add_patch(p)
    return p


# ── peças ──────────────────────────────────────────────────────────────────
def no(ax, cx, cy, r, texto, tamanho=9, fundo=None, cor_texto=None,
       largura_cm=None, **kw):
    """Nó circular com texto opticamente centrado. Devolve (info, folga_cm)."""
    fundo = fundo or cor('grafite', 200)
    ax.add_patch(Circle((cx, cy), r, facecolor=fundo, edgecolor='none',
                        zorder=2, clip_on=False))
    info = bloco_texto(ax, cx, cy, texto, tamanho, largura_cm=largura_cm,
                       cor_texto=cor_texto, **kw)
    return info, folga_no_circulo(info, cx, cy, r)


def chapa(ax, cx, cy_topo, largura, altura, titulo, fundo, numero=None,
          tamanho=9.5, cor_texto='#FFFFFF'):
    """Chapa de título com selo numerado embutido à esquerda (disco branco,
    número na cor da chapa). O título centra na chapa inteira."""
    x0 = cx - largura / 2
    ax.add_patch(Rectangle((x0, cy_topo - altura), largura, altura,
                           facecolor=fundo, edgecolor='none', zorder=2, clip_on=False))
    cy = cy_topo - altura / 2
    bloco_texto(ax, cx, cy, titulo, tamanho, cor_texto=cor_texto, peso='medium',
                zorder=4)
    if numero is not None:
        rd = altura * 0.34
        xd = x0 + altura / 2
        ax.add_patch(Circle((xd, cy), rd, facecolor='#FFFFFF', edgecolor='none',
                            zorder=3, clip_on=False))
        bloco_texto(ax, xd, cy, str(numero), tamanho - 1, cor_texto=fundo,
                    peso='medium', zorder=4)
    return cy_topo - altura
