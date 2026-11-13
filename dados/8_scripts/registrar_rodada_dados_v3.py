#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""registrar_rodada_dados_v3.py — registra no Diário de pesquisa a rodada de
produção de dados da Base Municipal v3 (21/09/2026) e acrescenta as pendências
que ela abre.

Casa âncora exata e aborta se não bater. Idempotente.

USO  python registrar_rodada_dados_v3.py [--gravar]
"""
import argparse
import datetime
import os
import shutil
import sys

RAIZ = os.environ.get("TZ_VAULT") or os.getcwd()
DIA = os.path.join(RAIZ, "04 - Análises", "Diário de pesquisa",
                   "Diário de pesquisa — 2026-09 (corrente).md")
ANC = "\n## Ligações\n"
MARCA = "21/09/2026 — quatro lacunas da base v3 fechadas"

ENTRADA = """
### 21/09/2026 — quatro lacunas da base v3 fechadas, e o teste que derrubou a hipótese das rotas OSM

#### 🔴 Antes de apurar: rotas do OpenStreetMap **não** são as linhas do sistema

A pergunta era se `n_rotas_onibus_osm` podia servir de denominador para a cobertura proporcional de Kębłowski, fechando a pendência da régua descritiva. **Não pode**, e o teste é direto: dos 35 municípios em que a base-mestre tem `Nº linhas` preenchido e comparável, **31 (89%) têm zero rotas no OSM** — Eusébio/CE tem 90 linhas oficiais e 0 rotas mapeadas; Mariana/MG, 48 e 0. Onde o OSM não é zero, ele erra nos dois sentidos: superestima (Monte Carmelo 5→13, **2,60×**; Rio Branco do Sul 1→4, **4,00×**) e subestima (Silva Jardim 80→4; Caucaia 26→2). **Correlação de Pearson: r = 0,117.**

- **O mecanismo explica os dois erros, e são erros diferentes.** Onde o município não está mapeado, o OSM dá zero — e isso é a regra, não a exceção: **3.036 municípios brasileiros têm mais de 20 ônibus registrados e nenhuma rota no OSM**. Onde está mapeado, o OSM conta `route` (variantes de itinerário, ida e volta separadas), não `route_master` (a linha) — daí a razão de 2,6 a 4 rotas por linha.
- **São Caetano do Sul é o caso que motivou a pergunta, e ilustra o ponto:** 29 rotas no OSM contra **11 linhas** na operação real (base de Grupos Econômicos, ago/2026, e NTU 2026; a NTU 2025 registrava 10). Razão de 2,6 — o mesmo padrão de Monte Carmelo.
- ➡️ **A pendência permanece**, mas muda de natureza: para SCS o número existe e está na própria ficha; o que falta é ele chegar ao campo `Nº linhas` da base-mestre. Para os demais, segue sendo leitura caso a caso. **O que não se pode é usar o OSM como atalho** — seria repetir, no denominador da cobertura, o erro que já derrubou as variáveis de OSM das fichas em 16/09.
- ⚠️ **Consequência editorial:** o Bloco 3 das fichas imprime as rotas do OSM poucas linhas acima da discussão de cobertura. Convida à confusão que este teste desfaz. **A revisar:** ou o bloco diz explicitamente que rota OSM não é linha, ou a informação sai de perto da régua.

#### ✅ FPM — 2019 a 2025, 29 colunas novas, sem baixar nada

O dado já estava no cofre (`contas_alvo_siconfi_v2_2019_2025.csv`, 106.526 linhas); faltava o ETL. Cobertura de **~99%** dos 5.570 municípios em todos os anos.

