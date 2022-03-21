import requests
import numpy as np
import pandas as pd
import statsmodels.api as sm
import copy
import time
import datetime
import random
from dotenv import load_dotenv
from pathlib import Path
import os

from binance import Client, ThreadedWebsocketManager, ThreadedDepthCacheManager
from futures_sign import send_signed_request, send_public_request

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
SECRET = os.getenv("SECRET")
SYMBOL = 'ETHUSDT'
client = Client(KEY, SECRET)


def get_futures_klines(symbol, limit=500):
    try:
        x = requests.get(
            'https://binance.com/fapi/v1/klines?symbol=' + symbol + '&limit=' + str(limit) + '&interval=5m')
        df = pd.DataFrame(x.json())
        df.columns = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'd1', 'd2', 'd3', 'd4', 'd5']
        df = df.drop(['d1', 'd2', 'd3', 'd4', 'd5'], axis=1)
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        return df
    except Exception as e:
        print(f'Ошибка при получении истории последних свечей: \n{e}')


def indSlope(series, n):
    array_sl = [j * 0 for j in range(n - 1)]

    for j in range(n, len(series) + 1):
        y = series[j - n:j]  # итоговые значения первых n свечей
        x = np.array(range(n))  # массив [1, 2, 3, ... n-1]
        x_sc = (x - x.min()) / (x.max() - x.min())
        y_sc = (y - y.min()) / (y.max() - y.min())
        x_sc = sm.add_constant(x_sc)
        model = sm.OLS(y_sc, x_sc)
        results = model.fit()
        array_sl.append(results.params[-1])
    slope_angle = (np.rad2deg(np.arctan(np.array(array_sl))))
    return np.array(slope_angle)


def indATR(source_DF, n):
    df = source_DF.copy()
    df['H-L'] = abs(df['high'] - df['low'])
    df['H-PC'] = abs(df['high'] - df['close'].shift(1))
    df['L-PC'] = abs(df['low'] - df['close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1, skipna=False)
    df['ATR'] = df['TR'].rolling(n).mean()
    df_temp = df.drop(['H-L', 'H-PC', 'L-PC'], axis=1)
    return df_temp


def PrepareDF(DF):
    ohlc = DF.iloc[:, [0, 1, 2, 3, 4, 5]]
    ohlc.columns = ["date", "open", "high", "low", "close", "volume"]
    ohlc = ohlc.set_index('date')
    df = indATR(ohlc, 14).reset_index()  # считаем ATR по последним 14 свечам
    df['slope'] = indSlope(df['close'], 5)  # считаем угол наклона
    df['channel_max'] = df['high'].rolling(10).max()  # считаем верхнюю границу канала
    df['channel_min'] = df['low'].rolling(10).min()  # считаем нижнюю границу канала
    df['position_in_channel'] = (df['close'] - df['channel_min']) / (
                df['channel_max'] - df['channel_min'])  # считаем позицию в канале
    df = df.set_index('date')
    df = df.reset_index()
    return df

ohlc = get_futures_klines(SYMBOL, 1000)
prepared_df = PrepareDF(ohlc)
mean_atr = prepared_df['ATR'].mean()
print(mean_atr)
