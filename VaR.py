# importacao de bibliotecas
import sys
import time
import json
import boto3
import numpy as np
import pandas as pd
import pickle as pkl
import yfinance as yf
from tqdm import tqdm
from pathlib import Path
from arch import arch_model
from datetime import datetime
import matplotlib.pyplot as plt
from scipy.stats import norm, t
from scipy.stats import genextreme


def sys_path(choose_path):
    sys.path.append(str(choose_path))

home = Path.home()
main_path = Path(home, 'Documents/GitHub/avaloncapital')
factors_path = Path(home, 'Documents/GitHub/avaloncapital/strategies/factors')
database_path = Path(home, 'Documents/GitHub/avaloncapital/database')
backtest_path = Path(home, 'Documents/GitHub/avaloncapital/backtesting')
reports_path = Path(home, 'Documents/GitHub/avaloncapital/reports')
path_list = [main_path, factors_path, database_path, backtest_path, reports_path]

if str(main_path) not in sys.path:
    for path in path_list:
        sys_path(path)


class VarAssets():

    def __init__(self, list_assets: list,
                 init_date: datetime, 
                 end_date: datetime,  
                 period: str = 'D',
                 asset: bool = True, 
                 alpha: int = 5,
                 initial_value: float = 1.,
                 time: int = 10):
      
        self.list_assets = list_assets
        self.init_date = init_date
        self.end_date = end_date
        self.alpha = alpha
        self.period = period
        self.asset = asset
        self.initial_value = initial_value
        self.time = time
    
    
    def assets_prices(self) -> pd.DataFrame:
        """
        Precos dos ativos selecionados
        """
      
        # captura de precos de ativos
        df_assets = pd.DataFrame()
        for asset in self.list_assets:
          # condicao para captura de dados de ativos ou indices
          if self.asset == True:
            asset_id = yf.Ticker(asset + '.SA')
          else: 
            asset_id = yf.Ticker(asset)
      
          # dados de fechamento
          df = asset_id.history(start=self.init_date, end=self.end_date)
          df = df["Close"].to_frame()
          df_assets[asset] = df
      
        return df_assets
    
    
    def assets_returns(self, data: pd.DataFrame = None, direct=False) -> pd.DataFrame:
        """
        Retornos dos ativos selecionados
      
        Params
        ------
        direct: caso True, roda direto asset_prices
        """
      
        if direct == True:
            # captura de precos de ativos
            data = self.assets_prices()
        else:
            assert (isinstance(data, pd.DataFrame)), "Necessário inserir um dataframe..."
      
        # adaptacao de periodo selecionado (diario, mensal, anual)
        if self.period == 'D':
            returns = data
        elif self.period == 'M':
            returns = data.resample('M').apply(lambda x: x.last('D'))
        elif self.period == 'Y':
            returns = data.resample('Y').apply(lambda x: x.last('D'))
        else:
            raise NameError('Período incorreto...')
        
        # avaliacao de integridade do df
        assert (returns.shape[0] > 3), 'O período selecionado gerou um df muito curto.'
      
        # retornos
        return np.log(returns/returns.shift(1)).dropna()
    
    
    def var_param(self, df_returns, dist='normal', dof=6, vol_setup='ewma', decay_factor=0.94) -> float:
        """
        VaR parametrico individual
        
        Riskmetrics: https://www.msci.com/documents/10199/5915b101-4206-4ba0-aee2-3449d5c7e95a
        O sistema implementado mais conhecido e o publicado no RiskMetrics, 
        desenvolvido pelo JP Morgan e publicado em 1993. O JP Morgan construiu sua metodologia 
        parametrica de calculo para o VaR sob a pressuposicao de uma distribuicao normal de retornos.
        Nos calculos da referida instituicao (que se vale do desvio padrao e media dos retornos, 
        alem do z-score) para estimar volatilidade, o JP Morgan se valeu de uma media movel 
        exponencial ponderada.
      
        Params
        ------
        df_returns: dataframe com retornos do ativo ou carteira
        dist: tipo de distribuicao normal ou t-Student
        dof: graus de liberdade (apenas para T de Student)
        vol_setup: ewma ou garch
      
        Returns
        -------
        riskmetrics: estimativa de VaR pelo modelo do RiskMetrics (JP Morgan)
        economtr: modelo econometrico para series temporais
        """
      
        # retorno medio
        # mu = df_returns.mean()
      
        if dist == 'normal':
            
            if vol_setup == 'ewma':
                df_returns['r2'] = df_returns **2
                
                decay_f = np.arange(df_returns.shape[0], 0, -1)
                decay_f = decay_factor ** decay_f
                decay_sum = sum(decay_f)
                w = decay_f / decay_sum
                
                df_returns['w'] = w
                ewma = np.sum(df_returns['r2'] * df_returns['w'])
                vol = np.sqrt(ewma)
            
            elif vol_setup == 'garch':
                vol = df_returns.iloc[-1]
                
            else:
                vol = df_returns.std(ddof=0)
    
            # VaR parametrico para distribuicao normal
            z = round(norm.ppf(1-self.alpha/100),2)
            riskmetrics = z * vol * np.sqrt(self.time)
      
        elif dist == 't':
            # VaR parametrico para distribuicao T de Student
            riskmetrics = np.sqrt((dof-2)/dof) * t.ppf(1-self.alpha/100, dof) * vol * np.sqrt(self.time) 
      
        else:
            raise TypeError("Espera-se que a distribuição selecionada seja 'normal' ou 't'")
      
        return riskmetrics
    
    
    def var_param_port(self, mean_return, std):
        """
        VaR parametrico para carteiras
        """
        raise NotImplementedError()
    
    
    def var_hist(self, df_returns, alpha=None) -> float:
        """
        VaR historico
      
        Params
        ------
        df_returns: dataframe com retornos do ativo ou carteira
        alpha: cutoff para os retornos
        method: simple, exp
        
        Returns
        -------
        float com var historico
        """
      
        if isinstance(df_returns, pd.DataFrame):
            # aplicacao de funcao para cada coluna
            hvar = df_returns.aggregate(self.var_hist, alpha=self.alpha)
      
        elif isinstance(df_returns, pd.Series):
            hvar = -np.percentile(df_returns, self.alpha) * np.sqrt(self.time)
      
        else:
            raise TypeError('var_hist: Input deve ser uma série ou dataframe.')
        
        return hvar 
    
    
    def var_hist_bootstrap(self, df_returns, size=5_000) -> float:
        """
        VaR historico com bootstrap
        
        Params
        ------
        df_returns: dataframe com retornos do ativo ou carteira
        size: simulacoes
        
        Returns
        -------
        float com var historico
        """
      
        if isinstance(df_returns, pd.DataFrame):
            bvar = df_returns.aggregate(self.var_hist_bootstrap)
        
        elif isinstance(df_returns, pd.Series):
            bs_handle = np.empty(size)
            for i in tqdm(range(size)):
              # array de dados aleatorios com base nos retornos reais
              sample = np.random.choice(np.array(df_returns).flatten(), df_returns.shape[0])
              # VaR (n-size) das amostras aleatorias
              bs_handle[i] = self.var_hist(pd.DataFrame(sample), self.alpha)
              # media dos resultados de VaR
              bvar = np.mean(bs_handle)
        
        else:
            raise TypeError('var_hist_bootstrap: Input deve ser uma série ou dataframe.')
      
        return bvar
    
        
    def var_montecarlo(self, df_returns, n_sims=10000):
        """
        VaR via simulacao de Monte Carlo
        
        Params
        ------
        df_returns: dataframe com retornos do ativo ou carteira
        n_sims: simulacoes
        
        Returns
        -------
        float com var parametrico utilizando simulacao de Monte Carlo
        """
        
        # retorno medio
        mu = df_returns.mean()
        vol = df_returns.std(ddof=0)
        T = df_returns.shape[0]
        
        # simulacoes
        np.random.seed(42)
        ret_mc = np.random.normal(loc=mu, scale=vol, size=n_sims)

        mc_var = self.var_hist(pd.DataFrame(ret_mc), self.alpha)
        
        return mc_var
    

    @classmethod
    def garch_model(cls, returns, p=1, q=1, mean='constant', model='GARCH', dist_form='normal'):
        am = arch_model(returns * 100, p=p, q=q, mean=mean, vol=model, dist=dist_form)
        res = am.fit(disp='off')
        
        vol_garch = res.conditional_volatility / 100
        vol_adj = vol_garch.apply(lambda x: vol_garch[-1]/x)
        
        adj_returns = pd.DataFrame(returns.values * vol_adj.values.reshape(returns.shape[0],1), 
                           columns=returns.columns, index=returns.index)
        
        return adj_returns
    
    
    def var_garch(self, df_returns, dist='normal', dof=6) -> float:
        """
        VaR parametrico com GARCH
        Nesse modelo, cada retorno e multiplicado pela estimativa de volatilidade 
        mais recente e dividido pela estimativa de volatilidade a partir do momento desse retorno. 
        Portanto, se a volatilidade agora for maior do que a volatilidade no passado, esse retorno 
        sera maior (ou menor, se for negativo) para alinha-lo com a volatilidade de hoje. 
        
        O que estamos tentando fazer nesse caso e impor as condições de mercado de hoje 
        sobre os retornos de ontem. A diferenca para o modelo de VaR parametrico e que naquele caso,
        a medicao de volatilidade pelo desvio e incondicionada. No VaR via GARCH a medicao de volatilidade
        e condicionada, isto e, a volatilidade de hoje, dada a volatilidade de ontem.
        
        Params
        ------
        df_returns: dataframe com retornos do ativo ou carteira
        dist_form: tipo de distribuicao normal ou t-Student
        dof: graus de liberdade (apenas para T de Student)
        
        Returns
        -------
        float com var parametrico utilizando GARCH
        """
        
        r = VarAssets.garch_model(df_returns)
        g_var = self.var_param(r, dist=dist, dof=dof, vol_setup='garch')

        return g_var

    
    def var_filtered_historical(self, df_returns) -> float:
        """
        VaR semiparametrico, por simulacao historica filtrada
        Esse e um modelo que resulta da combinação do metodo bootstrap 
        com um processo de modelo GARCH que captura a volatilidade condicional 
        com a maior precisao possivel
        
        Params
        ------
        df_returns: dataframe com retornos do ativo ou carteira
        
        Returns
        -------
        float com var parametrico utilizando modelo de simulacao historica filtrada
        """

        returns = self.garch_model(df_returns)
        var_fhist = self.var_hist_bootstrap(returns, size=5_000)
        
        return var_fhist
    
    
    def var_extreme_value(self, df_returns, ex_filter=-0.05, var_compute=0.95) -> float:
        """
        VaR semiparametrico, via teoria do valor extremo
        A Teoria dos Valores Extremos vem sendo utilizada para a analise de eventos raros. 
        Ela estuda o comportamento de maximos, minimos e outras estatisticas de ordem de 
        sequencias de variaveis aleatorias independentes e identicamente distribuidas 
        
        Params
        ------
        df_returns: dataframe com retornos do ativo ou carteira
        ex_filter: percentual de perda extrema
        var_compute: percentual do VaR
        
        Returns
        -------
        float com var semiparametrico utilizando modelo de teoria do valor extremo
        """
        
        loss = df_returns[df_returns < ex_filter]
        loss.dropna(inplace=True)
        
        p = genextreme.fit(loss)
        var_extr = genextreme.ppf(var_compute, *p)
        
        return var_extr
    
    
    
