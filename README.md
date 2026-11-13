# Painel Tarifa Zero × Grupos Econômicos (protótipo)

[![Versão](https://img.shields.io/badge/vers%C3%A3o-1.0.0-2ea44f)](./CHANGELOG.md)
[![Ver online](https://img.shields.io/badge/ver-online-2ea44f)](https://tvzgomes-2.github.io/painel_tz/)
[![Último commit](https://img.shields.io/github/last-commit/tvzgomes-2/painel_tz)](https://github.com/tvzgomes-2/painel_tz/commits/main)
[![Tamanho do repositório](https://img.shields.io/github/repo-size/tvzgomes-2/painel_tz)](https://github.com/tvzgomes-2/painel_tz)
[![Licença código](https://img.shields.io/badge/código-MIT-lightgrey)](./LICENSE.md)
[![Licença dados](https://img.shields.io/badge/dados-CC%20BY%204.0-lightgrey)](./LICENSE.md)
[![DOI](https://zenodo.org/badge/1310360192.svg)](https://doi.org/10.5281/zenodo.24186038)

Painel interativo de trabalho, parte da pesquisa de doutorado sobre Tarifa Zero e grupos econômicos do transporte coletivo no Brasil (PGT/UFABC).

**Instrumento exploratório da tese, na mesma base dela (11/11/2026).** Não substitui a análise da tese; as ressalvas de leitura estão no próprio painel (seção "Notas metodológicas"). Os dados que a tese cita estão em `dados/` e na página de dados do site.

## O que é

Site com páginas independentes da pesquisa de doutorado (era Canoa, desde 13/11/2026 — saída da fase de teste, com as páginas em v1.0.0):

- **Painel Brasil** (`painel.html`, tag "TZ") — a Tarifa Zero no Brasil: as políticas universais e parciais classificadas pela régua descritiva, o mapa dos 5.570 municípios, a comparação com o restante do país (inclusive dentro da mesma faixa de porte), o arranjo contratual, a remuneração do operador e a ficha de cada caso. Cruza a base-mestre de Tarifa Zero com uma base municipal integrada (FINBRA/Siconfi, PIB, frota, MUNIC, REGIC, Censo 2022, PEMOB/SIMU, OSM, TSE, NTU).
- **Rede de empresas** (`rede-ge.html`, tag "GE") — os 327 grupos econômicos do transporte coletivo, em duas abas: **Quem controla** (a rede societária interativa, as unidades de controle, linhagens e federações, a concentração do capital — Tabela 5 da tese — e onde os grupos têm endereço) e **Além do ônibus** (as holdings sócias das empresas dos grupos e as empresas de outros setores a que os sócios delas chegam — Seção 6.4).
- **Dados e conceitos** (`dados.html`) — duas abas: **Dados da tese** (os oito pacotes de `dados/` para baixar, arquivo por arquivo, com tamanho, colunas e dicionário, SHA-256, as duas citações, o DOI e os dois volumes da tese em PDF) e **Conceitos** (os verbetes). Gerada por `scripts/build_dados.py`, que só lê `dados/`; os verbetes têm a fonte em `scripts/verbetes-fonte.html` (`verbetes.html` redireciona para a aba).
- **Pesquisa colaborativa** (`pesquisa.html`).

Nenhuma página publica nome de sócio pessoa física nem CPF. CNPJ aparece só de empresas, quando a fonte documental o traz; o nome de mercado de alguns grupos é o do fundador e é publicado como marca. Vínculo societário mapeado não é prova de controle nem de atuação contra a Tarifa Zero.

Cada página é um arquivo HTML autocontido (dados embutidos) — sem backend, sem dependências externas. Cada uma tem seu próprio número de versão (ver [`VERSIONING.md`](./VERSIONING.md)); o site como um todo é identificado por uma "era" (nome de modo de transporte, em ordem alfabética), trocada só em eventos grandes (novo painel irmão publicado, ou redesign completo).

## Dados da tese (`dados/`)

A pasta [`dados/`](./dados/README.md) é o depósito de dados citado na tese, na **base congelada de 11/11/2026**: base de políticas, régua, Base Municipal v3, testes, rede de grupos sem nomes de sócios pessoas físicas, arranjo e contratos, revisão sistemática, normas padronizadas e scripts, com SHA-256 de cada arquivo. Os números da tese são os desta pasta. DOI de todas as versões no Zenodo: [10.5281/zenodo.24186038](https://doi.org/10.5281/zenodo.24186038), que aponta sempre para a mais recente; a release `dados-v1.0.0`, que a tese cita, é [10.5281/zenodo.24186039](https://doi.org/10.5281/zenodo.24186039).

O painel (`painel.html`, `rede-ge.html`) é o instrumento exploratório da pesquisa e, desde a v1.0.0 (13/11/2026), está na mesma **base de 11/11/2026**: o build lê o congelamento da base-mestre e da régua, o levantamento do arranjo harmonizado com essa base e as tabelas de `dados/5_arranjo_contratos/` (só leitura); as fichas vêm do Apêndice H da tese (r103). A conferência número a número está no `CHANGELOG.md` (Painel Brasil v1.0.0).

## Ver online

**https://tvzgomes-2.github.io/painel_tz/** — abre o hub do site (`index.html`), com acesso às páginas.

## Rodar localmente

Abra `index.html` para o hub, ou `painel.html` diretamente para ir direto ao Painel Brasil.

## Feedback recebido / pendências de ajuste

Ver [`FEEDBACK.md`](./FEEDBACK.md) — log cronológico dos relatos brutos recebidos (identidades anonimizadas). Status de cada item (feito/pendente, versão) vive só no `ROADMAP.md` e no `CHANGELOG.md`, não duplicado ali.

## Plano de melhorias

Ver [`ROADMAP.md`](./ROADMAP.md) — arquitetura do site (hub + páginas) e análise detalhada do Painel Brasil com plano em 5 fases (legibilidade → mapa → grandes números e novos gráficos → estrutura → dados futuros), com tabelas de Status por item, consolidando o feedback recebido e os pedidos da orientação.

## Estrutura do repositório

```
index.html          hub do site — links para as páginas (editado à mão; os números vêm de scripts/atualizar_numeros.py)
dados.html          página "Dados e conceitos" (gerada por scripts/build_dados.py a partir de dados/ e de scripts/verbetes-fonte.html)
tese/               os dois volumes da tese em PDF (gerados por scripts/build_tese_pdf.py a partir do .docx mais recente)
painel.html         página "Painel Brasil" (TZ), publicada (autocontida — não editar direto, ver scripts/)
README.md           este arquivo
CHANGELOG.md         histórico de versões e notas de metodologia/achados, por página
VERSIONING.md        política de versionamento (uma regra, aplicada por página)
FEEDBACK.md          log de relatos brutos recebidos, anonimizado (Painel Brasil) — status fica no ROADMAP/CHANGELOG
ROADMAP.md           arquitetura do site e plano de melhorias em fases (Painel Brasil)
METADADOS.md          dicionário das 54 variáveis embutidas no Painel Brasil
scripts/
  build_data.py       gera municipios_dados.json a partir das fontes brutas (privadas)
  build_stats.py       gera stats.json (agregados/cortes/listas)
  preparar_geometria.sh converte o shapefile do IBGE em topojson simplificado
  montar_html.sh        remonta painel.html a partir de head.html + dados + logic.js
  head.html            estrutura/CSS/controles do Painel Brasil (fonte legível)
  logic.js             lógica do Painel Brasil (mapa, filtros, gráficos — fonte legível)
  remontar_de_painel.py  remonta painel.html a partir de head.html + logic.js + crosswalks,
                         herdando do painel atual os blocos pesados que só o build gera
                         (usar quando a pasta build/ não estiver disponível)
  casos_por_fonte.json   crosswalk estudo acadêmico → município
  casos_por_noticia.json crosswalk reportagem → município
  camadas_tz.json        crosswalk camada da régua descritiva → município
  modal_por_municipio.json   partição modal por município (Censo 2022, 5.570)
  grupos_por_municipio.json  grupos econômicos do transporte por município (796)
  legislacao_tz.json         base legal da TZ por município (137 verificados, 62 com norma)
  build_modal_e_grupos.py    gera os dois primeiros a partir do cofre (fora do git)
  build_legislacao.py        gera o terceiro a partir do levantamento legal do cofre
  build_tudo.sh              monta o site inteiro na ordem certa e para no primeiro erro (conferência com o congelamento e varredura de nomes incluídas)
  build_dados.py             gera ../dados.html a partir de dados/ (só leitura)
  build_tese_pdf.py          gera tese/*.pdf a partir dos volumes da tese
  exportar_colunar.py        gera o bloco de dados enxuto do painel (sem colunas sem uso)
  conferir_congelamento.py   confere o painel contra a base congelada, linha a linha e nos números canônicos
  atualizar_numeros.py       atualiza os números da capa e dos verbetes
  build_legislacao_base.py   gera legislacao_tz.json da base congelada (substitui build_legislacao*.py desde a v1.0.0)
  pessoas_fisicas.py         varre as páginas geradas atrás de nomes de sócios pessoas físicas
```

`painel.html` é gerado, não editado à mão: para mudar algo (cores, filtros, layout), edite `head.html`/`logic.js` em `scripts/` e rode `montar_html.sh` (fluxo canônico, exige a pasta `build/`) ou `remontar_de_painel.py` (quando a `build/` não estiver disponível — herda os blocos pesados do próprio `painel.html`). Ver comentários nos próprios scripts para o passo a passo completo. `index.html` (hub) é pequeno o bastante para editar direto.

## Autoria

**Autor:** Thiago Von Zeidler Gomes
**Orientadora:** Prof.ª Silvana Zioni

## Licença

Código (scripts, `logic.js`, `head.html`): **MIT**. Dados e conteúdo compilados (dataset municipal, bases da tese, painel publicado): **CC BY 4.0**. Ver [`LICENSE.md`](./LICENSE.md) para o texto completo e a nota sobre `painel.html` (que combina os dois). Dados de origem de fontes públicas (IBGE, TSE, Siconfi, DENATRAN, Min. Cidades, DATASUS, OSM, NTU); ver `METADADOS.md` para a fonte de cada variável.
