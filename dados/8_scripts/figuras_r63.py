# -*- coding: utf-8 -*-
"""figuras_r63.py — figuras da revisão r63 (Cap. 6), no padrão de figuras_padrao.py e diagramas.py.
Saída: _attachments/tese-r63-*.svg + .png. Uso (na raiz do cofre): python "_meta/scripts/figuras_r63.py" [nome ...]
Conteúdo das árvores e cadeias: notas do cofre (historia-grupos-onibus-brasil; Barões do ônibus — matérias;
Partilhas familiares; Sócios de 2º e 3º nível) e cadastro CNPJ de maio de 2024; ver legendas na tese."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import figuras_padrao as fp
from figuras_padrao import *   # noqa
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt

R = {}
def reg(f): R[f.__name__] = f; return f
CL = cor('grafite', 200); CM_ = cor('grafite', 400); CE = cor('grafite', 700); CS = TZ

def caixa(ax, x, ytop, w, txt, fc=None, tc=None, tam=7.6, pad=0.28, sec=None, alinhar='center', h_min=0):
    from diagramas import bloco_texto
    fc = fc or CL; tc = tc or TINTA
    branco = tc == '#FFFFFF'
    xt = x + w / 2 if alinhar == 'center' else x + 0.25
    info = bloco_texto(ax, xt, ytop - pad, txt, tam, largura_cm=w - 0.45, alinhar=alinhar, ancora='topo',
                       entrelinha=1.32, cor_texto=tc, cor_negrito=tc,
                       cor_secundaria=sec or ('#FFFFFF' if branco else TINTA2), escala_secundaria=0.9)
    yb = min(info['base_tinta'] - pad, ytop - h_min)
    ax.add_patch(Rectangle((x, yb), w, ytop - yb, facecolor=fc, edgecolor='none', zorder=2))
    return yb

def seta_v(ax, x, y0, y1, **kw):
    from diagramas import seta
    seta(ax, [(x, y0 - 0.06), (x, y1 + 0.06)], raio=0, espessura=1.2, **kw)

def ramo(ax, xo, y0, xs, y1):
    """tronco de xo (y0) que se abre em setas para cada x em xs, chegando em y1."""
    from diagramas import linha, seta
    ym = (y0 + y1) / 2
    linha(ax, [(xo, y0 - 0.06), (xo, ym)], raio=0, espessura=1.2)
    if len(xs) > 1: linha(ax, [(min(xs), ym), (max(xs), ym)], raio=0, espessura=1.2)
    for x in xs: seta(ax, [(x, ym), (x, y1 + 0.06)], raio=0, espessura=1.2)

# ── Figura 10 (substitui o funil): o método em quatro etapas ───────────────
@reg
def r63_c6_fluxo_metodo():
    from diagramas import tela, ajustar
    fig, ax = tela(16.0, 16.0)
    G = 0.55
    y = caixa(ax, 0.3, 0, 15.4, '**Dados Abertos do CNPJ** //(Receita Federal, maio de 2024): estabelecimentos, empresas e sócios//', CL)
    seta_v(ax, 8.0, y, y - G); y -= G
    y = caixa(ax, 0.3, y, 15.4, '**Etapa 1 · O universo** //(passos 1 a 5; Tabela 4)//\n//delimitação pela atividade, situação ativa, sócios, rede de sócios comuns e recorte de porte//', CE, '#FFFFFF', sec=cor('grafite', 200))
    seta_v(ax, 8.0, y, y - G); y -= G
    y = caixa(ax, 3.3, y, 9.4, '**327 grupos econômicos**\n//1.040 empresas · R$ 8,13 bilhões de capital social · 26 grupos com metade do capital//', CM_, '#FFFFFF')
    xs = (2.75, 8.0, 13.25); ramo(ax, 8.0, y, xs, y - 0.9); y -= 0.9
    # fontes de cada etapa
    fontes = ['//sócios pessoas jurídicas, seguidos até o esgotamento da cadeia e nos sócios das holdings em qualquer setor//',
              '//imprensa, órgão gestor e ANTT, sítios oficiais e processos (136 rodadas)//',
              '//base de Tarifa Zero do Capítulo 5: operador comprovado em contrato, edital, empenho ou norma//']
    tit = ['**Etapa 2 · A rede além do grupo**\n//passo 6//', '**Etapa 3 · A qualificação**\n//passo 7//', '**Etapa 4 · O encontro com a Tarifa Zero**']
    sai = ['famílias, holdings e patrimônio dos sócios; medidas de rede e comunidades; federações',
           'atuação municipal, nome de mercado, colapso e conduta; dispositivos de proteção do incumbente',
           'CNPJ do operador (71) × empresas dos 327 grupos; forma de contratação e remuneração']
    sec_ = ['Seções 6.2 a 6.5', 'Seções 6.1 e 6.6', 'Seção 6.7']
    bots = []
    for i, x in enumerate((0.3, 5.55, 10.8)):
        yb = caixa(ax, x, y, 4.9, tit[i], CS, '#FFFFFF', h_min=1.25)
        yb2 = caixa(ax, x, yb, 4.9, '//fonte://\n' + fontes[i].strip('/'), cor('rosa', 100), TINTA, tam=7.0, h_min=1.55)
        yb3 = caixa(ax, x, yb2, 4.9, '**resultado:** ' + sai[i] + '\n//' + sec_[i] + '//', CL, TINTA, tam=7.0, h_min=1.9)
        bots.append(yb3)
    yb = min(bots)
    for x in xs:
        from diagramas import seta
        seta(ax, [(x, yb - 0.06), (x, yb - 0.6 + 0.06)], raio=0, espessura=1.2, cor_traco=cor('grafite', 400))
    caixa(ax, 0.3, yb - 0.6, 15.4, '**Síntese (6.8) e teste da hipótese (Capítulo 8)** //— o que falta: o operador e o contrato nos municípios sem Tarifa Zero//', cor('grafite', 200), tam=7.4)
    ajustar(fig, ax, margem=0.3)
    salvar(fig, 'tese-r63-c6-fluxo-metodo')

# ── 6.2: quatro famílias, da fundação ao código de grupo ─────────────────
FAM = [
    ('Constantino',
     '**Nenê Constantino** //(Patrocínio/MG, 1931)//\n//frete de carga (1949) · jardineira (1956) · Expresso União (1957 ou 1958)//',
     '//Reunidas Paulista (1979) · partilha entre os filhos nos anos 1990//',
     [('**GE-005 Comporte**', '//os quatro filhos: Piracicabana e outras operadoras; Gol (2001); Metrô BH (2022), VLT da Baixada, Linhas 7, 11, 12 e 13//', True),
      ('**GE-015**', '//Auristela e Cristiane: Pioneira e Planeta, no Distrito Federal (1994)//', True),
      ('**GE-033**', '//Aurivânia: Reunidas Paulista e STU Sorocaba; a Reunidas passa ao Comporte (CADE, 2026)//', True)]),
    ('Barata',
     '**Jacob Barata** //(Belém, 1932 – 2023)//\n//lotação Madureira–Irajá, Rio de Janeiro (1950)//',
     '//compra de empresas em dificuldade: Glória (anos 1960), Guarulhos (1991), Expresso Guanabara (1992), Real Expresso (2009), Sampaio (2014)//',
     [('**GE-001 Guanabara**', '//um só código: 51 empresas; membros da família ligam 26, 11, 9 e 8 delas//', True),
      ('**Holdings**', '//GB Guanabara Participações (9 empresas); sócias de Portugal e dos Estados Unidos//', False),
      ('**Fora do ônibus**', '//Banco Guanabara, duas securitizadoras, revendas de veículos; conselho da RioCard//', False)]),
    ('Gulin',
     '**Princesa dos Campos** //(Paraná, 1934/35)//\n//controle das famílias Gulin, Alberti, Baron e Manfron (1962)//',
     '//Auto Viação Redentor (irmãos Gulin desde 1980) · uma holding por ramo: 30 holdings com o sobrenome//',
     [('**GE-008**', '//Stabile//', True), ('**GE-014**', '//Senestra; Tarifa Zero de Paranaguá//', True),
      ('**GE-017**', '//ramo Dante, Luiz Norberto e Darci//', True), ('**GE-020**', '//Transguara//', True), ('**GE-236**', '//Marechal//', True)]),
    ('Setti Braga',
     '**Família Setti** //(chegada em 1877)//\n//tílburi em São Bernardo do Campo (c. 1910) · linha regular (1925)//',
     '//casamento Setti–Medina Braga (1947) · Auto Viação ABC (1956) · Cacique (1969) · Metra, corredor ABD (1997)//',
     [('**GE-012**', '//terceira e quarta gerações; Auto Viação ABC, Metra e Publix//', True),
      ('**Holdings e fábrica**', '//Nepart; Centro Tecnológico de Tração Elétrica; Eletra//', False),
      ('**Bilhetagem**', '//38,1% do Mondo FIP, que detém 95% da Autopass (imprensa)//', False)]),
]
@reg
def r63_c6_familias():
    from diagramas import tela, ajustar
    fig, ax = tela(16.0, 26.0)
    W = 7.6; X = (0.3, 8.1)
    ytop = [0, 0]
    for k, (nome, raiz, meio, ramos) in enumerate(FAM):
        col = k % 2; x0 = X[col]
        if k == 2: base2 = min(ytop) - 0.9
        y = ytop[col] if k < 2 else base2
        ax.text(x0, y, nome.upper(), fontsize=8.2, fontweight='medium', color=TZ_TXT, va='top', ha='left')
        y -= 0.55
        y = caixa(ax, x0, y, W, raiz, CE, '#FFFFFF', sec=cor('grafite', 200), tam=7.2)
        seta_v(ax, x0 + W / 2, y, y - 0.4); y -= 0.4
        y = caixa(ax, x0, y, W, meio, CL, TINTA, tam=7.0)
        n = len(ramos); g = 0.12; w = (W - g * (n - 1)) / n
        xs = [x0 + i * (w + g) + w / 2 for i in range(n)]
        ramo(ax, x0 + W / 2, y, xs, y - 0.7); y -= 0.7
        bots = []
        for i, (t, d, ge) in enumerate(ramos):
            bots.append(caixa(ax, x0 + i * (w + g), y, w, t + '\n' + d, CS if ge else cor('grafite', 300), '#FFFFFF' if ge else TINTA,
                              tam=6.6 if n > 3 else 6.9, pad=0.2, h_min=1.0))
        ytop[col] = min(bots)
    ajustar(fig, ax, margem=0.3)
    salvar(fig, 'tese-r63-c6-familias')

# ── 6.3: da família ao fundo — cadeias de controle ───────────────────────
CAD = [
    ('Constantino (GE-005)', ['Os quatro irmãos Constantino', 'Aller, Thurgau, Limmat e Vaud S.A.; Comporte Participações S.A. (sócia de 9 empresas)',
                              'Piracicabana e demais operadoras; Itamarati Express, de outro grupo (desde 2007)',
                              'Conselho da Metrô BH S.A.; diretoria do VLT da Baixada; Pagol (crédito direto); Gol (imprensa)']),
    ('Barata (GE-001)', ['Jacob Barata, Jacob Barata Filho, David e Rosane', 'GB Guanabara Participações (9 empresas, 2021–2023); Barraqueiro Brasil, com sócias portuguesas (desde 2010)',
                         '51 empresas do grupo, no Rio de Janeiro, em Fortaleza e no rodoviário',
                         'Banco Guanabara; BGS e Guanabara Securitizadora; Oz Capital; Guanabara Diesel']),
    ('Setti Braga (GE-012)', ['João Antônio e Maria Beatriz Setti Braga', 'Nepart; Centro Tecnológico de Tração Elétrica (sócio das três operadoras, 2014–2016); Ikatu e mais oito holdings',
                              'Auto Viação ABC, Metra e Publix',
                              'Eletra (ônibus elétricos); 38,1% do Mondo FIP, que detém 95% da Autopass (imprensa)']),
]
@reg
def r63_c6_cadeias():
    from diagramas import tela, ajustar, seta
    fig, ax = tela(16.0, 14.0)
    cols = ['Pessoas', 'Holdings', 'Operadoras', 'Fora do ônibus']
    w = 3.55; g = 0.42; xs = [0.3 + i * (w + g) for i in range(4)]
    y = 0
    for i, c in enumerate(cols):
        ax.text(xs[i] + w / 2, y, c, fontsize=7.8, fontweight='medium', color=TINTA2, ha='center', va='top')
    y -= 0.55
    for nome, cel in CAD:
        ax.text(0.3, y, nome.upper(), fontsize=7.8, fontweight='medium', color=TZ_TXT, va='top', ha='left'); y -= 0.45
        fcs = [CE, CM_, CS, CL]; tcs = ['#FFFFFF', '#FFFFFF', '#FFFFFF', TINTA]
        # mede a maior altura e desenha todas iguais
        tmp = []
        for i in range(4):
            tmp.append(caixa(ax, xs[i], y, w, cel[i], fcs[i], tcs[i], tam=6.8, pad=0.2, h_min=0))
        yb = min(tmp)
        for i in range(4):
            ax.add_patch(Rectangle((xs[i], yb), w, y - yb, facecolor=fcs[i], edgecolor='none', zorder=1.9))
        ym = (y + yb) / 2
        for i in range(3):
            seta(ax, [(xs[i] + w + 0.05, ym), (xs[i + 1] - 0.05, ym)], raio=0, espessura=1.2)
        y = yb - 0.45
    ajustar(fig, ax, margem=0.3)
    salvar(fig, 'tese-r63-c6-cadeias-controle')

# ── 6.6: registros da CVM sobre o Mondo FIP ────────────────────────────────
@reg
def r63_c6_cvm():
    from PIL import Image
    A = fp.U / '_attachments'
    arqs = [('a', 'prova CVM - Reag administradora do Mondo FIP (ata 2025-10-16).jpg', (0, 40, 1568, 632),
             'ata da assembleia geral de cotistas de 16/10/2025, realizada pela REAG Trust Administradora de Recursos'),
            ('b', 'prova CVM - Mondo FIP mudanca de administradora (ata 2025-10-17).jpg', (0, 40, 1568, 575),
             'documento eventual de 17/10/2025: novo regulamento, com troca dos prestadores de administração e custódia'),
            ('c', 'prova CVM - Mondo FIP dados gerais (administrador).jpg', (0, 40, 1568, 382),
             'dados gerais do fundo: IDFIP Administração Fiduciária como administradora atual')]
    ims = [(l, Image.open(A / f).convert('RGB').crop(b), t) for l, f, b, t in arqs]
    W = 16.0; hs = [W * im.size[1] / im.size[0] for _, im, _ in ims]
    tit = 0.75; H = sum(hs) + tit * 3 + 0.3
    fig = plt.figure(figsize=(W / 2.54, H / 2.54))
    y = H
    for (l, im, t), h in zip(ims, hs):
        y -= tit
        fig.text(0.0, (y + 0.22) / H, f'({l}) ', fontsize=8, fontweight='medium', color=TINTA, ha='left', va='bottom')
        fig.text(0.6 / W, (y + 0.22) / H, t, fontsize=7.6, color=TINTA2, ha='left', va='bottom')
        y -= h
        ax = fig.add_axes([0, y / H, 1, h / H]); ax.imshow(im); ax.axis('off')
        for sp in ('top', 'bottom', 'left', 'right'):
            ax.add_patch(Rectangle((0, 0), im.size[0] - 1, im.size[1] - 1, fill=False, edgecolor=cor('grafite', 300), lw=0.6))
        y -= 0.1
    salvar(fig, 'tese-r63-c6-cvm-mondo-fip')

if __name__ == '__main__':
    for n in (sys.argv[1:] or list(R)): R[n]()
