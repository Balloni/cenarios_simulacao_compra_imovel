import math
from dataclasses import dataclass

import pandas as pd
import streamlit as st
import altair as alt


st.set_page_config(
    page_title="Comprar ou alugar? Simulador de decisão imobiliária",
    page_icon="🏠",
    layout="wide",
)


CUSTOM_CSS = """
<style>
:root {
  --bg:#F8FAFC;
  --panel:#FFFFFF;
  --panel2:#F1F5F9;
  --text:#0F172A;
  --muted:#64748B;
  --border:#E2E8F0;
  --blue:#2563EB;
  --green:#059669;
  --amber:#D97706;
}
.main { background: var(--bg); }
.block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1180px; }
.hero {
  background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 55%, #2563EB 100%);
  color: white;
  border-radius: 24px;
  padding: 32px;
  margin-bottom: 24px;
  box-shadow: 0 16px 36px rgba(15,23,42,.16);
}
.hero h1 {
  margin: 0;
  font-size: 2.3rem;
  letter-spacing: -0.04em;
}
.hero p {
  color: #DBEAFE;
  font-size: 1.05rem;
  max-width: 850px;
  margin-top: 12px;
}
.badge {
  display: inline-block;
  background: rgba(255,255,255,.14);
  border: 1px solid rgba(255,255,255,.22);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: .82rem;
  color: #EFF6FF;
  margin-bottom: 14px;
}
.metric-card {
  background: white;
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 20px;
  box-shadow: 0 8px 22px rgba(15,23,42,.06);
  min-height: 130px;
}
.metric-label {
  color: var(--muted);
  font-size: .85rem;
  margin-bottom: 8px;
}
.metric-value {
  color: var(--text);
  font-size: 1.65rem;
  font-weight: 750;
  line-height: 1.15;
}
.metric-note {
  color: var(--muted);
  font-size: .82rem;
  margin-top: 8px;
}
.section-title {
  font-size: 1.2rem;
  font-weight: 750;
  color: var(--text);
  margin: 18px 0 6px;
}
.small-muted {
  color: var(--muted);
  font-size: .9rem;
}
.warning-box {
  background: #FFFBEB;
  border: 1px solid #FDE68A;
  color: #78350F;
  border-radius: 16px;
  padding: 14px 16px;
  font-size: .92rem;
}
.method-box {
  background: white;
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 16px;
  color: var(--text);
}
div[data-testid="stMetricValue"] { font-size: 1.5rem; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def brl(value: float) -> str:
    if value is None or pd.isna(value):
        return "—"
    value = float(value)
    sign = "-" if value < 0 else ""
    value = abs(value)
    return sign + "R$ " + f"{value:,.0f}".replace(",", ".")


def brl_k(value: float) -> str:
    if value is None or pd.isna(value):
        return "—"
    value = float(value)
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000:
        return sign + "R$ " + f"{value/1_000_000:.2f}".replace(".", ",") + " mi"
    return sign + "R$ " + f"{value/1_000:.0f}".replace(".", ",") + " mil"


@dataclass
class Params:
    valor_imovel: float
    entrada_pct: float
    taxa_fin_aa: float
    rendimento_aa: float
    valorizacao_aa: float
    correcao_aluguel_aa: float
    aluguel_inicial: float
    fgts_inicial: float
    fgts_anual: float
    anos: int
    prazo_fin_anos: int
    usar_fgts: bool
    custos_compra_pct: float
    manutencao_pct_aa: float
    venda_pct: float


def parcela_price(principal: float, taxa_mensal: float, n_meses: int) -> float:
    if principal <= 0:
        return 0.0
    if taxa_mensal == 0:
        return principal / n_meses
    fator = (1 + taxa_mensal) ** n_meses
    return principal * (taxa_mensal * fator) / (fator - 1)


def simulate(params: Params):
    meses = params.anos * 12
    n_fin = params.prazo_fin_anos * 12

    entrada = params.valor_imovel * params.entrada_pct
    principal = params.valor_imovel - entrada

    t_fin_m = (1 + params.taxa_fin_aa) ** (1 / 12) - 1
    t_inv_m = (1 + params.rendimento_aa) ** (1 / 12) - 1
    t_val_m = (1 + params.valorizacao_aa) ** (1 / 12) - 1
    t_alug_m = (1 + params.correcao_aluguel_aa) ** (1 / 12) - 1

    parcela = parcela_price(principal, t_fin_m, n_fin)
    custo_compra = params.valor_imovel * params.custos_compra_pct

    saldo_sem_fgts = principal
    saldo_com_fgts = principal
    fgts_saldo = params.fgts_inicial if params.usar_fgts else 0.0

    # No cenário de aluguel, a pessoa investe o capital que seria usado na compra:
    # entrada + custos de aquisição. O FGTS fica separado, porque não é livremente sacável.
    investimento_aluguel = entrada + custo_compra

    rows = []
    amortizacoes = []
    aluguel_mes = params.aluguel_inicial

    for mes in range(0, meses + 1):
        ano_frac = mes / 12
        valor_imovel_atual = params.valor_imovel * ((1 + t_val_m) ** mes)

        patrimonio_sem_fgts = valor_imovel_atual - saldo_sem_fgts
        patrimonio_com_fgts = valor_imovel_atual - saldo_com_fgts
        patrimonio_aluguel = investimento_aluguel

        # Custo hipotético de venda ao fim do período, para não tratar imóvel como 100% líquido.
        if mes == meses and params.venda_pct > 0:
            patrimonio_sem_fgts -= valor_imovel_atual * params.venda_pct
            patrimonio_com_fgts -= valor_imovel_atual * params.venda_pct

        rows.append({
            "mes": mes,
            "ano": round(ano_frac, 2),
            "valor_imovel": valor_imovel_atual,
            "saldo_sem_fgts": saldo_sem_fgts,
            "saldo_com_fgts": saldo_com_fgts,
            "patrimonio_financia_sem_fgts": patrimonio_sem_fgts,
            "patrimonio_financia_com_fgts": patrimonio_com_fgts,
            "patrimonio_aluga_investe": patrimonio_aluguel,
            "aluguel_mes": aluguel_mes,
            "parcela": parcela,
            "fgts_saldo": fgts_saldo,
        })

        if mes == meses:
            break

        # 1) investimento do aluguel rende
        investimento_aluguel *= (1 + t_inv_m)

        # 2) no aluguel, a diferença mensal entre parcela+custo de manutenção e aluguel é investida
        manutencao_mes = (valor_imovel_atual * params.manutencao_pct_aa) / 12
        custo_mensal_comprar = parcela + manutencao_mes
        diferenca = custo_mensal_comprar - aluguel_mes
        investimento_aluguel += diferenca

        # 3) financiamento evolui
        if saldo_sem_fgts > 0:
            juros = saldo_sem_fgts * t_fin_m
            amort = max(0.0, parcela - juros)
            saldo_sem_fgts = max(0.0, saldo_sem_fgts - amort)

        if saldo_com_fgts > 0:
            juros = saldo_com_fgts * t_fin_m
            amort = max(0.0, parcela - juros)
            saldo_com_fgts = max(0.0, saldo_com_fgts - amort)

        # 4) FGTS acumulando e amortizando a cada 24 meses
        if params.usar_fgts:
            fgts_saldo += params.fgts_anual / 12
            if (mes + 1) % 24 == 0 and saldo_com_fgts > 0 and fgts_saldo > 0:
                amort_fgts = min(fgts_saldo, saldo_com_fgts)
                saldo_com_fgts -= amort_fgts
                fgts_saldo -= amort_fgts
                amortizacoes.append({
                    "ano": (mes + 1) // 12,
                    "amortizacao_fgts": amort_fgts,
                    "saldo_devedor_apos": saldo_com_fgts,
                })

        aluguel_mes *= (1 + t_alug_m)

    df = pd.DataFrame(rows)

    long_df = df[["ano", "patrimonio_financia_com_fgts", "patrimonio_financia_sem_fgts", "patrimonio_aluga_investe"]].melt(
        id_vars="ano",
        var_name="cenario",
        value_name="patrimonio",
    )
    labels = {
        "patrimonio_financia_com_fgts": "Financia + FGTS",
        "patrimonio_financia_sem_fgts": "Financia sem FGTS",
        "patrimonio_aluga_investe": "Aluga + investe",
    }
    long_df["cenario"] = long_df["cenario"].map(labels)

    final = df.iloc[-1].to_dict()
    resultados = {
        "Financia + FGTS": final["patrimonio_financia_com_fgts"],
        "Financia sem FGTS": final["patrimonio_financia_sem_fgts"],
        "Aluga + investe": final["patrimonio_aluga_investe"],
    }
    vencedor = max(resultados, key=resultados.get)
    segundo = sorted(resultados.values(), reverse=True)[1]
    diferenca = resultados[vencedor] - segundo

    return df, long_df, pd.DataFrame(amortizacoes), {
        "entrada": entrada,
        "principal": principal,
        "parcela": parcela,
        "custo_compra": custo_compra,
        "vencedor": vencedor,
        "diferenca": diferenca,
        "resultados": resultados,
    }


st.markdown(
    """
    <div class="hero">
      <div class="badge">Projeto pessoal · analytics · moradia na Grande São Paulo</div>
      <h1>Comprar ou alugar?</h1>
      <p>
        Um simulador para comparar financiamento, uso de FGTS, aluguel e custo de oportunidade.
        A ideia é transformar uma decisão cotidiana em uma análise orientada a dados.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)


