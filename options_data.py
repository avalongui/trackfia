import os
import re
import pandas as pd
import datetime as dt
from tqdm import tqdm
from pathlib import Path

from mt5_connect import *
from manager import *
# from options_data_histb3 import downloadB3Hist


def id_options(opts_id):
    
    url = 'https://www.dadosdemercado.com.br/bolsa/acoes'
    tables = pd.read_html(url)
    data = tables[0]
    ativos = list(data.Ticker)
    # not_found_stocks = pkl.load(open(Path(Path.home(), 'Documents', 'github', 'avaloncapital', 'strategies', 'erros_mt5.pkl'), "rb"))
    # stocks = [i for i in stocks if i not in not_found_stocks]
        
    # diferenciar calls e puts
    calls = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
    puts = ['M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X']

    columns_df = ['stock', 'ticker', 'tipo', 'vencimento']
    df_opts = pd.DataFrame(columns=columns_df)
    
    def get_data(n1, n2, df):
        return df[n1:n2].replace(' ', '')

    def fix_price(var):
        reg = re.compile(r'[0]{10}')
        var = reg.sub('', var)
        var = pd.to_numeric(var[-6:-2] + '.' + var[-2:])
        return var

    def fix_ticker(var):
        if var.startswith('ON'):
            var = '3'
        elif var.startswith('PNA'):
            var = '5'
        elif var.startswith('PNB'):
            var = '6'
        elif var.startswith('PNC'):
            var = '7'
        elif var.startswith('PND'):
            var = '8'
        elif var.startswith('PN'):
            var = '4'
        elif var.startswith('UN'):
            var = '11'
        else:
            # print('não encontrei o tipo de papel: possíveis casos de IBOV e BOVA...')
            pass
        return var
    
    # abertura do txt
    home = Path.home()
    txt_path = Path(home, 'Documents', 'GitHub', 'database', 'historico_b3', f'COTAHIST_D19072024.TXT')

    if os.path.exists(txt_path):
        df_txt = pd.read_table(txt_path, encoding='Latin-1', index_col=None, header=0)
        np_txt = (df_txt.iloc[0:-1,0]).to_numpy()
    
    records = []
    for i in tqdm(np_txt):
        # filtro de opcoes
        ticker = get_data(12, 24, i)
        if ticker not in opts_id:
            continue
        else: 
            
            if len(ticker) >= 8:
                # filtro de empresas listadas
                nome_empresa = get_data(27, 39, i)[0:4]
                tipo_papel = get_data(39, 49, i)
                tipo_papel = fix_ticker(tipo_papel)
                nome_empresa = nome_empresa + tipo_papel
                ticker_ref = ticker[0:4] + tipo_papel
                info = i
    
                if nome_empresa in ativos:
                    tipo_registro = get_data(0, 2, i)
                    data_pregao = pd.to_datetime(get_data(2, 10, i), format='%Y%m%d')
                    price_exe = get_data(188,201,i)
                    strike = fix_price(price_exe)
    
                    if str(ticker[4]) in calls:
                        type_option = 'c'
                    elif ticker[4] in puts:
                        type_option = 'p'
                    else:
                        print(f'Não encontrei o tipo de opção para {ticker}')
                        continue
                    
                    data_venc = pd.to_datetime(get_data(202, 210, i), format='%Y%m%d', errors='coerce')
                    
                    # Adiciona registro à lista
                    records.append({
                        'stock': ticker_ref,
                        'ticker': ticker,
                        'tipo': type_option,
                        'vencimento': data_venc,
                        'strike': strike,
                        'info': info
                    })

    # Converte a lista de registros para um DataFrame
    df_opts = pd.DataFrame(records)
    
    return df_opts