- **A regra de agregação que a mudança de plano de contas exige** já estava na coluna `papel`: 2022-2025 vêm com total único (`1.7.1.1.51`), 2019-2021 com três componentes a somar (`1.7.1.8.01.x`). ✅ Conferido que os dois planos **nunca co-ocorrem** (0 município-ano com ambos) — não há dupla contagem.
- **🔴 Só o FUNDEB é subtraído, e a decisão é medida.** A razão FUNDEB/bruto tem mediana **0,183**, com p5-p95 de 0,178-0,185 em 36.975 município-ano: é a regra constitucional aparecendo no dado. Já `Deduções - Transferências Constitucionais` aparece em poucos casos e chega a **superar o FPM bruto** (Feira de Santana/BA, 2022: R$ 16,1 mi de dedução contra R$ 12,0 mi de bruto) — o FPM **é** transferência constitucional, não tem dedução desse tipo. Subtraí-la produzia 8 municípios com FPM negativo. Vai em coluna própria, não subtraída.
- **🔴 23 município-ano ficaram VAZIOS de propósito:** onde o FUNDEB declarado supera o próprio bruto, a declaração ao Siconfi está errada e o líquido sairia negativo. **NA ≠ 0** — não se inventa zero nem se publica impossível.
- **Derivadas:** `fpm_liquido_pc_<ano>` e `fpm_share_receita_corrente_2022`. ⚠️ A per capita usa população de 2022 em todos os anos — **compara municípios entre si, não descreve trajetória**.
- ➡️ **Por que interessa à tese:** não como valor, como **dependência fiscal**. Município cujo orçamento é majoritariamente FPM tem pouca receita própria para bancar subsídio permanente, e a política fica exposta à oscilação de um repasse que ele não controla. Conversa direto com a estratificação do custo de saída (B.2.1 das [[Regras de classificacao das reguas]]).

#### ✅ Feridos e óbitos por modo — os 9 modos do SIMU, em 5.570/5.570

O sintoma registrado na ficha de São Caetano do Sul (só 23 dos 69 feridos com modo) tinha causa simples: a base ingeriu **3 de 9 categorias** de ferido, e a que faltava era **motociclista** — a maior do país.

- **A fonte sempre teve as nove.** `SIMU/feridos/simu-feridos-mun-T.csv` e `simu-mortes-mun-T.csv` trazem pedestre · ciclista · motociclista · triciclo · automóvel · caminhonete · veículo pesado · ônibus · outros, para 5.570 municípios, 2010-2019. **Não havia dado a buscar fora do cofre.**
- ✅ **A soma dos 9 modos fecha com o total da fonte em 5.570/5.570 — resíduo zero**, e as 4 colunas antigas batem sem nenhuma divergência.
- **São Caetano, agora completo:** 16 pedestres · 7 ciclistas · **37 motociclistas** · 6 automóvel · 1 caminhonete · 2 outros · **0 ocupantes de ônibus** = 69. O modo que faltava era 54% do total.
- 🔵 **Zero ocupante de ônibus ferido é medida, não lacuna** — e é dado relevante para a tese, não detalhe.

#### ✅ Gini — calculado dos microdados, porque o arquivo do cofre estava corrompido

`osf_vrc59_gomes-filho-2025/gini.xlsx` tem **uma linha e uma coluna**: só o cabeçalho `id_municipio`. Não é resultado incompleto, é arquivo truncado — não há o que recuperar.

- **Calculado do Censo 2022**, tabela de Domicílios do acesso controlado: `D0360` (rendimento domiciliar per capita), `D0111` (peso), `D0150` (moradores), `D0080` (município). **5.570 de 5.570 municípios**, todos com mais de 50 domicílios na amostra.
- **Distribuição:** min 0,277 · p25 0,405 · **mediana 0,436** · p75 0,464 · max 0,713.
- **As decisões de método, declaradas:** a unidade é a **pessoa** (cada domicílio pesa `D0111 × D0150`), não o domicílio — é o que a definição usual do Gini municipal pede; renda **zero entra** (é a cauda que o índice precisa ver) e renda não declarada ficaria de fora (não houve nenhuma: o IBGE imputa); só domicílios particulares permanentes ocupados.
- ✅ **A fórmula foi testada contra casos de resposta fechada** antes de rodar: igualdade perfeita → 0; um domicílio com tudo, n=100 → 0,99 = (n−1)/n; rendas 0,1,2,3,4 → 0,400. Não é código que "parece certo".
- ⚠️ **Restrição de replicação herdada:** os microdados de acesso controlado **não** entram no pacote do Zenodo. O que se deposita é o script e o agregado municipal.

