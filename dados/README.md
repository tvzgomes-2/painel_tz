# Dados da tese — Tarifa Zero e grupos econômicos no transporte público coletivo brasileiro

Autor: Thiago Von Zeidler Gomes
Orientadora: Prof.ª Dra. Silvana Zioni

Programa de Pós-Graduação em Planejamento e Gestão do Território, Universidade Federal do ABC (PGT/UFABC).

Esta pasta é o depósito de dados citado na tese. Tudo está na **base congelada de 11 de novembro de 2026**, a última do trabalho, fechada ao fim da coleta dos pedidos de acesso à informação. Cada pacote corresponde ao que o Quadro α.1 do Volume II (Apêndices) atribui a cada apêndice.

## Pacotes

| Pasta | O que contém | Apêndice |
|---|---|---|
| `1_politicas/` | Base de políticas de Tarifa Zero (193 linhas, 187 em escopo), régua descritiva por aba, registro de alterações entre os congelamentos, tabela dos pedidos de acesso à informação, manifestos SHA-256 das cópias congeladas e dicionário das colunas | A, D, H |
| `2_base_municipal/` | Base Municipal v3 (5.570 municípios), dicionário de variáveis, colunas retiradas do depósito e séries | A, B |
| `3_testes/` | Base do teste nacional e resultados (principal e sensibilidade), teste por arranjo e listas de estrato | F |
| `4_grupos/` | Empresas dos 327 grupos econômicos (tabela mestre v5), grupos, unidades de controle e as 217 ligações graduadas, com a escala | A, E |
| `5_arranjo_contratos/` | Arranjo operacional (dimensões D1 a D5) com o livro de códigos, destinatário e contrapartida, preço do quilômetro, custo por habitante, custeio no ato e movimento do incumbente | D, F |
| `6_rsl/` | Revisão sistemática: registro (183), corpus (81) e rede de citações internas | C |
| `7_documentos/` | As 315 normas lidas, reescritas em notas padronizadas (Markdown: ementa, artigos que tratam da gratuidade, vínculo com a Tarifa Zero, fontes e lacunas), o catálogo delas em CSV e o índice dos arquivos de normas e contratos do acervo (com SHA-256) | D, H |
| `8_scripts/` | Roteiros em Python que montam a base, a régua, a rede de sócios, os levantamentos, os testes e as figuras | todos |

## O que ficou de fora, e por quê

- **Colunas de trabalho da base de políticas** (fila de busca, próximos passos, leituras críticas datadas, links de busca): são notas de processo, e não dado. As cópias congeladas completas ficam guardadas pelo autor, e `1_politicas/tz_congelamentos_sha256.txt` traz o SHA-256 de cada uma.
- **Nomes de sócios pessoas físicas**: não aparecem em nenhuma tabela da rede de grupos. A coluna dos sócios principais foi retirada, e nas colunas de nota e de evidência cada nome que coincide com o de um sócio pessoa física do cadastro foi trocado por `[pessoa física]`. Ficam a razão social das empresas e o nome de mercado dos grupos, que são públicos. Quatro roteiros auxiliares de auditoria da rede, que trazem nomes de sócios no código, não foram depositados.
- **CPF, e-mail, telefone e caminhos do acervo de trabalho**: foram retirados de todas as tabelas, e o CPF dos textos salvos já estava mascarado na origem.
- **Comprovantes e respostas dos pedidos de acesso à informação**: só a tabela dos pedidos vai ao depósito, porque os arquivos trazem dados pessoais do requerente e de servidores.
- **Três colunas da Base Municipal v3** (óbitos no trânsito vindos de base privada, sem fonte primária documentada e sem uso nas análises): `2_base_municipal/colunas_retiradas.csv`.
- **Malhas do IBGE**: obtê-las na fonte (Malha Municipal 2022 e Arranjos Populacionais, IBGE).
- **Normas e contratos em PDF**: não vão ao depósito; as normas entram pelas notas padronizadas, e o índice traz o SHA-256 de cada arquivo do acervo. As notas foram limpas de remissões ao acervo de trabalho, e as ligações internas entre elas viraram links relativos.

## Ressalvas de uso

- **Contagens**: use a base de políticas, nunca a aba RESUMO da régua. Não apurado não é zero.
- **Classe por hipótese**: as 26 políticas sem resposta até o fim da coleta (lacuna declarada) têm a classe da hipótese do pedido de acesso à informação, e a coluna correspondente as identifica.
- **Presença de grupo**: a presença de empresa de grupo vem do endereço do cadastro (maio de 2024), e presença não é operação. Vínculo societário mapeado não é prova de controle.
- **Incumbente**: a codificação do incumbente (`incumbente_entrada.csv`) é assistida e não foi conferida caso a caso.

## Licenças e citação

Dados: Creative Commons Atribuição 4.0 (CC BY 4.0). Código: MIT. Ver `../LICENSE.md` e `../CITATION.cff`.

Como citar: GOMES, Thiago Von Zeidler. *Tarifa Zero e grupos econômicos no transporte coletivo brasileiro: dados, scripts e painel da tese de doutorado (PGT/UFABC)*. Versão 2026-11-11. Zenodo, 2026. DOI: https://doi.org/10.5281/zenodo.24186039 (esta versão); https://doi.org/10.5281/zenodo.24186038 (todas as versões).

## Integridade

`SHA256SUMS.txt` traz o SHA-256 de cada arquivo desta pasta.
