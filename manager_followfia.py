from flask import Flask, request, jsonify, render_template
import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import norm
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import requests

from app.mt5_connect import *
from manager import *

mt5_path = Path('C:/', 'Program Files', 'MetaTrader 5', 'terminal64.exe')
initialize(user_path=str(mt5_path), server='XPMT5-DEMO', login=52276888, key='Cg21092013PM#')

app = Flask(__name__)

pl_fundo = 1_450_000.00

def get_real_time_prices(portfolio):
    prices_full = {}
    prices = {}
    for ticker in portfolio.keys():
        if portfolio[ticker]['quantity'] > 0:
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

def calculate_pnl(portfolio, prices):
    pnl = {}
    for ticker, data in portfolio.items():
        if data['quantity'] > 0:
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
                'percentage_change': (profit_loss / initial_value)
            }
    return pnl

def send_data_to_heroku(portfolio_data):
    url = 'https://seu-app-no-heroku.herokuapp.com/update_data'
    response = requests.post(url, json=portfolio_data)
    if response.status_code == 200:
        print("Data updated successfully on Heroku")
    else:
        print("Failed to update data on Heroku:", response.text)

def main():
    portfolio, df = run_manager_xml()
    last_prices, prices_full = get_real_time_prices(portfolio)
    pnl = calculate_pnl(portfolio, last_prices)
 
    portfolio_data = {
        "pnl": pnl,
        "prices_full": prices_full
    }
    
    send_data_to_heroku(portfolio_data)

if __name__ == '__main__':
    main()