with st.sidebar:
    st.header("Premissas")

    valor_imovel = st.slider("Valor do imóvel", 300_000, 600_000, 350_000, 10_000, format="R$ %d")
    entrada_pct = st.slider("Entrada", 10, 80, 60, 5) / 100
    aluguel_inicial = st.slider("Aluguel inicial mensal", 1_000, 5_000, 1_800, 100, format="R$ %d")

    st.divider()

    taxa_fin_aa = st.slider("Taxa do financiamento a.a.", 6.0, 15.0, 11.19, 0.25) / 100
    rendimento_aa = st.slider("Rendimento líquido a.a.", 4.0, 16.0, 9.5, 0.25) / 100
    valorizacao_aa = st.slider("Valorização do imóvel a.a.", 0.0, 12.0, 5.0, 0.5) / 100
    correcao_aluguel_aa = st.slider("Correção do aluguel a.a.", 0.0, 12.0, 6.0, 0.5) / 100

    st.divider()

    fgts_inicial = st.slider("FGTS acumulado hoje", 0, 100_000, 25_000, 5_000, format="R$ %d")
    fgts_anual = st.slider("Depósito anual de FGTS", 0, 30_000, 10_000, 1_000, format="R$ %d")
    usar_fgts = st.toggle("Usar FGTS a cada 24 meses", value=True)

    st.divider()

    anos = st.slider("Horizonte da análise", 5, 30, 10, 1)
    prazo_fin_anos = st.slider("Prazo do financiamento", 5, 35, 30, 5)
    custos_compra_pct = st.slider("Custos de compra: ITBI, registro etc.", 0.0, 8.0, 4.0, 0.5) / 100
    manutencao_pct_aa = st.slider("Manutenção/IPTU/condomínio extra a.a.", 0.0, 3.0, 1.0, 0.25) / 100
    venda_pct = st.slider("Custo de venda no fim", 0.0, 8.0, 0.0, 0.5) / 100


