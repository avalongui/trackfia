import os
from flask import Flask, render_template, redirect, url_for, request, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import pandas as pd
import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from datetime import datetime, timedelta

app = Flask(__name__)
data_store = None

app.config['SECRET_KEY'] = 'Avalon@123'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id):
        self.id = id

users = {'admin': {'password': 'Avalon@123'}}

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route('/login', methods=['GET', 'POST'])
def login():
    print("Login page accessed")
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"Attempting login with username: {username} and password: {password}")
        if username in users and users[username]['password'] == password:
            user = User(username)
            login_user(user)
            print("Login successful")
            return redirect(url_for('index'))
        else:
            print("Login failed")
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


def create_combined_bar_chart(df, columns, title):
    df = df.sort_values(by=columns[1], ascending=False)
    fig, ax = plt.subplots(figsize=(16, 8))  # Aumentar o tamanho da figura
    
    bar_width = 0.25  # Reduzir a largura das barras para aumentar o espaçamento
    index = np.arange(len(df))
    
    bars1 = ax.bar(index - bar_width/2, df[columns[0]], bar_width, label='retorno (%)', color='#1f77b4')
    bars2 = ax.bar(index + bar_width/2, df[columns[1]], bar_width, label='pesos (%)', color='#D3D3D3')
    
    ax.set_title(title, fontsize=16)
    ax.set_xticks(index)
    ax.set_xticklabels(df.index, rotation=45, ha='right')
    
    ax.legend()

    for bar in bars1:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval, f'{yval:.2f}', ha='center', va='bottom', fontsize=9)

    for bar in bars2:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval, f'{yval:.2f}', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight')
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    
    return f"data:image/png;base64,{data}"


# def create_combined_bar_chart(df, columns, title):
#     df = df.sort_values(by=columns[0], ascending=False)
#     fig, ax = plt.subplots(figsize=(14, 7))
    
#     bar_width = 0.35
#     index = np.arange(len(df))
    
#     bars1 = ax.bar(index - bar_width/2, df[columns[0]], bar_width, label='retorno (%)', color='#1f77b4')
#     bars2 = ax.bar(index + bar_width/2, df[columns[1]], bar_width, label='pesos (%)', color='#D3D3D3')
    
#     ax.set_title(title)
#     ax.set_xticks(index)
#     ax.set_xticklabels(df.index, rotation=45, ha='right')
    
#     ax.legend()

#     for bar in bars1:
#         yval = bar.get_height()
#         ax.text(bar.get_x() + bar.get_width()/2, yval, f'{yval:.2f}', ha='center', va='bottom', fontsize=7)

#     for bar in bars2:
#         yval = bar.get_height()
#         ax.text(bar.get_x() + bar.get_width()/2, yval, f'{yval:.2f}', ha='center', va='bottom', fontsize=7)

#     plt.tight_layout()
    
#     buf = BytesIO()
#     plt.savefig(buf, format="png", bbox_inches='tight')
#     data = base64.b64encode(buf.getbuffer()).decode("ascii")
    
#     return f"data:image/png;base64,{data}"


def create_bar_chart(df, column, title):
    df = df.sort_values(by=column, ascending=False)
    fig, ax = plt.subplots(figsize=(16, 8))  # Aumentar o tamanho da figura
    colors = ['#1f77b4' if x > 0 else '#FF4500' for x in df[column]]
    
    bars = ax.bar(df.index, df[column], color=colors, width=0.8)
    
    ax.set_title(title, fontsize=16)
    ax.tick_params(axis='x', rotation=45)
    
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval, f'{yval:.2f}', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    
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


def calculate_portfolio_change_pm(df):
    initial_value = (df['average_price'] * df['quantity']).sum()
    current_value = df['current_value'].sum()
    portfolio_change = (current_value / initial_value) - 1
    return portfolio_change 


def dict_to_dataframe(data_dict):
    return pd.DataFrame.from_dict(data_dict)


def dict_to_dataframe_ts(data_dict):
    data_dict['Data'] = [pd.to_datetime(i) for i in data_dict['Data']]
    df = pd.DataFrame.from_dict(data_dict)
    df.set_index('Data', inplace=True)
   
    return df


def get_last_monday(prices_df):
    today = datetime.now().date()
    last_monday = pd.to_datetime(today - timedelta(days=today.weekday()))
    
    if last_monday not in prices_df.index:
        last_monday = prices_df.index[prices_df.index <= last_monday][-1]
    
    return last_monday


def calculate_weekly_change(prices_df, weights):
    last_monday = get_last_monday(prices_df)
    prices_last_monday = prices_df.loc[last_monday]
    prices_today = prices_df.iloc[-1]
    weekly_returns = np.log(prices_today / prices_last_monday)
    portfolio_weekly_change = (weekly_returns * weights).sum() * 100  
    return portfolio_weekly_change


