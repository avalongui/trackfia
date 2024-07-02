from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt
from io import BytesIO
import base64

app = Flask(__name__)

data_store = None
pl_fundo = 1_450_000.00


def create_bar_chart(df, column, title):
    df = df.sort_values(by=column, ascending=False)
    fig, ax = plt.subplots(figsize=(14, 5))
    colors = ['#00008B' if x > 0 else '#FF4500' for x in df[column]]
    
    bars = ax.bar(df.index, df[column], color=colors, width=0.8)
    
    ax.set_title(title)
    ax.tick_params(axis='x', rotation=45)
    
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval, f'{yval:.2f}%', ha='center', va='bottom', fontsize=7)

    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight')
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    
    return f"data:image/png;base64,{data}"

def calculate_var(prices, weights, time_ahead):
    returns = np.log(1 + prices.pct_change())
    historical_returns = (returns * weights).sum(axis=1)
    cov_matrix = returns.cov() * 252
    portfolio_std_dev = np.sqrt(weights.T @ cov_matrix @ weights)
    
    confidence_levels = [0.90, 0.95, 0.99]
    VaRs = []
    for cl in confidence_levels:
        VaR = portfolio_std_dev * norm.ppf(cl) * np.sqrt(time_ahead / 252)
        VaRs.append(round(VaR * 100, 4))
    
    return VaRs

def calculate_daily_change(prices_df):
    today = prices_df.iloc[-1]
    yesterday = prices_df.iloc[-2]
    change = ((today - yesterday) / yesterday) * 100
    return change

def calculate_portfolio_change(df):
    initial_value = (df['average_price'] * df['quantity']).sum()
    current_value = df['current_value'].sum()
    portfolio_change = (current_value / initial_value) - 1
    return portfolio_change

@app.route('/update_data', methods=['POST'])
def update_data():
    global data_store
    data = request.get_json()
    data_store = data
    return jsonify({"status": "success", "message": "Data updated successfully"}), 200

@app.route('/')
def index():
    global data_store
    if data_store is None:
        return "No data available. Please update the data.", 200

    pnl = pd.DataFrame(data_store["pnl"])
    prices = data_store["prices_full"]


    df = pd.DataFrame.from_dict(pnl, orient='index')
    df['pcts_port'] = (df['current_value'] / np.sum(df['current_value'])) * 100
    df['percentage_change'] = df['percentage_change'] * 100
    df['impact'] = df['percentage_change'] * df['pcts_port'] / 100
    
    
    chart1 = create_bar_chart(df, 'percentage_change', "Variação da Carteira por Preço Médio")
    chart2 = create_bar_chart(df, 'impact', "Impacto da Variação na Carteira")

    weights = df['pcts_port'].values / 100
    
    df_var = pd.DataFrame({k: v['Fechamento'] for k,v in prices.items()}, columns=prices.keys())
    portfolio_var_1_week = calculate_var(df_var, weights, 5)
    portfolio_var_1_month = calculate_var(df_var, weights, 21)
    
    VaR_1_week = []
    VaR_1_month = []
    tickers = list(df.index)
    for ticker in tickers:
        individual_returns = np.log(1 + df_var[ticker].pct_change())
        individual_std_dev = individual_returns.std() * np.sqrt(252)
        var_1_week = individual_std_dev * norm.ppf(0.95) * np.sqrt(5 / 252)
        var_1_month = individual_std_dev * norm.ppf(0.95) * np.sqrt(21 / 252)
        VaR_1_week.append(var_1_week * 100)  # Convertendo para porcentagem
        VaR_1_month.append(var_1_month * 100)
 
    df['VaR 1 semana'] = VaR_1_week
    df['VaR 1 mês'] = VaR_1_month
    
    daily_change = calculate_daily_change(df_var)
    chart3 = create_bar_chart(daily_change.to_frame(name='daily_change'), 'daily_change', "Variação Percentual dos Ativos Hoje")

    portfolio_change = calculate_portfolio_change(df)

    # Atualizacao final para apresentacao do quadro
    df = df.sort_values(by='pcts_port', ascending=False)
    df.columns = ['Preço', 'Quantidade', 'PM', 'Financeiro', 'PnL', 'Variação', 'Peso', 'Variação ponderada',
                  'VaR semanal', 'VaR mensal']
    df = df.apply(lambda x: round(x,2))
    
    enquadramento = df['Financeiro'].sum() / pl_fundo
