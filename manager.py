"""
Em algum momento proximo, o leitor_notas tera que ser transformado em um codigo de cases.
Ex.: case 1 para leitura da nota (com referencia de area e colunas), case 2 etc. Posso fazer o link especifico no comeco para cada
nota em cada data. Assim tambem acho que terei que fazer para o tratamento dos dados da nota e para encontrar a data.

Algumas coisas serao manuais agora nesse comeco, ate que eu me adapte melhor a essa leitura, inclusive integrando IA ao processo.
"""

import os
import openai
from openai import OpenAI
from pathlib import Path
from tqdm import tqdm
import pandas as pd

from leitor_notas import *
from leitor_xml import *


def calculate_PnL_averagePrices(df):
    
    portfolio = {}
    df['P&L'] = 0.0
    df['average_price'] = 0.0
    
    for index, row in df.iterrows():
        
        ticker = row['ticker']
        quantity = row['quantidade']
        price = row['preco']
        financial = quantity * price
        date = row['data']
    
        if row['pos'] == 'C':
            if ticker not in portfolio:
                portfolio[ticker] = {'quantity': 0, 'total_cost': 0}
            
            # Update quantity and total cost
            portfolio[ticker]['quantity'] += quantity
            portfolio[ticker]['total_cost'] += financial
            
            # Calculate average price
            average_price = portfolio[ticker]['total_cost'] / portfolio[ticker]['quantity']
            df.at[index, 'average_price'] = average_price
            portfolio[ticker]['average_price'] = average_price
        
        elif row['pos'] == 'V':
            
            if ticker in portfolio and portfolio[ticker]['quantity'] > 0:
                
                # Calculate average price and P&L for the sale
                average_price = portfolio[ticker]['total_cost'] / portfolio[ticker]['quantity']
                pnl = (financial - (average_price * quantity))
                df.at[index, 'P&L'] = pnl
                
                # Update quantity and total cost
                portfolio[ticker]['quantity'] -= quantity
                portfolio[ticker]['total_cost'] -= average_price * quantity
                
                # If completely sold, update the average price to P&L
                if portfolio[ticker]['quantity'] == 0:
                    df.at[index, 'average_price'] = 0
                else:
                    df.at[index, 'average_price'] = average_price

    return portfolio, df


def run_manager_xml():
    
    df_firstpos = first_pos_fia()
    df_ops = run_xmls()

    df = pd.concat([df_firstpos, df_ops])
    df['ticker'] = df['ticker'].str.strip()
    df.reset_index(inplace=True, drop=True)
    
    portfolio, df = calculate_PnL_averagePrices(df)
    
    return portfolio, df


def run_manager_brokerage_notes():
    
    df_firstpos = first_pos_fia()
    
    file_path = Path(Path.home(), 'Documents', 'GitHub', 'database', 'notas_teste')
    all_data, errors = main(file_path, broker='necton2')
       
    df_ops = pd.concat(all_data, axis=0)
    df_ops.reset_index(inplace=True, drop=True)
    
    df = pd.concat([df_firstpos, df_ops])
    df['ticker'] = df['ticker'].str.strip()
    df.reset_index(inplace=True, drop=True)
    
    portfolio, df = calculate_PnL_averagePrices(df)
    
    return portfolio, df



