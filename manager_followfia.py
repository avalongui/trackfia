import os
import schedule
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import norm
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import requests
import json
import pickle
from flask import Flask, render_template, redirect, url_for, request, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

from api_btg import fund_data
from mt5_connect import *
from manager import *
from options_data import id_options

# mt5_path = Path('C:/', 'Program Files', 'MetaTrader 5', 'terminal64.exe')
# initialize(user_path=str(mt5_path), server='XPMT5-DEMO', login=52276888, key='Cg21092013PM#')

mt5_path = Path('C:/', 'Program Files', 'Rico - MetaTrader 5', 'terminal64.exe')
initialize(user_path=str(mt5_path), server='GenialInvestimentos-PRD', login=156691, key='Avca@1985')

app = Flask(__name__)



def get_real_time_prices(portfolio):
    prices_full = {}
    prices = {}
    for ticker in portfolio.keys():

        if portfolio[ticker]['quantity'] > 0 or (portfolio[ticker]['quantity'] < 0 and portfolio[ticker]['short_sellig'] == 1):
            prepare_symbol(ticker)
            df_ = get_prices_mt5(symbol=ticker, n=100, timeframe=mt5.TIMEFRAME_D1)
            df_['Volume_Financeiro'] = ((df_['Máxima'] + df_['Mínima']) / 2) * df_['Volume']
            df_ = df_[['Abertura', 'Máxima', 'Mínima', 'Fechamento', 'Volume_Financeiro']]
            df_.columns = ['Abertura', 'Maxima', 'Minima', 'Fechamento', 'Volume_Financeiro']
            df_.index.name = 'Data'
            prices_full[ticker] = df_
            last_price = df_.iloc[-1]['Fechamento']
            prices[ticker] = last_price
    return prices, prices_full


def get_real_time_prices_options_stocks(df_):
    """
    Pegar precos do ativo subjacente para dada opcao
    """
    prices = {}
    for ticker in list(df_.stock):
        prepare_symbol(ticker)
        df_ = get_prices_mt5(symbol=ticker, n=100, timeframe=mt5.TIMEFRAME_D1)
        df_['Volume_Financeiro'] = ((df_['Máxima'] + df_['Mínima']) / 2) * df_['Volume']
        df_ = df_[['Abertura', 'Máxima', 'Mínima', 'Fechamento', 'Volume_Financeiro']]
        df_.columns = ['Abertura', 'Maxima', 'Minima', 'Fechamento', 'Volume_Financeiro']
        df_.index.name = 'Data'
        last_price = df_.iloc[-1]['Fechamento']
        prices[ticker] = last_price
    return prices


def calculate_pnl(portfolio, prices):
    pnl = {}
    for ticker, data in portfolio.items():

        if data['quantity'] > 0 or (portfolio[ticker]['quantity'] < 0 and portfolio[ticker]['short_sellig'] == 1):
            current_price = prices.get(ticker, 0)
            average_price = data['average_price']
            current_value = current_price * data['quantity']
            initial_value = average_price * data['quantity']
            profit_loss = current_value - initial_value
            pnl[ticker] = {
                'current_price': current_price,
                'quantity': data['quantity'],
                'average_price': average_price,
                'current_value': current_value,
                'profit_loss': profit_loss,
                'percentage_change': (profit_loss / abs(initial_value))
            }
    return pnl


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


def calculate_weeklyAssets_change(prices_df):
    last_monday = get_last_monday(prices_df)
    prices_last_monday = prices_df.loc[last_monday]
    prices_today = prices_df.iloc[-1]
    weekly_returns = np.log(prices_today / prices_last_monday) * 100
    return weekly_returns


def get_first_day_of_month(prices_df):
    today = datetime.now().date()
    first_day_of_month = pd.to_datetime(today.replace(day=1))
    
    if first_day_of_month not in prices_df.index:
        first_day_of_month = prices_df.index[prices_df.index <= first_day_of_month][-1]
    return first_day_of_month


def calculate_monthlyAssets_change(prices_df):
    first_day_of_month = get_first_day_of_month(prices_df)
    prices_first_day = prices_df.loc[first_day_of_month]
    prices_today = prices_df.iloc[-1]
    monthly_returns = np.log(prices_today / prices_first_day) * 100
    return monthly_returns