#### 🟡 RAIS — estabelecimentos por município, com o Núcleo Transporte separado, mas **sem o ano confirmado**

- **O cache de FTP de jul/2026 é lixo:** os 54 arquivos de UF em `_meta/scripts/rais_cache/` têm **0 byte**. A fonte boa é `RAIS_ESTAB_PUB.7z` (143 MB → 1,46 GB), que estava lá o tempo todo.
- **Nacional:** 13.463.522 estabelecimentos · **8.651.625 em RAIS negativa (64%)** · 59.970.945 vínculos ativos (= 50,6 mi CLT + 9,4 mi estatutários, soma exata).
- **🔴 RAIS negativa é a distinção que decide o número.** Declarar é obrigatório mesmo sem empregado. Contar tudo infla; contar só quem emprega esconde a empresa que existe e não emprega. A base grava **os três** — total, negativa e com vínculo — e nunca um só.
- **🎯 Núcleo Transporte (4921-3/01 e /02, o recorte canônico de [[Núcleo Transporte]]): 11.052 estabelecimentos · 385.444 vínculos formais · em 1.893 municípios.** A expansão (4922/4929) sai em coluna à parte, **nunca somada**. ➡️ É a primeira medida do setor de ônibus **independente da Receita Federal**: o pipeline CNPJ conta empresa registrada, a RAIS conta empresa que declara emprego formal. Onde divergirem, a divergência é achado do Cap. 7, não erro a reconciliar. ⚠️ **Não comparar com os 14.988 estabelecimentos do pipeline sem antes igualar o recorte de CNAE** — aquele número é do pipeline de 6 CNAEs, este é do núcleo de 2.
- **🔴 O ano do arquivo NÃO está confirmado, e por isso as colunas saíram sem ano no nome.** O layout não traz coluna de ano. O total de 59,97 mi **não reconcilia** com os 54,7 mi publicados para a RAIS 2023, e a razão contra o `vinculos_formais_rais_2022` do SIDRA tem mediana **1,116** (+12%) — compatível com 2024, ou com uma diferença de definição entre o bruto do arquivo e o estoque publicado. **Enquanto não se resolver, é variável de composição e de comparação entre municípios, não de série temporal.**

#### O que ficou de fora, e por quê

- **`Nº linhas` da base-mestre** segue em 35-47 de 180. Não é apurável por script: é leitura caso a caso. Para São Caetano o número já está na ficha (11 linhas) e só precisa ser transposto — **não transpus porque mexer em `Nº linhas` mexe no denominador da régua**, e a regra do cofre é não alterar classificação sem confirmação do autor.
- **Remuneração do operador** (237/272) e **mecanismo de custeio** (212/272) seguem sendo pesquisa documental em contrato. Nenhuma base do cofre os tem — reconferido nesta rodada.

- **Fonte:** `_meta/scripts/enriquecer_base_fpm.py`, `enriquecer_base_sinistralidade_modo.py`, `calcular_gini_censo2022.py`, `agregar_rais_estabelecimentos.py` (todos novos). Backups datados da base v3 antes de cada gravação.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(DIA):
        sys.exit(f"🔴 não achei {DIA}")
    t = open(DIA, encoding="utf-8").read()
    if MARCA in t:
        print("já aplicado. Nada a fazer.")
        return
    if t.count(ANC) != 1:
        sys.exit(f"🔴 âncora '## Ligações' apareceu {t.count(ANC)} vezes. "
                 "Nada escrito.")
    novo = t.replace(ANC, ENTRADA + ANC)
    print(f"{len(t)} → {len(novo)} caracteres (+{len(novo)-len(t)})")
    if not a.gravar:
        print("\nnada foi escrito. Para aplicar: --gravar")
        return
    bk = DIA + ".BACKUP-" + datetime.datetime.now().strftime("%Y%m%d-%H%M") \
        + "-pre-rodada-dados-v3.md"
    shutil.copy2(DIA, bk)
    open(DIA, "w", encoding="utf-8", newline="\n").write(novo)
    print(f"✅ gravado · backup {os.path.basename(bk)}")


if __name__ == "__main__":
    main()
