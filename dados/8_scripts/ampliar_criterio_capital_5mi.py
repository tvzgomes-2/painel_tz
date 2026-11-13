"""
Teste 20 (04/08/2026) — Amplia o critério "médio/grande" de tamanho>=3 empresas
para tamanho>=3 OU capital_social_total_reais>=R$5.000.000 (mediana do universo
original de 165 componentes), e revisa o critério de ORDENAÇÃO dos GE-XXX.

Pergunta do autor (encadeada em 3 passos, mesmo dia):
1. "pq temos capital social 0?" -> investigação de cobertura de capital_social_por_cnpj.csv
   levou a recalcular capital por TODOS os 517 componentes da rede v4 (não só os 165
   de tamanho>=3), revelando outliers: componentes de só 2 empresas com capital de
   dezenas/centenas de milhões (Itapemirim R$522mi, "1001"/Rápido Ribeirão Preto
   R$202,7mi, Viação Garcia R$144,7mi, Grupo SOU/Sancetur R$107,6mi, entre outros).
2. "vamos revisar o critério, pode fazer um boxplot desse universo de empresas
   médias/grandes por capital social e ao lado um das pequenas?" -> boxplot log-scale
   comparando os 165 componentes de tamanho>=3 (mediana R$5,65mi) contra os 352 de
   tamanho=2 (mediana R$345mil, mas com cauda superior que ultrapassa boa parte da
   distribuição das médias/grandes).
3. "5 mi - revisar nossa metodologia e reescrever os critérios" -> adoção de
   capital_social_total_reais>=R$5.000.000 como critério ALTERNATIVO (OR) ao tamanho>=3.

Depois, pedido adicional: "vamos revisar os Ids para reorganizarmos pelo capital/no
empresas (capital médio)" -> testei capital_medio_por_empresa (=capital_total/tamanho)
como critério de ORDENAÇÃO principal dos GE-XXX. Resultado mostrado ao autor: Itapemirim
(2 empresas, R$261mi médio) assumiria GE-001, Barata (51 empresas, R$722mi total mas só
R$14,2mi médio) cairia para posição muito inferior -- efeito colateral explícito de que
capital médio favorece estruturalmente componentes de poucas empresas. Autor decidiu:
"talvez seja melhor manter mesmo soma do capital" -> ordenação REVERTIDA para capital
TOTAL (mesmo critério do Teste 19), com capital_medio_por_empresa mantida como coluna
complementar (não como critério de ordenação).

MÉTODO
------
1. Universo: capital_social_por_grupo.csv (517 componentes, cobertura completa —
   tamanho e capital_social_total_reais já calculados para TODOS, não só os 165).
2. Escopo novo: tamanho>=3 OR capital_social_total_reais>=5_000_000.
   Resultado: 223 componentes em escopo (era 165) -> 58 novos, todos tamanho=2.
3. Checagem de âncoras documentadas excluídas (Teste 14 apontava 2 âncoras sócio-
   confirmadas fora dos 165 por tamanho=2): "1001" (Perfil doc, status tentativo,
   componentes 17/25 — não é sócio-âncora, é nome de empresa) e "família Lemes
   Soares"/Andorinha sub-cluster C (componente 768, capital R$300 mil). NENHUMA das
   duas atinge R$5mi -> nenhuma âncora documentada muda de status neste teste.
4. Nomeação dos 58 novos: mesma hierarquia do Teste 14 (sócio-âncora -> holding PJ
   hub -> sobrenome de família PF hub, por sócio em 2+ empresas do componente).
   4 exceções deliberadas onde o algoritmo devolveria um sobrenome genérico mas a
   razão social das 2 empresas já indica marca nacional/regional conhecida — nesses
   casos usei o nome de mercado (origem_nome="nome de mercado", não é confirmação por
   sócio, é leitura direta da razão social, sinalizado como tal):
     - componente 371: "Itapemirim" (Itapemirim Group + Itapemirim Transporte Urbano)
     - componente 5170: "1001 (Rápido Ribeirão Preto)" — Auto Viação 1001 + Rápido
       Ribeirão Preto. ATENÇÃO: mesma marca "1001" já documentada no Perfil doc em
       componente DISTINTO (17/25) — possível fragmentação/homonímia, não fundido.
     - componente 2599: "Garcia" (Viação Garcia + Londrina Sul)
     - componente 399: "Grupo SOU (Sancetur)" — confirmado pelo autor como 2º negócio
       da família Abi Chedid (mesma família do GE-028), ver nota de cruzamento com
       literatura/mídia e ressalva metodológica já registrada em Pendências.
5. Ranking final: por capital_social_total_reais decrescente (não por capital médio —
   ver acima). GE-001..GE-223. Coluna id_grupo_TESTE19 preservada com o id anterior
   para os 165 já existentes (branco para os 58 novos).

RESULTADO
---------
223 grupos (era 165). 164 dos 165 antigos mudam de número (só GE-004/Comporte manteve
a posição, por coincidência). Top do ranking por capital total: GE-001 Barata (sem
mudança, R$722,4mi) > GE-002 Itapemirim (NOVO, R$522mi) > GE-003 Belarmino (era GE-002)
> GE-004 Ruas (era GE-003) > GE-005 Comporte (era GE-004) > GE-006 "1001"/Rápido
Ribeirão Preto (NOVO) > GE-007 Garcia (NOVO) > GE-010 Grupo SOU/Sancetur (NOVO).

3 achados de possível ramo familiar não confirmado (não decididos, ver Pendências):
(a) componente novo com hub sobrenome "Gulin" (Viação Campos Gerais + Transporte
Coletivo Glória) — possível 4ª ramificação da família Gulin (já documentada em 3
componentes: Senestra, Transguara, Gulin+Corleto), sem sócio em comum com nenhuma
das 3; (b) marca "1001" fragmentada em componente desconectado (ver item 4 acima);
(c) sobrenome "Constantino" em 2 componentes novos distintos, além do já documentado
Paiva Constantino — três focos possíveis da mesma família, não testados entre si.

RESSALVA DE COBERTURA (Becker, mandatória)
-------------------------------------------
Os 58 novos componentes NÃO passaram pelo pipeline de expansão de rede nível 2/3
(Testes 13/16/17) nem pela espacialização por município (Teste 18). cluster_id deles
é degenerado (= próprio id_grupo); municípios_atuacao marcado "pendente" na tabela
mestre. Os 2 mapas coropléticos e a aba "Resumo por cluster" da tabela mestre NÃO
foram regerados neste teste — ainda refletem os 165 grupos do Teste 19.

DECISÃO
-------
identificacao_componentes_medios_grandes_v4.csv (223 linhas, colunas novas
capital_medio_por_empresa e criterio_entrada) e capital_social_por_grupo.csv (517
linhas, cobertura completa) regravados. Tabela mestre: aba Empresas com os 116 novos
id_grupo MESCLADOS por CNPJ nas linhas já existentes (bug pego e corrigido durante a
execução — a 1ª tentativa ia inserir 116 linhas duplicadas, pois as 116 empresas já
existiam na planilha de 7.680 sem grupo atribuído); aba Resumo por grupo reconstruída
(223 linhas). Coluna id_grupo_TESTE19 preservada em todos os arquivos.

Ver [[Log de testes metodológicos - Grupos Econômicos (ago-2026)#Teste 20]] para o
registro completo (pergunta / método / resultado / decisão) e [[Pendências]] para os
achados não confirmados e o trabalho ainda pendente (mapas, cluster, rede nível 2/3
para os 58 novos).
"""