def calculate_portfolio_change(prices_df, weights, days):
    returns = np.log(prices_df / prices_df.shift(1))# .dropna()
    weighted_returns = returns * weights
    portfolio_change = weighted_returns.sum(axis=1).iloc[-days:].sum() * 100  
    return portfolio_change


def send_data_to_heroku(portfolio_data):
    url = 'https://trackfia-3ae72ebff575.herokuapp.com/update_data'
    response = requests.post(url, json=portfolio_data)
    if response.status_code == 200:
        print("Data updated successfully on Heroku")
    else:
        print("Failed to update data on Heroku:", response.text)


def dataframe_to_dict(df):
    return df.reset_index().to_dict(orient='records')


def dataframe_to_dict_ts(df):
    # Convert all datetime-like columns to strings
    df = df.copy()
    df.reset_index(inplace=True)
    for column in df.columns:
        if np.issubdtype(df[column].dtype, np.datetime64):
            df[column] = df[column].astype(str)
    return df.to_dict(orient='list')


def convert_timestamps_to_strings(data_dict):
    return {str(k): v for k, v in data_dict.items()}


def save_pickle(data, path):
    with open(path, 'wb') as file:
        pickle.dump(data, file)


def load_pickle(path):
    with open(path, 'rb') as file:
        return pickle.load(file)


