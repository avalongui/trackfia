import os
import base64
import logging
import requests
import numpy as np
import pandas as pd
from io import BytesIO
from datetime import datetime
import matplotlib.pyplot as plt
from flask import Flask, render_template, redirect, url_for, request, jsonify, flash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# Inicializa o Flask
app = Flask(__name__)

# Configurações de Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=['200 per day', '50 per hour']
)

# Configurações do Flask
app.config['SECRET_KEY'] = 'Avalon@123'

# Inicializa o LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configuração de Log
logging.basicConfig(level=logging.DEBUG)

# Usuários e Data Store
users = {'admin': {'password': 'Avalon@123'}}
data_store = None

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('5 per minute')
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/upload_operations', methods=['POST'])
@login_required
def upload_operations():
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('index'))

    if file and file.filename.endswith('.xlsx'):
        files = {'file': (file.filename, file.stream, file.content_type)}
        response = requests.post('http://localhost:5000/process_file_local', files=files)
        
        if response.status_code == 200:
            global data_store
            data_store = response.json()
            flash('File processed successfully', 'success')
        else:
            flash('Failed to process file on the local machine', 'error')
    
    return redirect(url_for('index'))

@app.route('/update_data', methods=['POST'])
def update_data():
    global data_store
    data = request.get_json()
    if data is None:
        return jsonify({"status": "error", "message": "No JSON data received"}), 400
    
    data_store = data
    return jsonify({"status": "success", "message": "Data updated successfully"}), 200

def create_combined_bar_chart(df, columns, title):
    df = df.sort_values(by=columns[1], ascending=False)
    fig, ax = plt.subplots(figsize=(16, 8))
    
    bar_width = 0.25
    index = np.arange(len(df))
    
    bars1 = ax.bar(index - bar_width / 2, df[columns[0]], bar_width, label='retorno (%)', color='#1f77b4')
    bars2 = ax.bar(index + bar_width / 2, df[columns[1]], bar_width, label='pesos (%)', color='#D3D3D3')
    
    ax.set_title(title, fontsize=16)
    ax.set_xticks(index)
    ax.set_xticklabels(df.index, rotation=45, ha='right')
    
    ax.legend()

    for bar in bars1:
        yval = bar.get_height()
        label_position = yval + 0.1 if yval >= 0 else yval - 0.1
        ax.text(bar.get_x() + bar.get_width() / 2, label_position, f'{yval:.2f}', ha='center', va='bottom' if yval >= 0 else 'top', fontsize=9)

    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight')
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    
    return f"data:image/png;base64,{data}"

def create_histReturns_bar_chart(df, title):
    df = df.sort_values(by='Retorno Diário (%)', ascending=True)
    fig, ax = plt.subplots(figsize=(16, 12))
    
    bar_width = 0.7
    index = np.arange(len(df)) * 2.6
    
    colors = ['#00416A', '#6495ED', '#000000']
    
    bars1 = ax.barh(index - bar_width, df['Retorno Diário (%)'], bar_width, label='Retorno Diário (%)', color=colors[0], alpha=0.8)
    bars2 = ax.barh(index, df['Retorno Semanal (%)'], bar_width, label='Retorno Semanal (%)', color=colors[1], alpha=0.8)
    bars3 = ax.barh(index + bar_width, df['Retorno Mensal (%)'], bar_width, label='Retorno Mensal (%)', color=colors[2], alpha=0.8)
    
    ax.set_title(title, fontsize=16)
    ax.set_yticks(index)
    ax.set_yticklabels(df.index, fontsize=12)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=12)

    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            width = bar.get_width()
            if width > 0:
                ax.text(width, bar.get_y() + bar.get_height()/2, f'{width:.2f}', ha='left', va='center', fontsize=8)
            else:
                ax.text(width, bar.get_y() + bar.get_height()/2, f'{width:.2f}', ha='right', va='center', fontsize=8)

    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight')
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    
    return f"data:image/png;base64,{data}"

def create_options_impact_chart(impact_by_date, title):
    fig, ax = plt.subplots(figsize=(12, 8))
    current_date = datetime.now()
    dates = [(date - current_date).days for date in impact_by_date.keys()]
    values = list(impact_by_date.values())
    bars = ax.bar(dates, values, color='black', alpha=0.7)

    ax.set_xlabel('Dias Restantes até o Vencimento')
    ax.set_ylabel('Impacto Financeiro (R$)')
    ax.set_title(title)
    
    for bar, value in zip(bars, values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height, f'{value:.0f}', ha='center', va='bottom', fontsize=10, color='black')

    ax.set_xticks(dates)
    ax.set_xticklabels([f'{date} dias' for date in dates])

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight')
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    
    return f"data:image/png;base64,{data}"

