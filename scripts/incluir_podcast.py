#!/usr/bin/env python3
"""
incluir_podcast.py — põe a aba Podcast em dados.html (13/11/2026, v1.0.0).

Edita scripts/build_dados.py por âncoras exatas, com backup (build_dados.py.bak-podcast), para que a página
Dados e conceitos ganhe a aba "Podcast": as duas conversas sobre a tese, com player, download do áudio e da
transcrição, a transcrição para ler e as correções conferidas com o Volume I. Os episódios ficam em
scripts/podcasts.json; os áudios e as transcrições, em assets/podcast/ (fora do depósito dados/).
Roda uma vez; depois, `python3 scripts/build_dados.py` gera a página.

Uso:  python3 scripts/incluir_podcast.py        (da raiz do repositório)
"""
import os, shutil, sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ARQ = os.path.join(RAIZ, 'scripts', 'build_dados.py')
s = open(ARQ, encoding='utf-8').read()
if 'aba-podcast' in s:
    sys.exit('build_dados.py já tem a aba Podcast; nada a fazer.')
shutil.copy2(ARQ, ARQ + '.bak-podcast')

def troca(a, b):
    global s
    c = s.count(a)
    assert c == 1, f'âncora com {c} ocorrência(s), esperado 1: {a[:90]!r}'
    s = s.replace(a, b)