def handle_data_Mainwebpage(manual_insert=[]):
    
    # Datas
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Captura de dados da API
    # Caminho para os arquivos pickle
    pickle_dir = Path(Path.home(), 'Documents', 'GitHub', 'database', 'dados_api')
    df_xml_path = os.path.join(pickle_dir, f'df_xml_{current_date}.pkl')
    data_xml_path = os.path.join(pickle_dir, f'data_xml_{current_date}.pkl')
    header_path = os.path.join(pickle_dir, f'header_{current_date}.pkl')
    
    # Verifica se os arquivos pickle do dia já existem
    if os.path.exists(df_xml_path) and os.path.exists(data_xml_path) and os.path.exists(header_path):
        df_xml = load_pickle(df_xml_path)
        data_xml = load_pickle(data_xml_path)
        header = load_pickle(header_path)
        print('Dados carregados dos arquivos serializados.')
    
    else:
        df_xml, data_xml, header = fund_data(find_type='xml')
        save_pickle(df_xml, df_xml_path)
        save_pickle(data_xml, data_xml_path)
        save_pickle(header, header_path)
        print('Dados capturados da API e salvos em arquivos serializados.')
            
    data_api = header['dtposicao']
    print(f'Data dos dados capturados da API: {data_api}')
    
    pl_fundo = header['patliq']
    data_dados = pd.to_datetime(header['dtposicao']).strftime('%d/%m/%Y')
    cota_fia = header['valorcota']
    a_receber = header['valorreceber']
    a_pagar = header['valorpagar']
    
    # Puxar dados locais
    portfolio, df_original_table = run_manager_xml() # manager
    
    # Alterar dados de entrada para inclusao de operacoes manuais
    if len(manual_insert) > 0:
        df_original_table = pd.concat([df_original_table, manual_insert], axis=0)
        portfolio, df_original_table = calculate_PnL_averagePrices(df_original_table) # manager function
    
    counter = 0
    last_prices = []
    while len(last_prices) == 0 and counter < 5:
        last_prices, prices = get_real_time_prices(portfolio)
        pnl = calculate_pnl(portfolio, last_prices)
        counter+=1
        time.sleep(2)

    # Base calculos posicoes
    df = pd.DataFrame.from_dict(pnl, orient='index')
    df['pcts_port'] = (df['current_value'] / np.sum(df['current_value'])) * 100
    df['percentage_change'] = df['percentage_change'] * 100
    df['impact'] = df['percentage_change'] * df['pcts_port'] / 100

    # PROCESSO 1: Lidar com acoes em carteira
    df_stocks = df[df.index.str.len() < 7]
    weights = df_stocks['pcts_port'].values / 100
    
    # Variacao de precos
    df_var = pd.DataFrame({k: v['Fechamento'] for k,v in prices.items() if k in list(df_stocks.index)}, columns=[i for i in prices.keys() if i in list(df_stocks.index)])
    # dates = prices[list(prices.keys())[0]]['Data']
    df_var.index = pd.to_datetime(df_var.index)
    
    portfolio_var_1_week = calculate_var(df_var, weights, 5)
    portfolio_var_1_month = calculate_var(df_var, weights, 21)
    
    VaR_1_week = []
    VaR_1_month = []
    tickers = list(df_stocks.index)
    for ticker in tickers:
        individual_returns = np.log(1 + df_var[ticker].pct_change())
        individual_std_dev = individual_returns.std() * np.sqrt(252)
        var_1_week = individual_std_dev * norm.ppf(0.95) * np.sqrt(5 / 252)
        var_1_month = individual_std_dev * norm.ppf(0.95) * np.sqrt(21 / 252)
        VaR_1_week.append(var_1_week * 100)  # Convertendo para porcentagem
        VaR_1_month.append(var_1_month * 100)
 
    df_stocks['VaR 1 semana'] = VaR_1_week
    df_stocks['VaR 1 mês'] = VaR_1_month
    
    # Variacao dos ativos
    daily_change = calculate_daily_change(df_var)  # Variacao diaria de cada ativo
    weekly_change = calculate_weeklyAssets_change(df_var)  # Variacao semanal de cada ativo
    monthly_change = calculate_monthlyAssets_change(df_var)  # Variacao mensal de cada ativo
    
    # Combinar dados de variações em um DataFrame
    change_df = pd.DataFrame({
        'Retorno Diário (%)': daily_change,
        'Retorno Semanal (%)': weekly_change,
        'Retorno Mensal (%)': monthly_change
    })

    # Criar gráfico combinado
    # chart3 = create_histReturns_bar_chart(change_df, "Variação Percentual dos Ativos")
    df_var_port = pd.DataFrame({k: v['Fechamento'] for k,v in prices.items()}, columns=df.index)
    df_var_port.index = pd.to_datetime(df_var_port.index)
    weights_total = df['pcts_port'].values / 100
    
    # Variacao portfolio
    portfolio_change = calculate_portfolio_change_pm(df) # variacao com PM dos ativos
    # Variacao apenas das acoes
    portfolio_change_stocks = calculate_portfolio_change_pm(df_stocks)
    portfolio_daily_change = calculate_portfolio_change(df_var_port, weights_total, 1) # com todos os ativos
    portfolio_daily_change_stocks = calculate_portfolio_change(df_var, weights, 1) # com todos os ativos
    
    portfolio_weekly_change = calculate_weekly_change(df_var_port, weights_total)
    
    df_chart_usage = df_stocks.copy()
    df_chart_usage.columns = ['Preço', 'Quantidade', 'PM', 'Financeiro', 'PnL', 'Variação', 'Peso', 'Variação ponderada',
                  'VaR semanal', 'VaR mensal']
    df_chart_usage = df_chart_usage.apply(lambda x: round(x,2))
    
    # Enquadramento do fundo
    enquadramento = df['current_value'].sum() / pl_fundo
    
    # Base tabela opcoes
    opts_df = df[df.index.str.len() >= 7]
    
    # lidar com dados de opcoes
    opts_id = list(opts_df.index)
    opts_database = id_options(opts_id)
    opts_database_find_data = opts_database[opts_database.ticker.isin(list(opts_df.index))]
    opts_database = opts_database[['stock', 'ticker', 'tipo', 'vencimento', 'strike']]

    # Base precos opcoes
    opts_df.index.name = 'ticker'
    df_opts = pd.merge(opts_df, opts_database, on='ticker')
    prices_assets_opts = get_real_time_prices_options_stocks(df_opts)
    
    # Pendente: se o strike da acao estiver em uma proximidade de 10% do preco, consideramos que vamos exercer ou ser exercidos
    df_opts['current_price_stock'] = df_opts['stock'].map(prices_assets_opts)
    # df_opts['exercise'] = 1 # Pendente
    
    # Limites derivativos
    limits_der = np.sum(abs(df_opts['current_value'])) / pl_fundo
    
    # Valor financeiro das ações
    financial_sum = df_chart_usage['Financeiro'].sum()
    
    # Calcula o impacto financeiro para cada data de vencimento
    impact_by_date = {}
    for index, row in df_opts.iterrows():
        
        expiry_date = row['vencimento']
        tipo = row['tipo']
        quantity = row['quantity']
        strike = row['strike']
        current_price_stock = row['current_price_stock']
    
        if expiry_date not in impact_by_date:
            impact_by_date[expiry_date] = 0
    
        if tipo == 'p':  # Put
            if quantity < 0:  # Vendendo Put
                impact_by_date[expiry_date] += abs(quantity) * strike
            else:  # Comprando Put
                impact_by_date[expiry_date] -= abs(quantity) * strike
        elif tipo == 'c':  # Call
            if quantity < 0:  # Vendendo Call
                impact_by_date[expiry_date] -= abs(quantity) * strike
            else:  # Comprando Call
                impact_by_date[expiry_date] += abs(quantity) * strike
    
    # Adiciona o impacto financeiro ao valor financeiro das ações
    impact_by_date = {date: financial_sum + impact for date, impact in impact_by_date.items()}
    
    # Tabela de operações com opções
    # df_opts.set_index('Ticker', inplace=True)
    df_opts = df_opts.sort_values(by='profit_loss', ascending=False)
    df_opts.columns = ['Ticker', 'Preço Atual', 'Quantidade', 'PM', 'Valor Atual', 'PnL', 'Variação', 'Peso', 'Variação ponderada', 'Ativo Subjacente', 'Tipo', 'Vencimento', 'Strike', 'Preço Atual Ativo']
    
    numeric_cols = df_opts.select_dtypes(include=[np.number]).columns
    df_opts[numeric_cols] = df_opts[numeric_cols].round(2)
    
    df_opts_table = df_opts.copy()
    df_opts_table.set_index('Ticker', inplace=True)
    
    # Converter dados para envio
    df_dict = dataframe_to_dict_ts(df_original_table) # conversao para envio
    df_stocks_dict = dataframe_to_dict(df_stocks)
    change_df_dict = dataframe_to_dict(change_df)
    impact_by_date_str_keys = convert_timestamps_to_strings(impact_by_date)
    df_chart_usage_dict = dataframe_to_dict(df_chart_usage)
    df_opts_table['Vencimento'] = df_opts_table['Vencimento'].astype(str)
    df_opts_table_dict = dataframe_to_dict(df_opts_table)
    
    # Preparar dados para envio
    portfolio_data = {
        'current_time': current_time,
        'data': data_dados,
        'current_pl': pl_fundo,
        'cota': cota_fia,
        'receber': a_receber,
        'pagar': a_pagar,
        'enquadramento': enquadramento,
        'limits_der': limits_der,
        'portfolio_change': portfolio_change,
        'portfolio_change_stocks': portfolio_change_stocks,
        'portfolio_daily_change': portfolio_daily_change,
        'portfolio_weekly_change': portfolio_weekly_change,
        'portfolio_var_1_week': portfolio_var_1_week,
        'portfolio_var_1_month': portfolio_var_1_month,
        'df_stocks_dict': df_stocks_dict,
        'change_df_dict': change_df_dict,
        'impact_by_date': impact_by_date_str_keys,
        'df_chart_usage': df_chart_usage_dict,
        'df_opts_table': df_opts_table_dict,
        'portfolio': portfolio,
        'df': df_dict
    }
    
    return portfolio_data


def job():
    
    portfolio_data = handle_data_Mainwebpage()
    
    url = 'https://trackfia-3ae72ebff575.herokuapp.com/update_data'

    response = requests.post(url, json=portfolio_data)

    if response.status_code == 200:
        print("Data updated successfully on Heroku")
    else:
        print("Failed to update data on Heroku:", response.text)


@app.route('/process_manual_operations', methods=['POST'])
def process_manual_operations():
    
    manual_insert = request.get_json()

    if manual_insert:
        manual_insert = pd.DataFrame.from_dict(manual_insert)
    else:
        manual_insert = []

    if len(manual_insert) == 0:
        print('Houve um problema no recebimento dos dados...')
        return None
    else:
        portfolio_data = handle_data_Mainwebpage(manual_insert=manual_insert)
        return jsonify(portfolio_data)


def main():
    # Agendamento da tarefa para rodar a cada 5 minutos
    schedule.every(5).minutes.do(job)
    
    # Iniciar o Flask app em uma thread separada para poder rodar o loop while true simultaneamente
    from threading import Thread
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=5000))
    flask_thread.start()
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    main()