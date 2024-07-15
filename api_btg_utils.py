import os
import tempfile
import zipfile
import requests
import time
import json
import time
import pandas as pd
import xml.etree.ElementTree as ET


def auth_apiBTG(config):
    
    # Credenciais
    client_id = config.get('CLIENT_ID')
    client_secret = config.get('CLIENT_SECRET')
    grant_type = config.get('GRANT_TYPE')

    # URL de autenticação e relatorios
    auth_url = 'https://funds.btgpactual.com/connect/token'
   
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    # Dados para a autenticacao
    data = {
        'grant_type': grant_type,
        'client_id': client_id,
        'client_secret': client_secret,
    }
    
    # Token
    time.sleep(10)
    response = requests.post(auth_url, headers=headers, data=data)
    
    # available_data = response.json()
    token = response.json().get('access_token')
    
    return token, data


def fia_main_info(token, data):
    
    # Info principais FIA
    report_url = 'https://funds.btgpactual.com/reports/Fund'
    ticket_base_url = 'https://funds.btgpactual.com/reports/Ticket'

    payload = json.dumps({
        "contract": {},
        "webhookEndpoint": "string"
    })
    
    # Headers
    report_headers = {
        'Content-Type': 'application/json',
        'X-SecureConnect-Token': token
    }
    
    # Requisicao relatorio
    response_report = requests.post(report_url, headers=report_headers, data=payload)
    ticket = response_report.json().get('ticket')
    ticket_url = f'{ticket_base_url}?ticketId={ticket}'
    
    # Headers para ticket
    ticket_headers = {
        'Content-Type': 'application/json',
        'X-SecureConnect-Token': token
    }
    
    # Dados FIA Avalon
    time.sleep(10)
    response_ticket = requests.get(ticket_url, headers=ticket_headers)
    info = response_ticket.json()
    
    return info


def portfolio_api(token, data, start_date, end_date, type_report, page_size):
    
    # Portfolio
    report_url = 'https://funds.btgpactual.com/reports/Portfolio'
    ticket_base_url = 'https://funds.btgpactual.com/reports/Ticket'
    scope = 'reports.position'
    
    data['scope'] = scope
    payload = json.dumps({
        'contract': {
            'startDate': start_date,
            'endDate': end_date,
            'typeReport': type_report,
            'fundName': 'AVALON FIA'
        },
        
        'pageSize': page_size,
        'webhookEndpoint': 'string'
    })
    
    # Headers 
    report_headers = {
        'Content-Type': 'application/json',
        'X-SecureConnect-Token': token
    }
    
    # Requisicao 
    response_report = requests.post(report_url, headers=report_headers, data=payload)
    
    # Requisicao de relatorio
    ticket = response_report.json().get('ticket')
    ticket_url = f'{ticket_base_url}?ticketId={ticket}'
    
    # Headers
    ticket_headers = {
        'Content-Type': 'application/json',
        'X-SecureConnect-Token': token
    }
    
    # Carteira Avalon
    time.sleep(10)
    response_ticket = requests.get(ticket_url, headers=ticket_headers)
    
    return response_ticket