params = Params(
    valor_imovel=valor_imovel,
    entrada_pct=entrada_pct,
    taxa_fin_aa=taxa_fin_aa,
    rendimento_aa=rendimento_aa,
    valorizacao_aa=valorizacao_aa,
    correcao_aluguel_aa=correcao_aluguel_aa,
    aluguel_inicial=aluguel_inicial,
    fgts_inicial=fgts_inicial,
    fgts_anual=fgts_anual,
    anos=anos,
    prazo_fin_anos=prazo_fin_anos,
    usar_fgts=usar_fgts,
    custos_compra_pct=custos_compra_pct,
    manutencao_pct_aa=manutencao_pct_aa,
    venda_pct=venda_pct,
)

df, long_df, amort_df, resumo = simulate(params)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-label">Melhor cenário</div>
          <div class="metric-value">{resumo["vencedor"]}</div>
          <div class="metric-note">no horizonte de {anos} anos</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-label">Vantagem sobre o 2º colocado</div>
          <div class="metric-value">{brl_k(resumo["diferenca"])}</div>
          <div class="metric-note">diferença estimada de patrimônio líquido</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-label">Parcela estimada</div>
          <div class="metric-value">{brl(resumo["parcela"])}/mês</div>
          <div class="metric-note">financiando {brl_k(resumo["principal"])} em {prazo_fin_anos} anos</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="section-title">Evolução do patrimônio líquido</div>', unsafe_allow_html=True)
st.caption("Patrimônio líquido = ativos estimados menos dívida restante. No aluguel, a entrada e a diferença mensal são investidas.")

chart = (
    alt.Chart(long_df)
    .mark_line(point=False, strokeWidth=3)
    .encode(
        x=alt.X("ano:Q", title="Ano"),
        y=alt.Y("patrimonio:Q", title="Patrimônio líquido", axis=alt.Axis(format="~s")),
        color=alt.Color(
            "cenario:N",
            title="Cenário",
            scale=alt.Scale(
                domain=["Financia + FGTS", "Financia sem FGTS", "Aluga + investe"],
                range=["#059669", "#2563EB", "#D97706"],
            ),
        ),
        tooltip=[
            alt.Tooltip("ano:Q", title="Ano", format=".1f"),
            alt.Tooltip("cenario:N", title="Cenário"),
            alt.Tooltip("patrimonio:Q", title="Patrimônio", format=",.0f"),
        ],
    )
    .properties(height=420)
)
st.altair_chart(chart, use_container_width=True)

