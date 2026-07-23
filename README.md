# Painel Tarifa Zero × Grupos Econômicos (protótipo)

Painel interativo de trabalho, parte da pesquisa de doutorado sobre Tarifa Zero e grupos econômicos do transporte coletivo no Brasil (PGT/UFABC).

**⚠️ Protótipo — não é uma peça da tese.** Serve para explorar os dados e recolher feedback. Há pendências de qualidade de dados sinalizadas no próprio painel (seção "Notas metodológicas").

## O que é

Mapa coroplético e comparações estatísticas dos 5.570 municípios do Brasil, cruzando a base-mestre de 155 registros de Tarifa Zero universal (145 ativas + 10 encerradas, com uma duplicata conhecida — ver notas no painel) com uma base municipal integrada de ~230 variáveis: FINBRA/Siconfi, PIB (IBGE), frota (DENATRAN), MUNIC 2020, REGIC 2018, Censo 2022, PEMOB/SIMU (Min. Cidades), OSM, TSE 2024, NTU.

Arquivo único autocontido (HTML + dados embutidos) — sem backend, sem dependências externas.

## Ver online

**https://tvzgomes-2.github.io/painel_tz/**

## Rodar localmente

Basta abrir `index.html` em qualquer navegador.

## Feedback recebido / pendências de ajuste

Ver [`FEEDBACK.md`](./FEEDBACK.md) — log cronológico de comentários e backlog de ajustes.

## Estrutura do repositório

```
index.html          painel publicado (autocontido — não editar direto, ver scripts/)
README.md           este arquivo
CHANGELOG.md         histórico de versões e notas de metodologia/achados
FEEDBACK.md          log de comentários recebidos e backlog de ajustes
METADADOS.md          dicionário das 54 variáveis embutidas no painel
scripts/
  build_data.py       gera municipios_dados.json a partir das fontes brutas (privadas)
  build_stats.py       gera stats.json (agregados/cortes/listas)
  preparar_geometria.sh converte o shapefile do IBGE em topojson simplificado
  montar_html.sh        remonta index.html a partir de head.html + dados + logic.js
  head.html            estrutura/CSS/controles do painel (fonte legível)
  logic.js             lógica do painel (mapa, filtros, gráficos — fonte legível)
```

`index.html` é gerado, não editado à mão: para mudar algo (cores, filtros, layout), edite `head.html`/`logic.js` em `scripts/` e rode `montar_html.sh`. Ver comentários nos próprios scripts para o passo a passo completo.

## Autoria

**Autor:** Thiago Von Zeidler Gomes
**Orientadora:** Prof.ª Silvana Zioni

## Licença dos dados

Dados de fontes públicas (IBGE, TSE, Siconfi, DENATRAN, Min. Cidades, DATASUS, OSM, NTU). Ver seção "Fontes" no rodapé do painel.