def parse_xml(root):

    data_xml = []

    fundo = root.find('fundo')
    header = fundo.find('header')

    # Extrair dados do header
    header_data = {
        'isin': header.find('isin').text,
        'cnpj': header.find('cnpj').text,
        'nome': header.find('nome').text,
        'dtposicao': header.find('dtposicao').text,
        'nomeadm': header.find('nomeadm').text,
        'cnpjadm': header.find('cnpjadm').text,
        'nomegestor': header.find('nomegestor').text,
        'cnpjgestor': header.find('cnpjgestor').text,
        'nomecustodiante': header.find('nomecustodiante').text,
        'cnpjcustodiante': header.find('cnpjcustodiante').text,
        'valorcota': float(header.find('valorcota').text),
        'quantidade': float(header.find('quantidade').text),
        'patliq': float(header.find('patliq').text),
        'valorativos': float(header.find('valorativos').text),
        'valorreceber': float(header.find('valorreceber').text),
        'valorpagar': float(header.find('valorpagar').text),
        'vlcotasemitir': float(header.find('vlcotasemitir').text),
        'vlcotasresgatar': float(header.find('vlcotasresgatar').text),
        'codanbid': header.find('codanbid').text,
        'tipofundo': header.find('tipofundo').text,
        'nivelrsc': header.find('nivelrsc').text
    }
    
    # Extrair dados dos títulos públicos
    for titpublico in fundo.findall('titpublico'):
        data_xml.append({
            'tipo': 'titpublico',
            'isin': titpublico.find('isin').text,
            'codativo': titpublico.find('codativo').text,
            'cusip': titpublico.find('cusip').text,
            'dtemissao': titpublico.find('dtemissao').text,
            'dtoperacao': titpublico.find('dtoperacao').text,
            'dtvencimento': titpublico.find('dtvencimento').text,
            'qtdisponivel': int(titpublico.find('qtdisponivel').text),
            'qtgarantia': int(titpublico.find('qtgarantia').text),
            'depgar': int(titpublico.find('depgar').text),
            'pucompra': float(titpublico.find('pucompra').text),
            'puvencimento': float(titpublico.find('puvencimento').text),
            'puposicao': float(titpublico.find('puposicao').text),
            'puemissao': float(titpublico.find('puemissao').text),
            'principal': float(titpublico.find('principal').text),
            'tributos': float(titpublico.find('tributos').text),
            'valorfindisp': float(titpublico.find('valorfindisp').text),
            'valorfinemgar': float(titpublico.find('valorfinemgar').text),
            'coupom': float(titpublico.find('coupom').text),
            'indexador': titpublico.find('indexador').text,
            'percindex': int(titpublico.find('percindex').text),
            'caracteristica': titpublico.find('caracteristica').text,
            'percprovcred': int(titpublico.find('percprovcred').text),
            'classeoperacao': titpublico.find('classeoperacao').text,
            'idinternoativo': titpublico.find('idinternoativo').text,
            'nivelrsc': titpublico.find('nivelrsc').text
        })

    # Extrair dados das ações
    for acao in fundo.findall('acoes'):
        data_xml.append({
            'tipo': 'acoes',
            'isin': acao.find('isin').text,
            'cusip': acao.find('cusip').text,
            'codativo': acao.find('codativo').text,
            'qtdisponivel': int(acao.find('qtdisponivel').text),
            'lote': int(acao.find('lote').text),
            'qtgarantia': int(acao.find('qtgarantia').text),
            'valorfindisp': float(acao.find('valorfindisp').text),
            'valorfinemgar': float(acao.find('valorfinemgar').text),
            'tributos': float(acao.find('tributos').text),
            'puposicao': float(acao.find('puposicao').text),
            'percprovcred': int(acao.find('percprovcred').text),
            'tpconta': int(acao.find('tpconta').text),
            'classeoperacao': acao.find('classeoperacao').text,
            'dtvencalug': acao.find('dtvencalug').text,
            'txalug': float(acao.find('txalug').text),
            'cnpjinter': acao.find('cnpjinter').text
        })

    # Extrair dados das provisões
    for provisao in fundo.findall('provisao'):
        data_xml.append({
            'tipo': 'provisao',
            'codprov': provisao.find('codprov').text,
            'credeb': provisao.find('credeb').text,
            'dt': provisao.find('dt').text,
            'valor': float(provisao.find('valor').text)
        })

    df = pd.DataFrame(data_xml)

    return df, data_xml, header_data


def read_xml(response_portfolio):
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.bin')
    temp_file.write(response_portfolio.content)
    temp_file.close()
    print(f"Conteúdo salvo como {temp_file.name}")
    
    try:
        tree = ET.parse(temp_file.name)
        root = tree.getroot()
        df_, data_xml, header = parse_xml(root)
        return df_, data_xml, header
        
    except ET.ParseError:
        print("Erro ao analisar o arquivo XML.")
        return pd.DataFrame(), None, None
    

def read_xls(response_portfolio):
    content_type = response_portfolio.headers.get('Content-Type')
    if 'application/octet-stream' in content_type or 'application/zip' in content_type:
        # Salvar conteúdo binário em um arquivo temporário
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_zip.write(response_portfolio.content)
        temp_zip.close()
        print(f"Conteúdo salvo como {temp_zip.name}")
    
        # Descompactar o arquivo ZIP e identificar o arquivo Excel
        with zipfile.ZipFile(temp_zip.name, 'r') as zip_ref:
            extracted_files = zip_ref.namelist()
            zip_ref.extractall(tempfile.gettempdir())
    
            # Procurar o arquivo Excel principal
            excel_file_path = None
            for file in extracted_files:
                if file.endswith('xl/worksheets/sheet1.xml'):
                    excel_file_path = os.path.join(tempfile.gettempdir(), 'xl', 'worksheets', 'sheet1.xml')
                    break
    
            if excel_file_path:
                # Reconstruir o caminho do arquivo Excel
                reconstructed_excel_path = os.path.join(tempfile.gettempdir(), 'reconstructed.xlsx')
                with zipfile.ZipFile(reconstructed_excel_path, 'w') as new_zip:
                    for file in extracted_files:
                        new_zip.write(os.path.join(tempfile.gettempdir(), file), file)
                # Ler o arquivo Excel com pandas
                df = pd.read_excel(reconstructed_excel_path, engine='openpyxl')

            else:
                print('Arquivo Excel não encontrado...')
                
            return df
    
    else:
        print('Resposta não condizente com captura... Conteúdo:')
        # print(response_portfolio.text)
        return pd.DataFrame()
