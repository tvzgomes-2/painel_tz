# -*- coding: utf-8 -*-
"""
build_tese_pdf.py — gera os PDFs dos dois volumes da tese para a página Dados e conceitos (13/11/2026).
Decisão do autor: publicar antes da defesa, com o texto como está (os nomes podem aparecer).

Pega a revisão "limpa" mais recente de cada volume em 01 - Projeto/Revisão pré-Silvana (até 06-10)/
(o arquivo sem "(trabalho…)" no nome) e converte com o LibreOffice para tese/. Antes, confere:
  - nenhuma marca de revisão (inserção/exclusão controlada) nem comentário no .docx;
  - nenhuma célula de quadro-resumo de ficha com uma letra só (o corte de 11/11, corrigido na r103).
Se a conferência falhar, não gera nada. Rodar de novo a cada revisão nova da tese.
Uso: python3 scripts/build_tese_pdf.py ["Volume I" | "Volume II"]   (da raiz; a conversão leva alguns minutos)
"""
import glob, os, re, shutil, subprocess, sys, tempfile, zipfile
import docx

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
VAULT = os.environ.get('TZ_VAULT') or os.path.join(RAIZ, '..', 'doutorado')
PASTA = os.path.join(VAULT, '01 - Projeto', 'Revisão pré-Silvana (até 06-10)')
SAIDA = {'Volume I - Texto': 'Tese - Volume I - Texto.pdf', 'Volume II - Apêndices': 'Tese - Volume II - Apêndices.pdf'}

def ultimo(vol):
    fs = [f for f in glob.glob(os.path.join(PASTA, f'*Tese - {vol} - r*.docx')) if re.search(r' - r(\d+)\.docx$', f)]
    return max(fs, key=lambda f: int(re.search(r' - r(\d+)\.docx$', f).group(1)))

def confere(f):
    z = zipfile.ZipFile(f); xml = z.read('word/document.xml').decode('utf-8')
    prob = []
    if '<w:ins ' in xml or '<w:del ' in xml: prob.append('tem marcas de revisão (alteração controlada)')
    if 'word/comments.xml' in z.namelist() and '<w:comment ' in z.read('word/comments.xml').decode('utf-8'): prob.append('tem comentários')
    d = docx.Document(f)
    for t in d.tables:
        rows = [[c.text for c in r.cells] for r in t.rows]
        if rows and rows[0] and rows[0][0].startswith('Ficha-resumo'):
            prob += [f'célula cortada: {r[0]} = {r[1]!r}' for r in rows[1:] if len(r) > 1 and len(r[1].strip()) == 1 and r[1].strip().isalpha()]
    return prob

origem, erros = {}, []
VOLS = [v for v in SAIDA if not sys.argv[1:] or any(a in v for a in sys.argv[1:])]   # ex.: python3 scripts/build_tese_pdf.py "Volume II"
for vol in VOLS:
    f = ultimo(vol); origem[vol] = f
    p = confere(f)
    print(f'{os.path.basename(f)}: {"ok" if not p else "; ".join(p[:5])}')
    erros += p
if erros: sys.exit('ERRO: nenhum PDF gerado — corrija a tese e rode de novo.')
os.makedirs(os.path.join(RAIZ, 'tese'), exist_ok=True)
for vol, f in origem.items():
    tmp = tempfile.mkdtemp()
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', tmp, f], check=True, capture_output=True, timeout=900)
    pdf = os.path.join(tmp, os.path.splitext(os.path.basename(f))[0] + '.pdf')
    shutil.copyfile(pdf, os.path.join(RAIZ, 'tese', SAIDA[vol]))
    print(f'tese/{SAIDA[vol]}: {os.path.getsize(os.path.join(RAIZ, "tese", SAIDA[vol]))/1e6:.1f} MB (de {os.path.basename(f)})')
orig = os.path.join(RAIZ, 'tese', 'ORIGEM.txt')
linhas = dict(l.split(' <- ', 1) for l in open(orig, encoding='utf-8').read().splitlines() if ' <- ' in l) if os.path.exists(orig) else {}
linhas.update({SAIDA[v]: os.path.basename(f) for v, f in origem.items()})
open(orig, 'w', encoding='utf-8').write(''.join(f'{k} <- {v}\n' for k, v in sorted(linhas.items())))
