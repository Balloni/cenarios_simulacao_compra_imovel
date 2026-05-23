# Comprar ou alugar? Simulador de decisão imobiliária

Projeto pessoal em Streamlit para comparar cenários de compra/financiamento versus aluguel, considerando:

- entrada;
- FGTS;
- taxa de financiamento;
- rendimento líquido dos investimentos;
- valorização do imóvel;
- correção do aluguel;
- custos de compra;
- manutenção/IPTU/condomínio extra;
- horizonte de análise.

## Objetivo

Transformar uma decisão cotidiana sobre moradia na Grande São Paulo em um exercício de analytics, modelagem financeira e visualização interativa.

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Como publicar no Streamlit Community Cloud

1. Crie um repositório público no GitHub.
2. Envie estes arquivos para o repositório:
   - `app.py`
   - `requirements.txt`
   - `README.md`
3. Acesse o Streamlit Community Cloud.
4. Clique em **Create app** ou **New app**.
5. Selecione:
   - repositório;
   - branch;
   - arquivo principal: `app.py`.
6. Clique em **Deploy**.

## Próximas melhorias

- Integrar dados reais de CDI/IPCA/BACEN.
- Adicionar dados regionais de aluguel e preço de imóveis.
- Criar pipeline em Databricks com arquitetura Bronze/Silver/Gold.
- Adicionar análise de sensibilidade com heatmap.
- Comparar regiões como São Carlos, Osasco, Jundiaí e Morumbi.

## Aviso

Simulação educacional. Não é recomendação financeira.
