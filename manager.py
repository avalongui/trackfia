"""
Em algum momento proximo, o leitor_notas tera que ser transformado em um codigo de cases.
Ex.: case 1 para leitura da nota (com referencia de area e colunas), case 2 etc. Posso fazer o link especifico no comeco para cada
nota em cada data. Assim tambem acho que terei que fazer para o tratamento dos dados da nota e para encontrar a data.

Algumas coisas serao manuais agora nesse comeco, ate que eu me adapte melhor a essa leitura, inclusive integrando IA ao processo.
"""

import os
from pathlib import Path
from tqdm import tqdm
import pandas as pd

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

        # Inicializar o ticker no portfólio, se não existir
        if ticker not in portfolio:
            if len(ticker) <= 6:
                portfolio[ticker] = {'flag': 1, 'quantity': 0, 'total_cost': 0, 'average_price': 0.0}  # 1 para ação
            elif len(ticker) >= 7:
                portfolio[ticker] = {'flag': 2, 'quantity': 0, 'total_cost': 0, 'average_price': 0.0}  # 2 para opção

        portfolio[ticker]['short_sellig'] = 0 # nao e short selling
        
        if row['pos'] == 'C':  # Compra
            # Atualizar dados
            portfolio[ticker]['quantity'] += quantity
            portfolio[ticker]['total_cost'] += financial
            
            # PM
            portfolio[ticker]['average_price'] = portfolio[ticker]['total_cost'] / portfolio[ticker]['quantity']
            df.at[index, 'average_price'] = portfolio[ticker]['average_price']
        
        elif row['pos'] == 'V':  # Venda
            if portfolio[ticker]['quantity'] > 0:  # Venda de posição comprada (long)
                # Preco e PnL
                average_price = portfolio[ticker]['average_price']
                pnl = (price - average_price) * quantity
                df.at[index, 'P&L'] = pnl
                
                # Atualizar dados
                portfolio[ticker]['quantity'] -= quantity
                portfolio[ticker]['total_cost'] -= average_price * quantity
                
                # Se venda completa, resetar PM
                if portfolio[ticker]['quantity'] == 0:
                    portfolio[ticker]['average_price'] = 0.0
                df.at[index, 'average_price'] = portfolio[ticker]['average_price']
            else:  # Short selling
                portfolio[ticker]['short_sellig'] = 1
            
                portfolio[ticker]['quantity'] -= quantity  # Incrementa posição short (quantidade negativa)
                portfolio[ticker]['total_cost'] += financial  # Atualiza o custo total com valor positivo
                
                # PM
                portfolio[ticker]['average_price'] = portfolio[ticker]['total_cost'] / abs(portfolio[ticker]['quantity'])
                df.at[index, 'average_price'] = portfolio[ticker]['average_price']

    return portfolio, df


def first_pos_fia():
    first_positions = Path(Path.home(), 'Documents', 'GitHub', 'database', 'Carteira_AVALON_FIA_21_06_2024.xlsx')
    df_firstpos = pd.read_excel(first_positions)
    
    # Selecionar ativos e precos
    loc_stocks = list(df_firstpos[df_firstpos.iloc[:,0]=='Departamento'].index)[0]
    stocks_df = df_firstpos.iloc[loc_stocks + 1:].dropna(how='all').reset_index(drop=True)
    loc_end = list(stocks_df[stocks_df.iloc[:,0]=='Compromissada Over'].index)[0]
    stocks_df = stocks_df.iloc[0:loc_end,:]
    
    stocks_df = stocks_df.iloc[:, 3:7]
    stocks_df.columns = ['ticker', 'quantidade', 'preco', 'financeiro']
    stocks_df['pos'] = 'C'
    stocks_df['data'] = pd.to_datetime('2021-06-21')
    stocks_df['nome_cia'] = 'first_ops'
    stocks_df = stocks_df[['pos', 'nome_cia', 'quantidade', 'preco', 'financeiro', 'ticker', 'data']]
    
    return stocks_df


def run_manager_xml():
    
    df_firstpos = first_pos_fia()
    df_ops = run_xmls()

    df = pd.concat([df_firstpos, df_ops])
    df['ticker'] = df['ticker'].str.strip()
    df.reset_index(inplace=True, drop=True)
    
    df = df.sort_values('data')
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
    
    df = df.sort_values('data')
    portfolio, df = calculate_PnL_averagePrices(df)
    
    return portfolio, df