r1, r2, r3 = st.columns(3)
resultados = resumo["resultados"]
r1.metric("Financia + FGTS", brl_k(resultados["Financia + FGTS"]))
r2.metric("Financia sem FGTS", brl_k(resultados["Financia sem FGTS"]))
r3.metric("Aluga + investe", brl_k(resultados["Aluga + investe"]))

tab1, tab2, tab3, tab4 = st.tabs(["Leitura do resultado", "FGTS", "Dados mês a mês", "Metodologia"])

with tab1:
    st.markdown("### O que mais muda o resultado?")
    st.write(
        """
        A decisão é muito sensível a três premissas: valorização do imóvel, rendimento líquido dos investimentos
        e relação entre parcela e aluguel. Pequenas mudanças nesses pontos podem inverter o cenário vencedor.
        """
    )

    st.markdown(
        f"""
        <div class="warning-box">
        <strong>Importante:</strong> este simulador é educacional. Ele não é recomendação financeira e ainda simplifica pontos como
        tributação de investimentos, seguros, regras específicas de financiamento, liquidez do imóvel e riscos individuais.
        </div>
        """,
        unsafe_allow_html=True,
    )

with tab2:
    st.markdown("### Amortizações simuladas com FGTS")
    if amort_df.empty:
        st.info("Nenhuma amortização de FGTS ocorreu no horizonte selecionado.")
    else:
        show = amort_df.copy()
        show["amortizacao_fgts"] = show["amortizacao_fgts"].map(brl)
        show["saldo_devedor_apos"] = show["saldo_devedor_apos"].map(brl)
        st.dataframe(show, use_container_width=True, hide_index=True)

    saldo_df = df[["ano", "saldo_com_fgts", "saldo_sem_fgts"]].melt(
        id_vars="ano",
        var_name="tipo",
        value_name="saldo_devedor",
    )
    saldo_df["tipo"] = saldo_df["tipo"].map({
        "saldo_com_fgts": "Com FGTS",
        "saldo_sem_fgts": "Sem FGTS",
    })
    saldo_chart = (
        alt.Chart(saldo_df)
        .mark_line(strokeWidth=3)
        .encode(
            x=alt.X("ano:Q", title="Ano"),
            y=alt.Y("saldo_devedor:Q", title="Saldo devedor", axis=alt.Axis(format="~s")),
            color=alt.Color("tipo:N", title="Cenário", scale=alt.Scale(range=["#059669", "#2563EB"])),
            tooltip=["ano:Q", "tipo:N", alt.Tooltip("saldo_devedor:Q", format=",.0f")],
        )
        .properties(height=320)
    )
    st.altair_chart(saldo_chart, use_container_width=True)

with tab3:
    st.markdown("### Base da simulação")
    table = df.copy()
    cols = [
        "mes", "ano", "valor_imovel", "saldo_com_fgts", "saldo_sem_fgts",
        "patrimonio_financia_com_fgts", "patrimonio_financia_sem_fgts",
        "patrimonio_aluga_investe", "aluguel_mes", "parcela", "fgts_saldo"
    ]
    table = table[cols]
    st.dataframe(table, use_container_width=True, hide_index=True)
    csv = table.to_csv(index=False).encode("utf-8")
    st.download_button("Baixar CSV da simulação", csv, "simulacao_moradia.csv", "text/csv")

with tab4:
    st.markdown(
        """
        <div class="method-box">
        <strong>Como a comparação foi estruturada</strong><br><br>
        1. Os cenários partem do mesmo capital inicial: entrada + custos de aquisição.<br>
        2. No cenário de compra, a entrada vira patrimônio no imóvel e o saldo devedor cai com as parcelas.<br>
        3. No cenário de aluguel, o capital inicial fica investido e a diferença entre comprar e alugar é aplicada mês a mês.<br>
        4. O FGTS, quando ativado, acumula mensalmente e amortiza o saldo devedor a cada 24 meses.<br>
        5. O resultado final compara patrimônio líquido estimado, não fluxo de caixa de curto prazo.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Próximos passos possíveis")
    st.write(
        """
        - Integrar dados reais de CDI/IPCA/BACEN.
        - Adicionar dados regionais de aluguel e preço de imóveis.
        - Criar uma camada Bronze/Silver/Gold em Databricks.
        - Adicionar análise de sensibilidade com heatmap.
        - Comparar regiões como São Carlos, Osasco, Jundiaí e Morumbi.
        """
    )