class VarPortfolio(VarAssets):

    def __init__(self, list_assets: list,
                 init_date: datetime, 
                 end_date: datetime,  
                 period: str = 'D',
                 asset: bool = True, 
                 alpha: int = 5,
                 initial_value: int = 1,
                 time: int = 1,
                 weights: list = None):
      
        super(VarPortfolio, self).__init__(list_assets,
                                           init_date, 
                                           end_date,  
                                           period,
                                           asset, 
                                           alpha,
                                           initial_value,
                                           time)
        self.weights = weights
      
        # preparo
        self.returns = self.assets_returns(direct=True)
        # retornos medios
        self.mean_returns = self.returns.mean()
        # matriz de covariancia
        self.cov_matrix = self.returns.cov()
    
    
    def portfolio_performance(self):
      
        if not isinstance(self.weights, list):
          # pesos aleatorios para os ativos, caso nao haja input do usuario
          w = np.random.random(len(self.returns.columns))
          w /= np.sum(w)
        else:
          w = np.array(self.weights)
        
        # df de retornos ponderados
        port_returns = np.sum(self.returns * w, axis=1)
        # media ponderada dos retornos
        port_mean_return = np.sum(self.mean_returns * w)
        # desvio padrao da carteira
        port_std = np.sqrt(np.dot(w.T, np.dot(self.cov_matrix, w)))
      
        return round(port_returns,4), round(port_mean_return,4), round(port_std,4)
    
    
    def var_param_port(self, mean_return, std, dist='normal', dof=6):
        """
        VaR parametrico para carteiras
        """
      
        if dist == 'normal':
          # VaR parametrico para distribuicao normal
          z = round(norm.ppf(1-self.alpha/100),2) 
          return (z * std - mean_return) * np.sqrt(self.time) 
        
        elif dist == 't':
          return (np.sqrt((dof-2)/dof) * t.ppf(1-self.alpha/100, dof) * std - mean_return) * np.sqrt(time)
      
        else:
          raise TypeError("Espera-se que a distribuição selecionada seja 'normal' ou 't'")
     

