import MetaTrader5 as mt5
import time
import logging
import pandas as pd
from datetime import datetime


def initialize(login=None, server=None, key=None, user_path=None):
    if user_path == None:
        if not mt5.initialize(login=login, server=server, password=key):
            print('Inicialização falhou. Verifique sua conexão.')
            mt5.shutdown()
        else:
            print('MT5 inicializado com sucesso...')
    else:
        if not mt5.initialize(path=user_path, login=login, server=server, password=key):
            print('Inicialização falhou. Verifique sua conexão.')
            mt5.shutdown()
        else:
            print('MT5 inicializado com sucesso...')
            
            
def prepare_symbol(symbol):
    
    # preparamos a estrutura de solicitação para compra
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(symbol, 'not found, can not call order_check()')
    
    # se o símbolo não estiver disponível no MarketWatch, adicionamo-lo
    if not symbol_info.visible:
        print(symbol, 'is not visible, trying to switch on...')
        if not mt5.symbol_select(symbol,True):
            print('symbol_select({}}) failed, exit',symbol)
            
            
def remove_symbol(symbol):
    """ 
    Remove symbol from market watch
    """
    # Check if symbol is visible
    mt5.symbol_select(symbol, False)
        
            
def get_prices_mt5(symbol, n, timeframe):
    """ 
    Importação de dados do mt5 para símbolo escolhido
    """
    # Current date extract
    utc_from = datetime.now()
    
    try:
        # Import the data into a tuple
        rates = mt5.copy_rates_from(symbol, timeframe, utc_from, n)

        # Tuple to dataframe
        rates_frame = pd.DataFrame(rates)

        # Convert time in seconds into the datetime format
        rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')

        # Convert the column "time" in the right format
        rates_frame['time'] = pd.to_datetime(rates_frame['time'], format='%Y-%m-%d')

        # Set column time as the index of the dataframe
        rates_frame = rates_frame.set_index('time')
        
        # adaptar df
        rates_frame = rates_frame.rename(columns={'open': 'Abertura', 'high': 'Máxima', 'low': 'Mínima', 
                                                  'close': 'Fechamento', 'real_volume': 'Volume'})
    
    except Exception as e:
        print(e)
        print(f'Não foi possível pegar os preços de {symbol}')
        rates_frame = None
    
    return rates_frame
    

def trading_time(start_time_hour, finishing_time_hour, start_time_minutes, finishing_time_minutes):
    if int(start_time_hour) < datetime.now().hour < int(finishing_time_hour):
        return True
    elif datetime.now().hour == int(start_time_hour):
        if datetime.now().minute >= int(start_time_minutes):
            return True
    elif datetime.now().hour == int(finishing_time_hour):
        if datetime.now().minute < int(finishing_time_minutes):
            return True
    return False


def get_positions(asset):
    """ 
    Pegar posicoes abertas na conta
    """
    # obtemos as posições abertas com base no ativo selecionado
    positions = mt5.positions_get(symbol=asset)
    
    if positions == None:
        print("No positions on asset, error code={}".format(mt5.last_error()))
        return None
        
    elif len(positions)>0:
        print("Total positions on asset =",len(positions))
        # imprimimos todas as posições abertas
        for position in positions:
            print(position)
     
        # detalhamento da posicao aberta
        df=pd.DataFrame(list(positions),columns=positions[0]._asdict().keys())
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.drop(['time_update', 'time_msc', 'time_update_msc', 'external_id'], axis=1, inplace=True)

        return df


def request_result(symbol, price, lot, result):
    """
    Verificação de execução de ordem
    """

    print(f'Ordem enviada: {symbol}, {lot} lot(s), a {price}.')
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f'Algo deu errado ao tentar buscar o ret_code, error: {result.retcode}')

    # mostrar resultado
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        if len(mt5.positions_get(symbol=symbol)) == 1:
            order_type = 'Buy' if mt5.positions_get(symbol=symbol)[0].type == 0 else 'Sell'
            print(order_type, 'Posição aberta:', result.price)
        else:
            print(f'Posição fechada: {result.price}')

def order_open(symbol, lot=1.0, deviation=1, order_type=None):
    """ 
    Montar posicao no ativo selecionado
    """

    if order_type == 0: # buy
        o_type = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).ask
        if price < mt5.symbol_info_tick(symbol).ask:
            price = mt5.symbol_info_tick(symbol).ask
    
    if order_type == 1: # sell
        o_type = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).bid
        if price < mt5.symbol_info_tick(symbol).bid:
                price = mt5.symbol_info_tick(symbol).bid
        
    request = {
    'action': mt5.TRADE_ACTION_DEAL,
    'symbol': symbol,
    'volume': lot,
    'type': o_type,
    'price': price,
    'deviation': deviation,
    'magic': 1,
    'comment': 'shadow',
    'type_time': mt5.ORDER_TIME_GTC,
    'type_filling': mt5.ORDER_FILLING_RETURN,
    }  
   
     
    # enviamos a solicitação de negociação
    result = mt5.order_send(request)
    # verificamos o resultado da execução
    print('1. order_send(): by {} {} lots at {} with deviation = {} points'.format(symbol,lot,price,deviation));
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print('2. order_send failed, retcode={}'.format(result.retcode))
       # solicitamos o resultado na forma de dicionário e exibimos elemento por elemento
        result_dict=result._asdict()
        for field in result_dict.keys():
            print('   {} = {}'.format(field,result_dict[field]))
            #se esta for uma estrutura de uma solicitação de negociação, também a exibiremos elemento a elemento
            if field=='request':
                traderequest_dict=result_dict[field]._asdict()
                for tradereq_filed in traderequest_dict:
                    print('       traderequest: {} = {}'.format(tradereq_filed,traderequest_dict[tradereq_filed]))
    
    request_result(symbol, price, lot, result)
    
    return result
            

