from dotenv import load_dotenv
from pathlib import Path
import pandas as pd
import os
import requests
import matplotlib.pyplot as plt
from calc_psar import PSAR

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
SYMBOL = 'ETHUSDT'

def get_futures_klines(symbol, limit):
    x = requests.get(
        'https://www.binance.com/fapi/v1/klines?symbol=' + symbol + '&limit=' + str(limit) + '&interval=1m')
    df = pd.DataFrame(x.json())
    df.columns = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'd1', 'd2', 'd3', 'd4', 'd5']
    df = df.drop(['d1', 'd2', 'd3', 'd4', 'd5'], axis=1)
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    return df


def get_rsi(df):
    delta = df['close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=14, adjust=False).mean()
    ema_down = down.ewm(com=14, adjust=False).mean()
    rs = ema_up / ema_down
    rsi = 100 - (100 / (1 + rs))
    return rsi




def get_sar(df):
    indic = PSAR()
    df['PSAR'] = df.apply(
        lambda x: indic.calcPSAR(x['high'], x['low']), axis=1)
    # Add supporting data
    df['EP'] = indic.ep_list
    df['Trend'] = indic.trend_list
    df['AF'] = indic.af_list
    df.head()
    return df



df = get_futures_klines(SYMBOL, 100)
df['ema7'] = df['close'].ewm(span=7).mean()
print(df)
