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
SYMBOL = 'ETCUSDT'
client = Client(KEY, SECRET)


def get_symbol_price(symbol):
    prices = client.get_all_tickers()
    df = pd.DataFrame(prices)
    return float(df[df['symbol'] == symbol]['price'])


def get_wallet_balance():
    status = client.futures_account()
    balance = round(float(status['totalWalletBalance']), 2)
    return balance


current_price = get_symbol_price(SYMBOL)
balance = get_wallet_balance()
maxposition = round((balance * 0.1) / current_price, 2)
stop_percent = 0.008


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


def get_opened_positions(symbol):
    try:
        status = client.futures_account()
        positions = pd.DataFrame(status['positions'])
        a = positions[positions['symbol'] == symbol]['positionAmt'].astype(float).tolist()[0]
        leverage = int(positions[positions['symbol'] == symbol]['leverage'])
        entryprice = positions[positions['symbol'] == symbol]['entryPrice']
        profit = float(status['totalUnrealizedProfit'])
        balance = round(float(status['totalWalletBalance']), 2)
        if a > 0:
            pos = "long"
        elif a < 0:
            pos = "short"
        else:
            pos = ""
        return [pos, a, profit, leverage, balance, round(float(entryprice), 3), 0]
    except Exception as e:
        print(f'Ошибка при получении данных по открытой позиции: \n{e}')


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


def open_position(symbol, s_l, quantity_l):
    try:
        sprice = get_symbol_price(symbol)

        if s_l == 'long':
            close_price = str(round(sprice * (1 + stop_percent), 2))
            params = {
                "batchOrders": [
                    {
                        "symbol": symbol,
                        "side": "BUY",
                        "type": "LIMIT",
                        "quantity": str(quantity_l),
                        "timeInForce": "GTC",
                        "price": close_price

                    }
                ]
            }
            response = send_signed_request('POST', '/fapi/v1/batchOrders', params)
            print(response)

        if s_l == 'short':
            close_price = str(round(sprice * (1 - stop_percent), 2))
            params = {
                "batchOrders": [
                    {
                        "symbol": symbol,
                        "side": "SELL",
                        "type": "LIMIT",
                        "quantity": str(quantity_l),
                        "timeInForce": "GTC",
                        "price": close_price
                    }
                ]
            }
            response = send_signed_request('POST', '/fapi/v1/batchOrders', params)
            print(response)
    except Exception as e:
        print(f'Ошибка открытия позиции: \n{e}')


# функция закрытия позиции принимает название валюты, тип сделки (short/long) и сумму ставки,
# собирает параметры и отправляет POST-запрос с параметрами для закрытия позиции на /fapi/v1/order
# https://binance-docs.github.io/apidocs/futures/en/#cancel-order-trade

def close_position(symbol, s_l, quantity_l):
    try:
        sprice = get_symbol_price(symbol)

        if s_l == 'long':
            close_price = str(round(sprice * (1 - stop_percent), 2))
            params = {
                "symbol": symbol,
                "side": "SELL",
                "type": "LIMIT",
                "quantity": str(quantity_l),
                "timeInForce": "GTC",
                "price": close_price
            }
            response = send_signed_request('POST', '/fapi/v1/order', params)
            print(response)

        if s_l == 'short':
            close_price = str(round(sprice * (1 + stop_percent), 2))
            params = {

                "symbol": symbol,
                "side": "BUY",
                "type": "LIMIT",
                "quantity": str(quantity_l),
                "timeInForce": "GTC",
                "price": close_price
            }
            response = send_signed_request('POST', '/fapi/v1/order', params)
            print(response)
    except Exception as e:
        print(f'Ошибка закрытия позиции: \n{e}')


ohlc = get_futures_klines(SYMBOL, 100)
prepared_df = PrepareDF(ohlc)
mean_atr = prepared_df['ATR'].mean()
res_open = open_position(SYMBOL, 'long', maxposition)
res_close = close_position(SYMBOL, 'long', maxposition)
print(res_close)
