#!/usr/bin/env bash
# monta rede-ge.html (Rede de empresas): head-ge.html, com a seção "Além do ônibus" (secao-alem.html)
# no lugar de <!--ALEM-->, + rede_ge.json + patrimonio.json + logic-ge.js + logic-pat.js.
# Desde 23/10/2026 as duas partes são uma página só (decisão do autor). logic-pat.js vai dentro
# de uma função, para os nomes dele não colidirem com os de logic-ge.js.
set -e
cd "$(dirname "$0")"
OUT=../rede-ge.html
python3 - <<'PY'
h = open('head-ge.html', encoding='utf-8').read()
s = open('secao-alem.html', encoding='utf-8').read()
assert h.count('<!--ALEM-->') == 1
open('.head-ge-montado.html', 'w', encoding='utf-8').write(h.replace('<!--ALEM-->', s))
PY
{
  cat .head-ge-montado.html
  cat rede_ge.json
  printf '\n</script>\n<script id="data-pat" type="application/json">'
  cat patrimonio.json
  printf '</script>\n<script>\n'
  cat logic-ge.js
  printf '\n</script>\n<script>\n(() => {\n'
  cat logic-pat.js
  printf '\n})();\nif (location.hash.startsWith("#alem")) abreAba("alem");\n</script>\n</body>\n</html>\n'
} > "$OUT"
rm -f .head-ge-montado.html
echo "gerado: $OUT ($(wc -c < "$OUT") bytes)"