@app.route('/')
@login_required
def index():
    global data_store
    if data_store is None:
        return jsonify({"status": "error", "message": "No data available. Please update the data."}), 200
    
    time_web = data_store['current_time']
    data_dados = pd.to_datetime(data_store['data']).strftime('%d/%m/%Y')
    pl_fundo = data_store['current_pl']
    cota_fia = data_store['cota']
    a_receber = data_store['receber']
    a_pagar = data_store['pagar']
    enquadramento = data_store['enquadramento']
    limits_der = data_store['limits_der']
    portfolio_change = data_store['portfolio_change']
    portfolio_change_stocks = data_store['portfolio_change_stocks']
    portfolio_daily_change = data_store['portfolio_daily_change']
    portfolio_weekly_change = data_store['portfolio_weekly_change']
    portfolio_var_1_week = data_store['portfolio_var_1_week']
    portfolio_var_1_month = data_store['portfolio_var_1_month']
  
    additional_info = pd.DataFrame({
        'Informação': ['Referência API', 'PL', 'Cota', 'A receber', 'A pagar', 'Enquadramento', 'Limites (Derivativos)',
                       'Variação Portfólio RV (PM)', 'Variação Portfólio Ações (PM)',
                       'Variação Diária do Portfólio RV', 
                       'Variação Semanal do Portfólio RV', 'VaR 1 semana (95%)', 'VaR 1 mês (95%)'],
        
    'Valor': [f'{data_dados}', f'R$ {pl_fundo:,.2f}', f'{cota_fia}', f'R$ {a_receber:,.2f}', f'R$ {a_pagar:,.2f}', 
              f'{enquadramento:.2%}', f'{limits_der:.2%}',  f'{portfolio_change:.2%}', f'{portfolio_change_stocks:.2%}', 
              f'{portfolio_daily_change:.2f}%', f'{portfolio_weekly_change:.2f}%', f'{portfolio_var_1_week[1]:.2f}%', 
              f'{portfolio_var_1_month[1]:.2f}%']
    })
    
    df_stocks = pd.DataFrame.from_dict(data_store['df_stocks_dict'])
    df_stocks.set_index('index', inplace=True)
    
    change_df = pd.DataFrame.from_dict(data_store['change_df_dict'])
    change_df.set_index('index', inplace=True)
    
    impact_by_date = {pd.to_datetime(k): v for k, v in data_store['impact_by_date'].items()}
    
    df_chart_usage = pd.DataFrame.from_dict(data_store['df_chart_usage'])
    df_opts_table = pd.DataFrame.from_dict(data_store['df_opts_table'])
   
    chart1 = create_combined_bar_chart(df_stocks, ['percentage_change', 'pcts_port'], "Variação da Carteira por Preço Médio x Peso do Ativo na Carteira")
    chart3 = create_histReturns_bar_chart(change_df, "Variação Percentual dos Ativos")
    chart4 = create_options_impact_chart(impact_by_date, 'Impacto Financeiro das Opções nas Datas de Vencimento')
    
    return render_template('index.html', chart1=chart1, chart3=chart3, chart4=chart4, 
                       table=df_chart_usage.to_html(classes='table table-striped table-bordered', border=0), 
                       options_table=df_opts_table.to_html(classes='table table-striped table-bordered', border=0),
                       additional_table=additional_info.to_html(classes='table table-striped table-bordered', index=False, header=True), 
                       current_time=time_web)

