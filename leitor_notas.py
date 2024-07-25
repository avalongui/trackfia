import os
import re
import time
import locale
import tabula
import requests
import numpy as np
import pandas as pd
import pickle as pkl
from tqdm import tqdm
from pathlib import Path



def read_pdf(file, area, columns):
    return tabula.read_pdf(
        file, pages="all", multiple_tables=False, area=area, 
        columns=columns, encoding='Latin-1', pandas_options={'decimal':',', 'header':None}
    )


def identify_tickers(df, ticker_storage):
    # Ticker control
    for i in df.index:
        if df.shape[0] == 1:
            company_name = df.iloc[0,1]
        else:
            company_name = df.iloc[i,1]
            
        if company_name not in ticker_storage:
            print('\n Nome de referência: {}'.format(company_name))           
            print('Ticker correto: ')
            ticker = str(input()).upper()
            ticker_storage[company_name] = ticker
            df.loc[i,'ticker'] = ticker
        else:
            df.loc[i,'ticker'] = ticker_storage[company_name]
    return df, ticker_storage


def handle_data_xp(df):
    # Clean data
    df.columns = df.iloc[0,:]  # set columns --> essa parte so funciona se estivermos pegando o cabecalho na area 
    try:
        df.drop(df.loc[df['Q Negociação']=='Q Negociação'].index, inplace=True)  # drop duplicated headers
    except:
        df.drop(df.loc[df['Negociação']=='Negociação'].index, inplace=True)  # drop duplicated headers
    if df.shape[0] > 1:
        # df = df.iloc[1:,:]  # drop first row --> parece que essa parte esta excluindo indevidamente uma linha de operacoes
        df.reset_index(drop=True, inplace=True)
    
    # Convert numbers
    locale.setlocale(locale.LC_NUMERIC, '')
    df.iloc[:,6:9] = df.iloc[:,6:9].applymap(locale.atof)
    df = df.iloc[:,[1,4,6,7,8]]
    cols = ['pos', 'nome_cia', 'quantidade', 'preco', 'financeiro']
    df.columns = cols
    
    return df

def handle_data_necton(df):
    # Clean data
    df.columns = df.iloc[0,:] # set columns --> essa parte so funciona se estivermos pegando o cabecalho na area 
    try:
        df.drop(df.loc[df['Q Bolsa']=='Q Bolsa'].index, inplace=True) 
        df.drop(df.loc[df['Q Bolsa']=='esumo dos Negócios'].index, inplace=True) # drop duplicated headers
    except:
        df.drop(df.loc[df['Negociação']=='Negociação'].index, inplace=True)  # drop duplicated headers
        
    if df.shape[0] > 1:
        # df = df.iloc[1:,:] # drop first row --> parece que essa parte esta excluindo indevidamente uma linha de operacoes
        df.reset_index(drop=True, inplace=True)
    
    # Convert numbers
    locale.setlocale(locale.LC_NUMERIC, '')
    df.iloc[:,7:10] = df.iloc[:,7:10].astype(str)
    df.iloc[:,7:10] = df.iloc[:,7:10].applymap(locale.atof)
    df = df.iloc[:,[1,4,7,8,9]]
    cols = ['pos', 'nome_cia', 'quantidade', 'preco', 'financeiro']
    df.columns = cols
    
    return df


def extract_date_xp(file):
    # Handle dates
    date_list = tabula.read_pdf(
        file, pages="1", multiple_tables=False, area=[59.81, 519.87, 67.10, 560.15],
        columns=[560.40], encoding='Latin-1', pandas_options={'decimal':',', 'header':None}
    )
    date = pd.to_datetime(date_list[0].iloc[0, 0], format='%d/%m/%Y')
    return date


def extract_date_necton(file):
    # Handle dates
    try:
        date_list = tabula.read_pdf(
        file, pages="1", multiple_tables=False, area=[0, 0, 200, 600],
        columns=[560.40], encoding='Latin-1', pandas_options={'decimal':',', 'header':None})
        
        date_str = date_list[0].iloc[2, 0].split()[-1]  # '5706346 1 28/06/2024'
        date = pd.to_datetime(date_str, format='%d/%m/%Y')
        
    except:
        date_list = tabula.read_pdf(
        file, pages="1", multiple_tables=False, area=[0, 0, 200, 600],
        columns=[530.40], encoding='Latin-1', pandas_options={'decimal':',', 'header':None})
        
        date_str = date_list[0].iloc[1, 1].split()[-1]  # '5706346 1 28/06/2024'
        date = pd.to_datetime(date_str, format='%d/%m/%Y')
        
    return date


