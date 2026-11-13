#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""montar_ntu2025_tz.py — cria `03 - Dados/_data/casos por fonte/NTU 2025 -
TZ maiores cidades.csv`, ficha por ficha, a partir do relatório NTU "Tarifa
Zero nas Cidades do Brasil 2025" (Zotero storage/7MWUZNLA, Série Pesquisas
Temáticas NTU nº4), seção "Caracterização das cidades com tarifa zero
universal" (pág. 19-25) — as 12 cidades com tarifa zero universal e mais de
100 mil habitantes, dados consolidados até maio/2025.

NÃO SOBRESCREVE `NTU 2023.csv` (já existente, tabulado manualmente pelo
autor a partir da edição 2024 do mesmo relatório, 25 cidades >50mil hab.,
snapshot de dados mais antigo) — arquivo NOVO, snapshot mais recente e
recorte diferente (12 cidades >100mil hab.), para preservar histórico
canônico vs. atualização (ver norma do cofre: nunca sobrescrever sem
marcar). Ambos os arquivos têm interseção de 9 municípios (Caucaia,
Luziânia, Maricá, Ibirité, São Caetano do Sul, Itapetininga, Paranaguá,
Balneário Camboriú, Formosa) com valores DIFERENTES de frota/passageiros/
custo entre as duas datas — evolução real, não erro.

USO: python montar_ntu2025_tz.py"""
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..")), "03 - Dados")
OUT_DIR = os.path.join(V, "_data", "casos por fonte")
OUT_CSV = os.path.join(OUT_DIR, "NTU 2025 - TZ maiores cidades.csv")

ROWS = [
    dict(Cidade="Caucaia-CE", Populacao=355679, Data_inicio="Março/2021",
         Passageiros_transportados="90 mil por dia em set/2024 (2,0% vs. set/2023)",
         Frota="54 em fev/2025 (-23% vs. set/2023)", Custo_total_TP_anual_R_milhao=33.6,
         Fonte_de_custeio="Orçamento municipal", Linhas=32, Tipo_operacao="Privada (Empresa Vitória)",
         Regras_utilizacao="Não há catraca no interior dos ônibus",
         Resultados_verificados="Aumento de 25% do faturamento do comércio e serviços; aumento de 25% da arrecadação tributária do município."),
    dict(Cidade="Luziânia-GO", Populacao=208725, Data_inicio="Novembro/2023",
         Passageiros_transportados="17 mil por dia em fev/2025 (31% vs. dez/2023)",
         Frota="24 em fev/2025 (9% vs. nov/2023)", Custo_total_TP_anual_R_milhao=9.3,
         Fonte_de_custeio="Emenda parlamentar", Linhas=24, Tipo_operacao="Privada (Viação Catedral)",
         Regras_utilizacao="Cadastramento e uso de cartão no embarque",
         Resultados_verificados="Comércio varejista: +36% nas vendas; +R$ 25 milhões em circulação na economia local."),
    dict(Cidade="Maricá-RJ", Populacao=197300, Data_inicio="Março/2021",
         Passageiros_transportados="39,3 milhões em 2024 (2,5% vs. 2023)",
         Frota="148 em jan/2025 (10% vs. set/2023)", Custo_total_TP_anual_R_milhao=87.6,
         Fonte_de_custeio="Orçamento municipal incrementado por royalties do petróleo", Linhas=47,
         Tipo_operacao="Pública (EPT)", Regras_utilizacao="Não há catraca no interior dos ônibus",
         Resultados_verificados="Economia de 20% da renda mensal das famílias (segundo a EPT)."),
    dict(Cidade="Ibirité-MG", Populacao=170387, Data_inicio="Janeiro/2021",
         Passageiros_transportados="450 mil em jan/2024 (29% vs. mar/2023)",
         Frota="24 em jan/2024 (0% vs. mai/2023)", Custo_total_TP_anual_R_milhao=9.6,
         Fonte_de_custeio="Orçamento municipal", Linhas=14, Tipo_operacao="Privada (Sidon)",
         Regras_utilizacao="Acesso liberado na catraca", Resultados_verificados="Não identificados."),
    dict(Cidade="São Caetano do Sul-SP", Populacao=165655, Data_inicio="Novembro/2023",
         Passageiros_transportados="74 mil/dia em out/2024 (6% vs. fev/2024)",
         Frota="63 em out/2024 (5% vs. fev/2024)", Custo_total_TP_anual_R_milhao=34.8,
         Fonte_de_custeio="Orçamento municipal (Fundo de Apoio ao Transporte: multas de trânsito + publicidade)",
         Linhas=10, Tipo_operacao="Privada (VIPE)", Regras_utilizacao="Acesso liberado na catraca",
         Resultados_verificados="Redução de remarcações de consultas no SUS; menos veículos de aplicativo/clandestinos no terminal; +36% faturamento no comércio das vias de circulação dos ônibus."),
    dict(Cidade="Itapetininga-SP", Populacao=157790, Data_inicio="Dezembro/2023",
         Passageiros_transportados="Não disponível", Frota="22 em dez/2023 (sem comparação divulgada)",
         Custo_total_TP_anual_R_milhao=6.1, Fonte_de_custeio="Orçamento municipal", Linhas=22,
         Tipo_operacao="Pública", Regras_utilizacao="Acesso liberado na catraca",
         Resultados_verificados="Não identificados."),
    dict(Cidade="Paranaguá-PR", Populacao=145829, Data_inicio="Março/2022",
         Passageiros_transportados="720 mil em ago/2024 (3% vs. mai/2023)",
         Frota="52 em out/2023 (sem comparação divulgada)", Custo_total_TP_anual_R_milhao=24.0,
         Fonte_de_custeio="Fundo de Transporte Coletivo Municipal", Linhas=20,
         Tipo_operacao="Privada (Viação Rocio)", Regras_utilizacao="Cadastramento e uso de cartão no embarque",
         Resultados_verificados="+30% vendas no comércio local; -40% acidentes de trânsito; +~200% demanda no Restaurante Popular."),
    dict(Cidade="Balneário Camboriú-SC", Populacao=139155, Data_inicio="Junho/2023",
         Passageiros_transportados="77 mil em dez/2023 (43% vs. jun/2023)",
         Frota="16 (0% vs. dez/2023)", Custo_total_TP_anual_R_milhao=7.6,
         Fonte_de_custeio="Orçamento municipal", Linhas=5, Tipo_operacao="Privada (Transpiedade)",
         Regras_utilizacao="Acesso liberado na catraca", Resultados_verificados="Não identificados."),
    dict(Cidade="Formosa-GO", Populacao=115669, Data_inicio="Agosto/2021",
         Passageiros_transportados="85 mil em jul/2023 (844% vs. set/2021)",
         Frota="Não disponível", Custo_total_TP_anual_R_milhao=4.3,
         Fonte_de_custeio="Fundo Municipal de Transporte Urbano (inclui receita de estacionamento rotativo)",
         Linhas=4, Tipo_operacao="Privada", Regras_utilizacao="Não disponível",
         Resultados_verificados="Não identificados."),
    dict(Cidade="Sorriso-MT", Populacao=110635, Data_inicio="Maio/2025",
         Passageiros_transportados="Não disponível", Frota="Não disponível",
         Custo_total_TP_anual_R_milhao=None,
         Fonte_de_custeio="Orçamento municipal", Linhas=10,
         Tipo_operacao="Pública (locação de ônibus de empresa privada)", Regras_utilizacao="Não disponível",
         Resultados_verificados="75% dos usuários insatisfeitos com o serviço; 80% relatam que a oferta não atende à necessidade de deslocamento diário."),
    dict(Cidade="Ituiutaba-MG", Populacao=102217, Data_inicio="Julho/2023",
         Passageiros_transportados="98 mil em set/2023 (416% vs. jan/2021 [sic — cf. edição 2024: base jul/2023])",
         Frota="11 (22% vs. jun/2023)", Custo_total_TP_anual_R_milhao=4.5,
         Fonte_de_custeio="Emenda parlamentar", Linhas=10,
         Tipo_operacao="Pública (locação de ônibus e motoristas de empresa privada)",
         Regras_utilizacao="Acesso liberado na catraca", Resultados_verificados="Não identificados."),
    dict(Cidade="Assis-SP", Populacao=101409, Data_inicio="Março/2021",
         Passageiros_transportados="Não disponível", Frota="Não disponível",
         Custo_total_TP_anual_R_milhao=None, Fonte_de_custeio="Orçamento municipal", Linhas=None,
         Tipo_operacao="Privada (Oswaldo Brambilla)", Regras_utilizacao="Não disponível",
         Resultados_verificados="Não identificados (pesquisa à parte, ligada ao PlanMob: 75% dos usuários insatisfeitos; 80% relatam oferta insuficiente)."),
]

FONTE = ("NTU — 'Tarifa zero nas cidades do Brasil 2025' (Série Pesquisas Temáticas NTU nº4), "
         "págs. 19-25. Dados consolidados até maio/2025. As 12 cidades com tarifa zero UNIVERSAL "
         "e população total >100 mil habitantes no país, segundo levantamento próprio da NTU "
         "('Clipping NTU').")


def main():
    df = pd.DataFrame(ROWS)
    df.insert(0, "Fonte", FONTE)
    os.makedirs(OUT_DIR, exist_ok=True)
    df.to_csv(OUT_CSV, sep=";", index=False, encoding="utf-8-sig", lineterminator="\r\n")
    print(f"OK — {OUT_CSV}\n{df.shape[0]} cidades x {df.shape[1]} colunas")


if __name__ == "__main__":
    main()
