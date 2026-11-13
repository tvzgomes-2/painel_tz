#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ocr_norma.py — OCR de normas digitalizadas, com o pacote de idioma garantido.

MOTIVO DE EXISTIR (09/09/2026): o `tesseract` sem o pacote `tesseract-ocr-por`
NÃO dá erro — devolve texto vazio. Em 09/09/2026 isso quase fez o Contrato
003/2024 de Cantagalo ser classificado como "PDF sem camada de texto", e foi o
que degradou o primeiro OCR da Lei 501/2014 de Mário Campos (acentos corrompidos:
"servi¢o", "Cédigo", "nio podendo"). Este script falha ALTO em vez de calar.

USO
    python3 ocr_norma.py <arquivo.pdf> [--dpi 110] [--paginas 1-3] [--forcar]

SAÍDA
    "<mesmo nome> - OCR.txt", ao lado do PDF (precedente: Mário Campos/MG).

NOTAS DE AMBIENTE
  - A VM local tem limite de ~120 s por chamada: use --paginas para fatiar
    documentos longos. Páginas grandes (ex.: 1965x2894 pt) estouram o tempo a
    200 dpi; 110-150 dpi resolve com qualidade suficiente para leitura.
  - Se não houver rede para o apt, o script diz o que instalar e para.
"""
import os, re, sys, glob, shutil, argparse, subprocess, tempfile

def sh(cmd, timeout=None):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)

def exige_idioma(lang='por'):
    if not shutil.which('tesseract'):
        sys.exit("ERRO: tesseract não instalado. Instale: apt-get install -y tesseract-ocr")
    langs = sh('tesseract --list-langs').stdout.splitlines()
    if lang in [l.strip() for l in langs]:
        return True
    print("AVISO: pacote de idioma '%s' ausente — tentando instalar..." % lang)
    r = sh('apt-get install -y tesseract-ocr-%s' % lang, timeout=180)
    langs = sh('tesseract --list-langs').stdout.splitlines()
    if lang in [l.strip() for l in langs]:
        print("OK: '%s' instalado." % lang); return True
    sys.exit("ERRO: não foi possível instalar 'tesseract-ocr-%s'.\n"
             "      NÃO prossiga sem ele: o tesseract devolveria texto VAZIO sem avisar,\n"
             "      e o documento seria classificado erradamente como 'sem camada de texto'.\n"
             "      Instale manualmente e rode de novo." % lang)

def tem_texto(pdf):
    r = sh('pdftotext -layout "%s" -' % pdf)
    return len(re.sub(r'\s', '', r.stdout)) >= 200

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf'); ap.add_argument('--dpi', type=int, default=110)
    ap.add_argument('--paginas', default=''); ap.add_argument('--lang', default='por')
    ap.add_argument('--forcar', action='store_true',
                    help='OCR mesmo que o PDF já tenha camada de texto')
    a = ap.parse_args()
    if not os.path.isfile(a.pdf): sys.exit("ERRO: arquivo não encontrado: %s" % a.pdf)
    exige_idioma(a.lang)
    if tem_texto(a.pdf) and not a.forcar:
        sys.exit("Este PDF JÁ tem camada de texto — use pdftotext -layout. (--forcar para OCR mesmo assim)")
    fl = ll = None
    if a.paginas:
        m = re.match(r'^(\d+)(?:-(\d+))?$', a.paginas)
        if not m: sys.exit("ERRO: --paginas aceita '3' ou '2-5'")
        fl = int(m.group(1)); ll = int(m.group(2) or m.group(1))
    tmp = tempfile.mkdtemp(prefix='ocr_')
    rng = ('-f %d -l %d' % (fl, ll)) if fl else ''
    r = sh('pdftoppm %s -r %d -png "%s" "%s/pg"' % (rng, a.dpi, a.pdf, tmp), timeout=300)
    pngs = sorted(glob.glob(tmp + '/pg-*.png'))
    if not pngs: sys.exit("ERRO: pdftoppm não gerou imagem. %s" % r.stderr[:200])
    partes = []
    for p in pngs:
        t = sh('tesseract "%s" - -l %s' % (p, a.lang), timeout=120).stdout
        print("  %s: %d caracteres" % (os.path.basename(p), len(t)))
        partes.append(t)
    txt = '\n'.join(partes)
    if len(re.sub(r'\s', '', txt)) < 100:
        sys.exit("ERRO: OCR devolveu quase nada. Verifique o idioma e a resolução — "
                 "NÃO conclua que o documento é ilegível sem checar as duas coisas.")
    base = re.sub(r'\.pdf$', '', a.pdf, flags=re.I)
    suf = ' - OCR.txt' if not a.paginas else ' - OCR pp%s.txt' % a.paginas
    out = base + suf
    with open(out, 'w', encoding='utf-8') as f: f.write(txt)
    shutil.rmtree(tmp, ignore_errors=True)
    print("\nGravado: %s (%d caracteres)" % (out, len(txt)))

if __name__ == '__main__':
    main()
