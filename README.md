# Painel Tarifa Zero × Grupos Econômicos (protótipo)

[![Status](https://img.shields.io/badge/status-prot%C3%B3tipo-orange)](./CHANGELOG.md)
[![Ver online](https://img.shields.io/badge/ver-online-2ea44f)](https://tvzgomes-2.github.io/painel_tz/)
[![Último commit](https://img.shields.io/github/last-commit/tvzgomes-2/painel_tz)](https://github.com/tvzgomes-2/painel_tz/commits/main)
[![Tamanho do repositório](https://img.shields.io/github/repo-size/tvzgomes-2/painel_tz)](https://github.com/tvzgomes-2/painel_tz)
[![Licença código](https://img.shields.io/badge/código-MIT-lightgrey)](./LICENSE.md)
[![Licença dados](https://img.shields.io/badge/dados-CC%20BY--NC%204.0-lightgrey)](./LICENSE.md)

Painel interativo de trabalho, parte da pesquisa de doutorado sobre Tarifa Zero e grupos econômicos do transporte coletivo no Brasil (PGT/UFABC).

**⚠️ Protótipo — não é uma peça da tese.** Serve para explorar os dados e recolher feedback. Há pendências de qualidade de dados sinalizadas no próprio painel (seção "Notas metodológicas").

## O que é

Site com páginas independentes da pesquisa de doutorado (Era Bicicleta, lançamento de teste de 23/10/2026):

- **Painel Brasil** (`painel.html`, tag "TZ") — a Tarifa Zero no Brasil: as políticas universais e parciais classificadas pela régua descritiva, o mapa dos 5.570 municípios, a comparação com o restante do país (inclusive dentro da mesma faixa de porte), o arranjo contratual, a remuneração do operador e a ficha de cada caso. Cruza a base-mestre de Tarifa Zero com uma base municipal integrada (FINBRA/Siconfi, PIB, frota, MUNIC, REGIC, Censo 2022, PEMOB/SIMU, OSM, TSE, NTU).
- **Rede de empresas** (`rede-ge.html`, tag "GE") — os 327 grupos econômicos do transporte coletivo, em duas abas: **Quem controla** (a rede societária interativa, as unidades de controle, linhagens e federações, a concentração do capital — Tabela 5 da tese — e onde os grupos têm endereço) e **Além do ônibus** (as holdings sócias das empresas dos grupos e as empresas de outros setores a que os sócios delas chegam — Seção 6.4).
- **Verbetes** (`verbetes.html`) e **Pesquisa colaborativa** (`pesquisa.html`).

Nenhuma página publica nome de sócio pessoa física, CPF ou CNPJ. Vínculo societário mapeado não é prova de controle nem de atuação contra a Tarifa Zero.

Cada página é um arquivo HTML autocontido (dados embutidos) — sem backend, sem dependências externas. Cada uma tem seu próprio número de versão (ver [`VERSIONING.md`](./VERSIONING.md)); o site como um todo é identificado por uma "era" (nome de modo de transporte, em ordem alfabética), trocada só em eventos grandes (novo painel irmão publicado, ou redesign completo).

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
index.html          hub do site — links para as páginas (editado à mão, é pequeno)
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
```

`painel.html` é gerado, não editado à mão: para mudar algo (cores, filtros, layout), edite `head.html`/`logic.js` em `scripts/` e rode `montar_html.sh` (fluxo canônico, exige a pasta `build/`) ou `remontar_de_painel.py` (quando a `build/` não estiver disponível — herda os blocos pesados do próprio `painel.html`). Ver comentários nos próprios scripts para o passo a passo completo. `index.html` (hub) é pequeno o bastante para editar direto.

## Autoria

**Autor:** Thiago Von Zeidler Gomes
**Orientadora:** Prof.ª Silvana Zioni

## Licença

Código (scripts, `logic.js`, `head.html`): **MIT**. Dados e conteúdo compilados (dataset municipal, painel publicado): **CC BY-NC 4.0** — uso comercial reservado ao autor/Polo Planejamento. Ver [`LICENSE.md`](./LICENSE.md) para o texto completo e a nota sobre `painel.html` (que combina os dois). Dados de origem de fontes públicas (IBGE, TSE, Siconfi, DENATRAN, Min. Cidades, DATASUS, OSM, NTU); ver `METADADOS.md` para a fonte de cada variável.