def order_close(symbol, result, lot=1.0, deviation=1, order_type=None):
    """ 
    Montar posicao no ativo selecionado
    """

    if order_type == 0: # buy
        o_type = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).ask
        if price < mt5.symbol_info_tick(symbol).ask:
            price = mt5.symbol_info_tick(symbol).ask
    
    if order_type == 1: # sell
        o_type = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).bid
        if price < mt5.symbol_info_tick(symbol).bid:
                price = mt5.symbol_info_tick(symbol).bid
                
    position_id = result.order
        
    request = {
    'action': mt5.TRADE_ACTION_DEAL,
    'symbol': symbol,
    'volume': lot,
    'type': o_type,
    'position': position_id,
    'price': price,
    'deviation': deviation,
    'magic': 1,
    'comment': 'shadow',
    'type_time': mt5.ORDER_TIME_GTC,
    'type_filling': mt5.ORDER_FILLING_RETURN,
    }  
   
     
    # enviamos a solicitação de negociação
    result = mt5.order_send(request)
    # verificamos o resultado da execução
    print('1. order_send(): by {} {} lots at {} with deviation = {} points'.format(symbol,lot,price,deviation));
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print('2. order_send failed, retcode={}'.format(result.retcode))
       # solicitamos o resultado na forma de dicionário e exibimos elemento por elemento
        result_dict=result._asdict()
        for field in result_dict.keys():
            print('   {} = {}'.format(field,result_dict[field]))
            #se esta for uma estrutura de uma solicitação de negociação, também a exibiremos elemento a elemento
            if field=='request':
                traderequest_dict=result_dict[field]._asdict()
                for tradereq_filed in traderequest_dict:
                    print('       traderequest: {} = {}'.format(tradereq_filed,traderequest_dict[tradereq_filed]))
    
    request_result(symbol, price, lot, result)

def account_info():
    account_info=mt5.account_info()
    if account_info!=None:
        # exibimos os dados sobre a conta de negociação como estão
        print(account_info)
        # exibimos os dados da conta de negociação como um dicionário
        print("Show account_info()._asdict():")
        account_info_dict = mt5.account_info()._asdict()
        for prop in account_info_dict:
            print("  {}={}".format(prop, account_info_dict[prop]))
        print()
 
       # convertemos o dicionário num DataFrame e imprimimos
        df = pd.DataFrame(list(account_info_dict.items()),columns=['property','value'])
        print("account_info() as dataframe:")
        print(df)
        
    else:
        print("failed to connect to trade account 25115284 with password=gqz0343lbdm, error code =",mt5.last_error())


def book_info(choose_asset):
    # subscreva para receber atualizações no livro de ofertas para o símbolo EURUSD (Depth of Market)
    if mt5.market_book_add(choose_asset):
      # obtemos 10 vezes em um loop os dados do livro de ofertas
       for i in range(10):
            # obtemos o conteúdo do livro de ofertas (Depth of Market)
            items = mt5.market_book_get(choose_asset)
            # exibimos todo o livro de ofertas como uma string tal qual como está
            print(items)
            # agora exibimos cada solicitação separadamente para maior clareza
            if items:
                for it in items:
                    # conteúdo da solicitação
                    print(it._asdict())
            # vamos fazer uma pausa de 5 segundos antes da próxima solicitação de dados do livro de ofertas
            time.sleep(5)
      # cancelamos a subscrição de atualizações no livro de ofertas (Depth of Market)
       mt5.market_book_release(choose_asset)
    else:
        print(f"mt5.market_book_add(choose_asset) failed, error code =",mt5.last_error())


def summary(symbol):
    print(
        f'Summary:\n'
        f'Running on symbol:               {symbol}\n')


def statistics(total_deals, profit_deals, loss_deals, balance, fee):
    print(f'Negocios: {total_deals}, {profit_deals} gain, {loss_deals} loss.')
    print(f'Balance: {balance}, fee: {total_deals * fee}, final balance:'
          f' {balance - (total_deals * fee)}.')
    if total_deals != 0:
        print(f'Accuracy: {round((profit_deals / total_deals) * 100, 2)}%.\n')
