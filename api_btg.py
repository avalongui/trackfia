import json
from pathlib import Path
from datetime import datetime
from datetime import timedelta
import pandas as pd

from api_btg_utils import auth_apiBTG, fia_main_info, portfolio_api, read_xls, read_xml


def fund_data(find_type='xml'):
    
    json_path = Path.home() / 'Desktop' / 'api_btg_info.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Token de acesso
    token, data = auth_apiBTG(config)
    
    if find_type == 'excel':
        # Carteira xls
        counter = -1
        df = pd.DataFrame()
        while len(df) == 0:
            counter+=1
            print(f'Voltando {counter} dias para obter PL...')
            date_ref = datetime.today() - timedelta(days=counter)
            formt_time = datetime.strftime(date_ref, format='%Y-%m-%d')
            response_portfolio = portfolio_api(token, data, start_date=formt_time, end_date=formt_time, type_report=10, page_size=100)
            df = read_xls(response_portfolio)
        
        # Encontrar PL do fundo
        print(f'PL encontrado para o dia {formt_time}')
        index_pl = df.iloc[:,0]
        index_pl = list(index_pl[index_pl=='Patrimonio'].index)[0]
        pl = df.iloc[index_pl+1,0]
        
        return pl
    
    elif find_type == 'xml':
        # Carteira xml
        counter = -1
        df_xml = pd.DataFrame()
        while len(df_xml) == 0:
            counter+=1
            print(f'Voltando {counter} dias para obter PL...')
            date_ref = datetime.today() - timedelta(days=counter)
            formt_time = datetime.strftime(date_ref, format='%Y-%m-%d')
            response_portfolio = portfolio_api(token, data, start_date=formt_time, end_date=formt_time, type_report=3, page_size=100)
            
            content_type = response_portfolio.headers.get('Content-Type')
            if 'application/octet-stream' in content_type or 'application/zip' in content_type:
                df_xml, data_xml, header = read_xml(response_portfolio)               
            else:
                print('Erro na captura do arquivo xml. O formato não é compatível...')
            
        return df_xml, data_xml, header
    

if __name__ == "__main__":
    
    json_path = Path.home() / 'Desktop' / 'api_btg_info.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Token de acesso
    token, data = auth_apiBTG(config)
    
    # Dados principais FIA
    info_fia = fia_main_info(token, data)
    
    # Carteira xls
    print('Selecione a data para pesquisa:')
    date_ref = input()
    response_portfolio = portfolio_api(token, data, start_date=date_ref, end_date=date_ref, type_report=10, page_size=100)
    df = read_xls(response_portfolio)
    
    # Encontrar PL do fundo
    index_pl = df.iloc[:,0]
    index_pl = list(index_pl[index_pl=='Patrimonio'].index)[0]
    pl = df.iloc[index_pl+1,0]
    
    # Carteira xml
    response_portfolio = portfolio_api(token, data, start_date='2024-07-08', end_date='2024-07-08', type_report=3, page_size=100)
    df_xml, data_xml, header = read_xml(response_portfolio)

    












































"""
report_url = 'https://funds-uat.btgpactual.com/reports/Portfolio'
scope = 'reports.portfolio'

current_time = datetime.utcnow().isoformat() + 'Z'
time.sleep(10) 
current_time_ = datetime.utcnow().isoformat() + 'Z'


payload = json.dumps({
  "contract": {
    "startDate": current_time,
    "endDate": current_time_,
    "typeReport": 3,
    "fundName": "AVALON FIA"
  },
  "pageSize": 100,
  "webhookEndpoint": "string"
})

headers = {
  'Content-Type': 'application/json',
  'X-SecureConnect-Token': 'Informe o token obtido na geração da autenticação'
}


response_report = requests.post(report_url, headers=report_headers, data=payload)
"""





