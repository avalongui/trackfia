import os
import xml.etree.ElementTree as ET
import pandas as pd
from pathlib import Path
import pickle as pkl
from tqdm import tqdm


def parse_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()

    data = []
    
    for evento in root.findall('evento'):
        cliente = evento.find('cliente')
        nome = cliente.find('nome').text
        cpfcnpj = cliente.find('cpfcnpj').text
        datadonegocio = evento.get('datadonegocio')
        
        for negocio in evento.findall('negocio'):
            qualificado = negocio.find('qualificado').text
            local = negocio.find('local').text
            natureza = negocio.find('natureza').text
            mercado = negocio.find('mercado').text
            isin = negocio.find('isin').text
            especificacao = negocio.find('especificacao').text
            quantidade = negocio.find('quantidade').text
            precoajuste = negocio.find('precoajuste').text
            volume = negocio.find('volume').text

            data.append({
                'nome': nome,
                'cpfcnpj': cpfcnpj,
                'qualificado': qualificado,
                'local': local,
                'natureza': natureza,
                'mercado': mercado,
                'isin': isin,
                'especificacao': especificacao,
                'quantidade': quantidade,
                'precoajuste': precoajuste,
                'volume': volume,
                'data': datadonegocio 
            })

    df = pd.DataFrame(data)
    df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y')

    # Convertendo colunas numericas
    df['quantidade'] = pd.to_numeric(df['quantidade'].str.replace('.', '').str.replace(',', '.'))
    df['precoajuste'] = pd.to_numeric(df['precoajuste'].str.replace('.', '').str.replace(',', '.'))
    df['volume'] = pd.to_numeric(df['volume'].str.replace('.', '').str.replace(',', '.'))

    return df, pd.to_datetime(datadonegocio, format='%d/%m/%Y')


def identify_tickers(df, ticker_storage):
    # Ticker control
    for i in df.index:
        company_name = df.loc[i,'especificacao']

        if company_name not in ticker_storage:
            print('\n Nome de referência: {}'.format(company_name))           
            print('Ticker correto: ')
            ticker = str(input()).upper()
            ticker_storage[company_name] = ticker
            df.loc[i,'ticker'] = ticker
        else:
            df.loc[i,'ticker'] = ticker_storage[company_name]
    return df, ticker_storage


def calculate_average_prices(df):
    
    grouped = df.groupby(['ticker', 'natureza'])
    
    result = []
    
    # Iterar pelos grupos para calcular o preço médio
    for (ticker, natureza), group in grouped:
        total_quantidade = group['quantidade'].sum()
        total_volume = group['volume'].sum()
        especificacao = group['especificacao'].unique()[0]
        
        if total_quantidade != 0:
            preco_medio = total_volume / total_quantidade
        else:
            preco_medio = 0
        
        result.append({
            'ticker': ticker,
            'natureza': natureza,
            'quantidade_total': total_quantidade,
            'volume_total': total_volume,
            'preco_medio': preco_medio,
            'nome_cia': especificacao
        })
    
    return pd.DataFrame(result)


def run_xmls():
    
    ticker_storage = pkl.load(open(Path(Path.home(), 'Desktop', 'notas_dict.pkl'),'rb'))
    
    # adpts
    # ticker_storage['GPS  ON      NM'] = 'GGPS3'
    
    file_path = Path(Path.home(), 'Documents', 'GitHub', 'database', 'operacoes_fia_xml')
    all_data = []
    for item in tqdm(os.listdir(Path(file_path))):
        file_rout = Path(file_path, item)
        
        file_xml, data = parse_xml(file_rout)
        df_ops, ticker_storage = identify_tickers(file_xml, ticker_storage)
        df_ops['volume'] = abs(df_ops['volume'])
        df_handle = calculate_average_prices(df_ops)
        df_handle['data'] = data
        df_handle.columns = ['ticker', 'pos', 'quantidade', 'financeiro', 'preco', 'nome_cia', 'data']
        all_data.append(df_handle)
    
    df = pd.concat(all_data)
    pkl.dump(ticker_storage, open(Path(Path.home(), 'Desktop', 'notas_dict.pkl'), 'wb'))

    return df