def process_brokerage_note_xp(file, ticker_storage):
    area = [240.55, 33.57, 437.73, 566.27]
    columns = [90.32, 106.25, 150.2, 180.99, 306.28, 339.70, 389.245, 446.305, 543.705, 560.995]
    
    table_list = read_pdf(file, area, columns)
    if len(table_list) == 0:
        return None, None
    
    df = pd.concat(table_list)
    df = handle_data_xp(df)
    
    df, ticker_storage = identify_tickers(df, ticker_storage)
    df['data'] = extract_date_xp(file)
    
    return df, ticker_storage


def process_brokerage_note_necton(file, ticker_storage):
    area = [170, 33.57, 437.73, 566.27]
    columns = [90.32, 106.25, 150.2, 180.99, 306.28, 339.70, 389.245, 446.305, 500.705, 540.995, 560.000]
    
    table_list = read_pdf(file, area, columns)
    if len(table_list) == 0:
        return None, None
    
    df = pd.concat(table_list)
    df = handle_data_necton(df)
    df.dropna(inplace=True)
    
    df, ticker_storage = identify_tickers(df, ticker_storage)
    df['data'] = extract_date_necton(file)
    
    return df, ticker_storage


def process_brokerage_note_necton2(file, ticker_storage):
    area = [230.55, 28.57, 437.73, 566.27]
    columns = [75.00, 85.25, 150.2, 170.99, 306.28, 339.70, 389.245, 446.305, 510.705]
    
    table_list = read_pdf(file, area, columns)
    if len(table_list) == 0:
        return None, None
    
    df = pd.concat(table_list)
    df = handle_data_necton(df)
    df.dropna(inplace=True)
    
    df, ticker_storage = identify_tickers(df, ticker_storage)
    df['data'] = extract_date_necton(file)
    
    return df, ticker_storage


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


def main(file_path, broker='xp'):
    all_data = []
    errors = []
    ticker_storage = pkl.load(open(Path(Path.home(), 'Desktop', 'notas_dict.pkl'),'rb'))

    for item in tqdm(os.listdir(file_path)):
        file = Path(file_path, item)
        
        # Depending on the brokerage note, call the specific processing function
        if broker == 'xp':
            df, ticker_storage = process_brokerage_note_xp(file, ticker_storage)
        elif broker == 'necton':
            df, ticker_storage = process_brokerage_note_necton(file, ticker_storage)
        elif broker == 'necton2':
            df, ticker_storage = process_brokerage_note_necton2(file, ticker_storage)
            
        if df is None:
            errors.append(item)
            continue
        
        all_data.append(df)
    
    # Store the updated ticker storage
    pkl.dump(ticker_storage, open(Path(Path.home(), 'Desktop', 'notas_dict.pkl'), 'wb'))
    
    # Further processing or return all_data as needed
    return all_data, errors


    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