GERA = r'''# ---- Podcast (aba própria): episódios em scripts/podcasts.json; áudios e transcrições em assets/podcast/ ----
POD = json.load(open(os.path.join(RAIZ, 'scripts', 'podcasts.json'), encoding='utf-8'))
def _transcricao(rel):
    p = os.path.join(RAIZ, rel)
    if not os.path.exists(p): return ''
    corpo = open(p, encoding='utf-8').read().split('\n\n', 1)[1]
    out = []
    for b in corpo.strip().split('\n\n'):
        m = re.match(r'^\((\d+:\d+) - (\d+:\d+)\)\n(.*)$', b, re.S)
        if b.startswith('[ATENÇÃO'):
            out.append(f'<p class="aviso">{e(b.strip()[1:-1])}</p>'); continue
        out.append(f'<p><span class="ts">{m.group(1)}</span> {e(m.group(3).strip())}</p>' if m else f'<p>{e(b.strip())}</p>')
    return ''.join(out)
def _episodio(ep):
    au, tx = ep['audio'], ep['transcricao']
    ok = os.path.exists(os.path.join(RAIZ, au))
    tam_au = tam(os.path.getsize(os.path.join(RAIZ, au))) if ok else ''
    ext = os.path.splitext(au)[1][1:].upper()
    def _lin(r):
        av = r[3] if len(r) > 3 else ''
        cls = ' class="av"' if av else ''
        nota = f'<p class="aviso">Atenção — o que a tese diz: {e(av)}</p>' if av else ''
        return f'<tr{cls}><td class="min">{e(r[0])}</td><td>{e(r[1])}{nota}</td><td class="onde">{e(r[2])}</td></tr>'
    rot = ''.join(_lin(r) for r in ep.get('roteiro', []))
    n_av = sum(1 for r in ep.get('roteiro', []) if len(r) > 3 and r[3])
    return (f'<article class="ep" id="podcast-{ep["n"]}"><div class="ep-cab"><span class="ep-n">Parte {ep["n"]}</span>'
            f'<h3>{e(ep["titulo"])}</h3><p class="ep-meta">{e(ep["duracao"])} · {e(ep["capitulos"])}</p></div>'
            f'<p class="ep-res">{e(ep["resumo"])}</p>'
            + (f'<audio controls preload="none" src="{quote(au)}"></audio>' if ok else '<p class="ep-meta">Áudio em preparação.</p>')
            + '<p class="ep-bt">'
            + (f'<a class="btn" href="{quote(au)}" download>Baixar o áudio ({ext}, {tam_au})</a> ' if ok else '')
            + f'<a class="btn sec" href="{quote(tx)}" download>Baixar a transcrição (TXT)</a></p>'
            + (f'<details class="ep-rot" open><summary>Onde está na tese · {len(ep["roteiro"]) - n_av} trechos e {n_av} avisos</summary>'
               f'<div class="tabwrap"><table class="cor rot"><thead><tr><th>Minuto</th><th>Assunto</th><th>Na tese</th></tr></thead><tbody>{rot}</tbody></table></div></details>' if rot else '')
            + f'<details class="ep-tx"><summary>Ler a transcrição</summary><p class="ep-meta">Transcrição automática, sem revisão. Os avisos em destaque dizem o que a tese diz onde a conversa simplifica demais ou erra.</p><div class="tx">{_transcricao(tx)}</div></details></article>')
PODCAST = ('<style>'
    '.pod-intro{max-width:900px;}'
    '.pod-nomes{font-size:12.5px;color:var(--muted);max-width:900px;margin:-4px 0 18px;}'
    '.ep{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px 20px;margin:0 0 18px;}'
    '.ep-cab h3{margin:2px 0 2px;font-size:20px;} .ep-n{display:inline-block;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:#111;background:var(--amarelo);padding:2px 8px;border-radius:4px;}'
    '.ep-meta{font-size:12.5px;color:var(--muted);margin:2px 0;} .ep-res{font-size:14px;line-height:1.6;max-width:900px;}'
    '.ep audio{width:100%;max-width:720px;margin:8px 0 6px;display:block;}'
    '.ep details{margin-top:12px;border-top:1px solid var(--border);padding-top:10px;} .ep details > summary{cursor:pointer;font-weight:700;font-size:14px;}'
    '.ep .tabwrap{overflow-x:auto;margin-top:8px;} table.cor{border-collapse:collapse;width:100%;min-width:640px;font-size:12.5px;}'
    'table.cor th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);padding:6px 8px;border-bottom:1px solid var(--border);}'
    'table.cor td{vertical-align:top;padding:8px;border-bottom:1px solid var(--border);line-height:1.5;} table.cor td.min{white-space:nowrap;font-weight:700;color:var(--amarelo);} table.cor td.onde{font-size:11.5px;color:var(--muted);min-width:110px;}'
    '.aviso{margin:6px 0 2px;padding:6px 10px;border-left:3px solid var(--rosa);background:rgba(255,45,107,.08);font-size:12.5px;line-height:1.5;color:var(--text);} table.cor tr.av td.min{color:var(--rosa);}'
    '.ep .tx{max-height:480px;overflow:auto;font-size:13px;line-height:1.6;padding-right:8px;} .ep .tx .ts{font-size:11px;font-weight:700;color:var(--muted);margin-right:4px;}'
    '</style>'
    f'<p class="intro-aba pod-intro">{e(POD["intro"])}</p>' + (f'<p class="pod-nomes">{e(POD["nomes"])}</p>' if POD.get('nomes') else '')
    + ''.join(_episodio(ep) for ep in POD['episodios']))

'''
troca("pagina = f'''<!DOCTYPE html>", GERA + "pagina = f'''<!DOCTYPE html>")
troca('    <button type="button" role="tab" id="tab-referencias" aria-controls="aba-referencias" data-aba="referencias">Referências</button>\n',
      '    <button type="button" role="tab" id="tab-referencias" aria-controls="aba-referencias" data-aba="referencias">Referências</button>\n'
      '    <button type="button" role="tab" id="tab-podcast" aria-controls="aba-podcast" data-aba="podcast">Podcast</button>\n')
troca('  <section class="aba" id="aba-dados" role="tabpanel" aria-labelledby="tab-dados">',
      '  <section class="aba" id="aba-podcast" role="tabpanel" aria-labelledby="tab-podcast" hidden>\n  {PODCAST}\n  </section>\n'
      '  <section class="aba" id="aba-dados" role="tabpanel" aria-labelledby="tab-dados">')
troca("    else if (h === 'referencias' || (el && el.closest('#aba-referencias'))) abre('referencias', h === 'referencias' ? null : el);",
      "    else if (h === 'referencias' || (el && el.closest('#aba-referencias'))) abre('referencias', h === 'referencias' ? null : el);\n"
      "    else if (h === 'podcast' || (el && el.closest('#aba-podcast'))) abre('podcast', h === 'podcast' ? null : el);")
troca('em Referências, os livros, teses e artigos citados.</p>',
      'em Referências, os livros, teses e artigos citados; em Podcast, três conversas em áudio sobre a tese.</p>')
open(ARQ, 'w', encoding='utf-8').write(s)
print('build_dados.py com a aba Podcast (backup em build_dados.py.bak-podcast). Agora: python3 scripts/build_dados.py')
