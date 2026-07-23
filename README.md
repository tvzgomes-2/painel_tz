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

Comentários de Ivan Pereira Pereira (23/07/2026, WhatsApp) — a incorporar numa próxima versão:

- [ ] Aumentar o tamanho do título do painel
- [ ] Adicionar borda luminosa leve nos municípios com TZ no mapa (destaque visual sutil)
- [ ] Manter a borda dos estados (UF) sempre visível no mapa — hoje, ao filtrar só municípios com TZ, eles ficam "flutuando" sem referência geográfica
- [ ] (Futuro, depende de dados ainda não coletados) Número de viagens antes × depois da adoção da TZ, por município
- [ ] (Futuro, depende de dados ainda não coletados) Investimento em infraestrutura antes × depois da adoção da TZ

Log completo (com o texto original dos comentários) no cofre Obsidian: `03 - Dados/Painel TZ - log de feedback.md`.

## Autoria

**Autor:** Thiago Von Zeidler Gomes
**Orientadora:** Prof.ª Silvana Zioni

## Licença dos dados

Dados de fontes públicas (IBGE, TSE, Siconfi, DENATRAN, Min. Cidades, DATASUS, OSM, NTU). Ver seção "Fontes" no rodapé do painel.