"""
# MANAGE POSITIONS SCRIPT
# merge dfs



# Calcular o P&L das operações finalizadas e o preço médio das posições restantes
result = {}
for ticker in df['ticker'].unique():
    df_ticker = df[df['ticker'] == ticker].sort_values(by='data')
    if all(df_ticker['pos'] == 'V'):
        continue
    
    total_compra = 0
    total_quantidade = 0
    total_venda = 0
    quantidade_vendida = 0
    
    for index, row in df_ticker.iterrows():
        if row['pos'] == 'C':
            total_compra += row['preco'] * row['quantidade']
            total_quantidade += row['quantidade']
        elif row['pos'] == 'V':
            total_venda += row['preco'] * row['quantidade']
            quantidade_vendida += row['quantidade']
    
    # Calculando P&L das operações finalizadas
    pl = total_venda - (total_compra * (quantidade_vendida / total_quantidade))
    
    # Calculando o preço médio das posições restantes
    quantidade_restante = total_quantidade - quantidade_vendida
    preco_medio_restante = (total_compra - total_compra * (quantidade_vendida / total_quantidade)) / quantidade_restante if quantidade_restante > 0 else 0
    
    result[ticker] = {
        'PL': pl,
        'quantidade_restante': quantidade_restante,
        'preco_medio_restante': preco_medio_restante
    }

# Exibir o resultado
for ticker, data in result.items():
    print(f"Ticker: {ticker}, P&L: {data['PL']:.2f}, Quantidade Restante: {data['quantidade_restante']}, Preço Médio Restante: {data['preco_medio_restante']:.2f}")




























    
# average price
duplicates = list(set(df_ops['ticker'][df_ops['ticker'].duplicated()]))
df_ops.quantidade = np.where(df_ops.pos == 'V', -1*df_ops.quantidade, df_ops.quantidade)
df_ops.financeiro = df_ops.quantidade * df_ops.preco

pm = df_ops.groupby(by=['data', 'ticker'])['financeiro', 'quantidade'].sum()
pm['pm'] = np.where(pm.financeiro>0, pm.financeiro/pm.quantidade, pm.financeiro/pm.quantidade*-1)

# PnL
# df_ops.to_excel(Path(Path.home(), 'Desktop', 'ops_test.xlsx'))
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        







   # calculo de lucro/prejuizo em operacoes fechadas
   duplicates = list(set(transacoes['ticker'][transacoes['ticker'].duplicated()]))
   pm_values = {}
   all_data = {}
   for asset in list(set(transacoes['ticker'])):
       if asset not in duplicates:
           pm_df = transacoes[transacoes.ticker == asset].reset_index(drop=True)
           pm_df['Posicao'] = np.nan
           pos = float(pm_df['Quantidade'])
           if pos > 0:
               pm_df['Posicao'] = 'C'
           if pos < 0:
               pm_df['Posicao'] = 'V'
           if pos == 0:
               pm_df['Posicao'] = 'N'
                      
           # preco
           pm_df['PM'] = pm_df['Preço'] 
           
           pm_df['Lucro/Prejuízo'] = np.nan
           # coluna de preparo para impostos 
           pm_df['Volume_Fin'] = np.nan
           all_data[asset] = pm_df
           
       if asset in duplicates:
           # tabela para calculo de pm
           pm_df = transacoes[transacoes.ticker == asset].reset_index(drop=True)

           # identificar posicoes compradas e vendidas
           pm_df['Posicao'] = np.nan
           for row in pm_df.itertuples():
               index_ref = row.Index
               pos = np.sum(pm_df[(pm_df.index >= 0) & (pm_df.index <= row.Index)]['Quantidade'])
               if pos > 0:
                   pm_df.loc[index_ref,'Posicao'] = 'C'
               if pos < 0:
                   pm_df.loc[index_ref,'Posicao'] = 'V'
               if pos == 0:
                   pm_df.loc[index_ref,'Posicao'] = 'N'

           # calculo de lucro/prejuizo por operacao
           # obs.: aqui e preciso identificar cada venda, olhar para tras e fazer os calculos
           # obs2.: esses calculos nao contemplam a possibilidade de inversao da posicao (*zerar para depois vender)
           for row in pm_df.itertuples():
               # calculo de lucro/prejuizo para posicao comprada
               if ((row.Posicao == 'C') and (row.Quantidade < 0)) or ((row.Posicao == 'N') and (row.Quantidade < 0)):
                   # preco e volume de venda
                   sell = float(pm_df[pm_df.index == row.Index]['Preço'])
                   qt_sell = float(pm_df[pm_df.index == row.Index]['Quantidade'])
                   # calculo do pm anterior
                   count_df = pm_df[pm_df.index <= row.Index]
                   quant_filter = count_df[count_df.Quantidade>0]['Quantidade']
                   price_filter = count_df[count_df.Quantidade>0]['Preço']
                   prices_weight = float(np.sum(price_filter * quant_filter))
                   quant_total = np.sum(quant_filter)
                   pm = float(round(prices_weight / quant_total, 2))
                   # inserir esse PM na tabela
                   result_pct = sell/pm - 1
                   sell_ref = count_df.iloc[-1].Quantidade * -1
                   result = (sell_ref*pm) * result_pct
                   # resultados
                   pm_df.loc[row.Index, 'Lucro/Prejuízo'] = result
                   # coluna de preparo para impostos 
                   pm_df.loc[row.Index, 'Volume_Fin'] = sell * qt_sell
                   # all_data[asset] = pm_df
                   
               # calculo de lucro/prejuizo para posicao vendida
               if ((row.Posicao == 'V') and (row.Quantidade > 0)) or ((row.Posicao == 'N') and (row.Quantidade > 0)):
                   # preco e volume de compra
                   buy = float(pm_df[pm_df.index == row.Index]['Preço'])
                   qt_buy = float(pm_df[pm_df.index == row.Index]['Quantidade'])
                   # calculo do pm anterior
                   count_df = pm_df[pm_df.index <= row.Index]
                   quant_filter = count_df[count_df.Quantidade<0]['Quantidade']
                   price_filter = count_df[count_df.Quantidade<0]['Preço']
                   prices_weight = float(np.sum(price_filter * quant_filter))
                   quant_total = np.sum(quant_filter)
                   pm = float(round(prices_weight / quant_total, 2))
                   result_pct = buy/pm - 1
                   sell_ref = count_df.iloc[-1].Quantidade * -1
                   result = (sell_ref*pm) * result_pct
                   # resultados
                   pm_df.loc[row.Index, 'Lucro/Prejuízo'] = result
                   # coluna de preparo para impostos 
                   pm_df.loc[row.Index, 'Volume_Fin'] = buy * qt_buy
                   # all_data[asset] = pm_df
               
               else:
                   pass
                   # all_data[asset] = pm_df
               
               # calculo do PM para analise de retornos
               # obs.: o ideal seria inserir essa parte no loop anterior (pendencia)
               if (row.Posicao == 'C') or (row.Posicao == 'N'):
                   if row.Index == 0:
                       pm_df.loc[row.Index, 'PM'] = pm_df.loc[row.Index, 'Preço']
                   else:
                       # vendas nao sao computadas como alteracoes no PM, entao o PM e o mesmo da linha anterior
                       count_df = pm_df[pm_df.index <= row.Index]
                       if pm_df.loc[row.Index, 'Quantidade'] < 0:
                           pm_df.loc[row.Index, 'PM'] = pm_df.loc[row.Index-1, 'PM']
                       else:
                           quant_filter = count_df[count_df.Quantidade>0]['Quantidade']
                           price_filter = count_df[count_df.Quantidade>0]['Preço']
                           prices_weight = float(np.sum(price_filter * quant_filter))
                           quant_total = np.sum(quant_filter)
                           pm = float(round(prices_weight / quant_total, 2))
                           pm_df.loc[row.Index, 'PM'] = pm
               
               if (row.Posicao == 'V'):
                   if row.Index == 0:
                       pm_df.loc[row.Index, 'PM'] = pm_df.loc[row.Index, 'Preço']
                   else:
                       # compras nao sao computadas como alteracoes no PM (posicao vendida), entao o PM e o mesmo da linha anterior
                       count_df = pm_df[pm_df.index <= row.Index]
                       if pm_df.loc[row.Index, 'Quantidade'] > 0:
                           pm_df.loc[row.Index, 'PM'] = pm_df.loc[row.Index-1, 'PM']
                       else:
                           quant_filter = count_df[count_df.Quantidade<0]['Quantidade']
                           price_filter = count_df[count_df.Quantidade<0]['Preço']
                           prices_weight = float(np.sum(price_filter * quant_filter))
                           quant_total = np.sum(quant_filter)
                           pm = float(round(prices_weight / quant_total, 2))
                           pm_df.loc[row.Index, 'PM'] = pm
               
               all_data[asset] = pm_df
           
   # calculos de pm final: desprezando vendas ou compras (a depender da posicao)
   for asset in transacoes['ticker']:
       # verificar se ha posicao e se ela e comprada ou vendida
       position = np.sum(transacoes[(transacoes.ticker == asset) & (transacoes.Quantidade)]['Quantidade'])
       if position > 0:
           quant = transacoes[(transacoes.ticker == asset) & (transacoes.Quantidade > 0)]['Quantidade'] 
           prices = transacoes[(transacoes.ticker == asset) & (transacoes.Quantidade > 0)]['Preço']
           pm_calc = np.sum(quant*prices)
           quant_total = np.sum(quant)
           pm_final = pm_calc/quant_total
           pm_values[asset] = round(pm_final,2)
       if position < 0:
           quant = transacoes[(transacoes.ticker == asset) & (transacoes.Quantidade < 0)]['Quantidade'] 
           prices = transacoes[(transacoes.ticker == asset) & (transacoes.Quantidade < 0)]['Preço']
           pm_calc = np.sum(quant*prices)
           quant_total = np.sum(quant)
           pm_final = pm_calc/quant_total
           pm_values[asset] = round(pm_final,2)
       
   final_df = pd.concat(all_data)
   final_df = final_df.sort_values(by='Data da Transação')
   
   # calculo de pagamento de impostos
   darf = {}
   final_df['Mês'] = final_df['Data da Transação'].apply(lambda x: x.month)
   for info in final_df.groupby(['Mês']):
       if np.sum(list(info[1].Volume_Fin)) > 20000:
           result_month =  np.sum(list(info[1]['Lucro/Prejuízo']))
           if result_month > 0:
               darf[info[0]] = result_month * 0.15


"""