if __name__ == '__main__':
 
    # returns = pkl.load(open(Path(database_path, 'risco', 'factors.pkl'), 'rb'))
    # returns = returns.final_return
    
    def save_file(path, content):
        with open (path, 'wb') as f:
            for chunk in content.iter_chunks(chunk_size=4096):
                f.write(chunk)
    
    # Read the secret.json file
    f = open(Path(Path.home(), 'Desktop', 'AT', 'secret.json'))
    data = json.load(f)
    
    # Create a connection to the AWS service using the access key ID and secret access key
    client = boto3.client('s3', aws_access_key_id = data['access_key'], aws_secret_access_key = data['secret_key'])
    
    # List all the buckets
    response = client.list_objects_v2(Bucket='m2xdb')
    for bucket in response['Contents']:
        r = client.get_object(Bucket='m2xdb', Key='stock_origin.pkl')
    
    # Download a file from the bucket
    local_file = str(Path(database_path, 'prices'))
    file_name = 'stock_origin.pkl'
    
    save_file(Path(local_file, file_name), r['Body'])
    
    # abrir pickle
    assets_dict = pkl.load(open(Path(local_file, file_name), 'rb'))
    prices = pd.DataFrame({k: v.Fechamento for (k,v) in assets_dict.items()}, columns=assets_dict.keys())
    returns = prices.pct_change()
    
    # inputs
    assets_list = ['EGIE3', 'TAEE11', 'VIVT3', 'TIMS3', 'KLBN11',
                   'ENBR3', 'ITSA4', 'RADL3', 'EQTL3', 'ENGI11',
                   'SUZB3', 'SLCE3', 'CPFE3', 'ITUB4', 'HYPE3',
                   'WEGE3', 'JBSS3', 'BRAP4', 'GOAU4', 'SANB11',
                   'ELET6', 'CMIG4', 'CCRO3', 'ENEV3']
    
    time_ahead = input('Horizonte de tempo: ')
    data = VarAssets(assets_list, datetime(2022, 3, 9), datetime(2023, 3, 9), time=int(time_ahead))
    
    # dataframe
    VaR = pd.DataFrame()
    
    var_p = data.var_param(returns, vol_setup=None)
    VaR.loc[0, 'param'] = round(var_p,5) * 100
    
    var_h = data.var_hist(returns.dropna(axis=0))
    VaR.loc[0, 'hist'] = round(var_h,5) * 100
    
    r = []
    for i in returns.columns:
      var_mc = data.var_montecarlo(returns[i])
      r.append(list(round(var_mc,4))[0])
    
    
    # var mc
    # var_mc = data.var_montecarlo(returns.dropna(axis=0))
    # VaR.loc[0, 'mc'] = round(list(var_mc)[0],5) * 100
    
    # VaR por simulação histórico filtrada
    # var_g = data.var_filtered_historical(pd.DataFrame(returns))
    # VaR.loc[0, 'shf'] = round(list(var_g)[0],5) * 100
    
    VaR = VaR.T
    VaR.columns = ['VaR']
    
    print(VaR)
    
    
    
    
    
    
    