def calculate_portfolio_change(prices_df, weights, days):
    returns = np.log(prices_df / prices_df.shift(1)).dropna()
    weighted_returns = returns * weights
    portfolio_change = weighted_returns.sum(axis=1).iloc[-days:].sum() * 100  
    return portfolio_change


# @app.route('/update_data', methods=['POST'])
# def update_data():
#     global data_store
#     data = request.get_json()
#     data_store = data
#     return jsonify({"status": "success", "message": "Data updated successfully"}), 200


@app.route('/update_data', methods=['POST'])
def update_data():
    global data_store
    data = request.get_json()
    if data is None:
        return jsonify({"status": "error", "message": "No JSON data received"}), 400
    
    data_store = data
    # current_time = data.get('current_time')
    return jsonify({"status": "success", "message": "Data updated successfully"}), 200


@app.route('/')
@login_required
def index():
    global data_store, current_time
    if data_store is None:
        return jsonify({"status": "error", "message": "No data available. Please update the data."}), 200

    # print("Current data_store:")
    # print(data_store)
    
    pl_fundo = data_store['current_pl']
    
    current_time = data_store['current_time'] # hora em que dados foram enviados ao sistema

    prices = data_store["prices_full"]
    prices = {asset: dict_to_dataframe_ts(data_dict) for asset, data_dict in prices.items()}

    df = pd.DataFrame.from_dict(data_store["pnl"], orient='index')
    df['pcts_port'] = (df['current_value'] / np.sum(df['current_value'])) * 100
    df['percentage_change'] = df['percentage_change'] * 100
    df['impact'] = df['percentage_change'] * df['pcts_port'] / 100
    
    weights = df['pcts_port'].values / 100
    
    chart1 = create_combined_bar_chart(df, ['percentage_change', 'pcts_port'], "Variação da Carteira por Preço Médio x Peso do Ativo na Carteira")
    # chart1 = create_bar_chart(df, 'percentage_change', "Variação da Carteira por Preço Médio")
    chart2 = create_bar_chart(df, 'impact', "Impacto da Variação na Carteira")

    df_var = pd.DataFrame({k: v['Fechamento'] for k,v in prices.items()}, columns=prices.keys())
    # dates = prices[list(prices.keys())[0]]['Data']
    df_var.index = pd.to_datetime(df_var.index)
    
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
    
    enquadramento = df['current_value'].sum()  / pl_fundo
    data_dados = pd.to_datetime(data_store['data']).strftime('%d/%m/%Y')
    cota_fia = data_store['cota']
    a_receber = data_store['receber']
    a_pagar = data_store['pagar']
    
    daily_change = calculate_daily_change(df_var) # variacao diaria de cada ativo
    chart3 = create_bar_chart(daily_change.to_frame(name='daily_change'), 'daily_change', "Variação Percentual dos Ativos Hoje")

    portfolio_change = calculate_portfolio_change_pm(df) # variacao com PM dos ativos
    portfolio_daily_change = calculate_portfolio_change(df_var, weights, 1)
    portfolio_weekly_change = calculate_weekly_change(df_var, weights)

    # Atualizacao final para apresentacao do quadro
    df = df.sort_values(by='profit_loss', ascending=False)
    df.columns = ['Preço', 'Quantidade', 'PM', 'Financeiro', 'PnL', 'Variação', 'Peso', 'Variação ponderada',
                  'VaR semanal', 'VaR mensal']
    df = df.apply(lambda x: round(x,2))
    
    posicao_acoes = df['Financeiro'].sum()
    enquadramento = df['Financeiro'].sum() / data_store['current_pl']

    # Tabela de informações adicionais
    additional_info = pd.DataFrame({
        'Informação': ['Referência API', 'PL', 'Posição Ações', 'Cota', 'A receber', 'A pagar', 'Enquadramento', 'Variação da Carteira desde Última Alocação', 'Variação Diária do Portfólio', 
                       'Variação Semanal do Portfólio', 'VaR 1 semana (95%)', 'VaR 1 mês (95%)'],
        
    'Valor': [f'{data_dados}', f'R$ {pl_fundo:,.2f}', f'R$ {posicao_acoes:,.2f}', f'{cota_fia}', f'R$ {a_receber:,.2f}', f'R$ {a_pagar:,.2f}', f'{enquadramento:.2%}', f'{portfolio_change:.2%}', f'{portfolio_daily_change:.2f}%', f'{portfolio_weekly_change:.2f}%', 
                  f'{portfolio_var_1_week[1]:.2f}%', f'{portfolio_var_1_month[1]:.2f}%']
    })
    
    
    return render_template('index.html', chart1=chart1, chart2=chart2, chart3=chart3, table=df.to_html(classes='table table-striped table-bordered', border=0), additional_table=additional_info.to_html(classes='table table-striped table-bordered', index=False, header=True), current_time=current_time)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
