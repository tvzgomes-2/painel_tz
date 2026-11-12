# Licença

Este repositório usa **duas licenças separadas**, porque código e dados têm implicações de reuso diferentes — ver detalhes abaixo.

## Código — MIT

Aplica-se a: `scripts/head.html`, `scripts/logic.js`, `scripts/build_data.py`, `scripts/build_stats.py`, `scripts/preparar_geometria.sh`, `scripts/montar_html.sh` (a lógica/metodologia do painel — mapa, filtros, gráficos, pipeline de dados).

```
MIT License

Copyright (c) 2026 Thiago Von Zeidler Gomes

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Dados e conteúdo — CC BY 4.0 (Atribuição)

Aplica-se a: o dataset municipal compilado (`municipios_dados.json`/`stats.json`, embutidos em `painel.html`), as bases da tese depositadas neste repositório, `METADADOS.md`, `CHANGELOG.md`, `FEEDBACK.md` e o painel publicado.

Você tem o direito de compartilhar e adaptar este material, para qualquer fim, inclusive comercial, desde que dê crédito apropriado, indique a licença e diga se fez mudanças (decisão do autor, 11/11/2026; antes, CC BY-NC 4.0).

Texto legal completo: https://creativecommons.org/licenses/by/4.0/legalcode.pt

## ⚠️ Nota sobre `painel.html`

O arquivo publicado (`painel.html`) **contém os dois** — a lógica de exibição (MIT) e o dataset compilado embutido (CC BY 4.0). Os dois podem ser reusados com crédito ao autor. O hub do site (`index.html`) não tem dados embutidos — é só MIT.

## Como citar

Gomes, Thiago Von Zeidler. *Painel Tarifa Zero × Grupos Econômicos (protótipo)*. 2026. Disponível em: https://github.com/tvzgomes-2/painel_tz

## Observação sobre os dados de origem

Os dados brutos usados na compilação (IBGE, TSE, Siconfi, DENATRAN, Ministério das Cidades, DATASUS, OSM, NTU) têm suas próprias licenças/termos de uso como dados públicos — ver `METADADOS.md` para as fontes de cada variável. As licenças acima se aplicam à compilação e ao painel, não substituem os termos das fontes originais.