@app.route('/manual_operations', methods=['GET', 'POST'])
@login_required
def manual_operations():
    global data_store
    if request.method == 'POST':
        manual_insert = None

        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            if file and file.filename.endswith('.xlsx'):
                df_manual_operations = pd.read_excel(file)

                df_manual_operations = df_manual_operations[df_manual_operations.Status == 'Executada']
                data_manual = []
                for index in df_manual_operations.index:
                    row = df_manual_operations.loc[index]

                    pos = row.Lado
                    nome_cia = 'manual'
                    quantidade = row['Qtd Executada']
                    preco = row['Preço']
                    financeiro = quantidade * preco
                    ticker = row.Ativo
                    data = pd.to_datetime(row['Data Validade'])

                    data_manual.append({
                        'pos': pos,
                        'nome_cia': nome_cia,
                        'quantidade': quantidade,
                        'preco': preco,
                        'financeiro': financeiro,
                        'ticker': ticker,
                        'data': data,
                        'P&L': 0.0,
                        'average_price': 0.0
                    })

                manual_insert = pd.DataFrame.from_dict(data_manual)
                manual_insert['data'] = manual_insert['data'].astype(str)

        ngrok_url = "https://trackfia.ngrok.app"
        logging.debug(f"Enviando solicitação para {ngrok_url}")

        try:
            response = requests.post(f'{ngrok_url}/process_manual_operations', json=manual_insert.to_dict(orient='records') if manual_insert is not None else {})
            logging.debug(f"Resposta recebida: {response.status_code} - {response.text}")
            if response.status_code == 200:
                data_store = response.json()
                flash('File processed successfully', 'success')
                
                time_web = data_store['current_time']
                data_dados = pd.to_datetime(data_store['data']).strftime('%d/%m/%Y')
                pl_fundo = data_store['current_pl']
                cota_fia = data_store['cota']
                a_receber = data_store['receber']
                a_pagar = data_store['pagar']
                enquadramento = data_store['enquadramento']
                limits_der = data_store['limits_der']
                portfolio_change = data_store['portfolio_change']
                portfolio_change_stocks = data_store['portfolio_change_stocks']
                portfolio_daily_change = data_store['portfolio_daily_change']
                portfolio_weekly_change = data_store['portfolio_weekly_change']
                portfolio_var_1_week = data_store['portfolio_var_1_week']
                portfolio_var_1_month = data_store['portfolio_var_1_month']
              
                additional_info = pd.DataFrame({
                    'Informação': ['Referência API', 'PL', 'Cota', 'A receber', 'A pagar', 'Enquadramento', 'Limites (Derivativos)',
                                   'Variação Portfólio RV (PM)', 'Variação Portfólio Ações (PM)',
                                   'Variação Diária do Portfólio RV', 
                                   'Variação Semanal do Portfólio RV', 'VaR 1 semana (95%)', 'VaR 1 mês (95%)'],
                    
                'Valor': [f'{data_dados}', f'R$ {pl_fundo:,.2f}', f'{cota_fia}', f'R$ {a_receber:,.2f}', f'R$ {a_pagar:,.2f}', 
                          f'{enquadramento:.2%}', f'{limits_der:.2%}',  f'{portfolio_change:.2%}', f'{portfolio_change_stocks:.2%}', 
                          f'{portfolio_daily_change:.2f}%', f'{portfolio_weekly_change:.2f}%', f'{portfolio_var_1_week[1]:.2f}%', 
                          f'{portfolio_var_1_month[1]:.2f}%']
                })

                df_stocks = pd.DataFrame.from_dict(data_store['df_stocks_dict'])
                df_stocks.set_index('index', inplace=True)

                change_df = pd.DataFrame.from_dict(data_store['change_df_dict'])
                change_df.set_index('index', inplace=True)

                impact_by_date = {pd.to_datetime(k): v for k, v in data_store['impact_by_date'].items()}

                df_chart_usage = pd.DataFrame.from_dict(data_store['df_chart_usage'])
                df_opts_table = pd.DataFrame.from_dict(data_store['df_opts_table'])

                chart1 = create_combined_bar_chart(df_stocks, ['percentage_change', 'pcts_port'], "Variação da Carteira por Preço Médio x Peso do Ativo na Carteira")
                chart3 = create_histReturns_bar_chart(change_df, "Variação Percentual dos Ativos")
                chart4 = create_options_impact_chart(impact_by_date, 'Impacto Financeiro das Opções nas Datas de Vencimento')

                return render_template('manual_operations.html',
                                       chart1=chart1, chart3=chart3, chart4=chart4,
                                       table=df_chart_usage.to_html(classes='table table-striped table-bordered', border=0),
                                       options_table=df_opts_table.to_html(classes='table table-striped table-bordered', border=0),
                                       additional_table=additional_info.to_html(classes='table table-striped table-bordered', index=False, header=True),
                                       current_time=time_web)
            else:
                logging.error(f"Erro na resposta: {response.status_code} - {response.text}")
                return jsonify({"status": "error", "message": "Erro ao processar operações"}), response.status_code
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro ao enviar solicitação: {e}")
            return jsonify({"status": "error", "message": "Erro de comunicação com o servidor local"}), 500

    return render_template('manual_operations.html')



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
