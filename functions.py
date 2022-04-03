import requests
import numpy as np
import pandas as pd
import statsmodels.api as sm
import time
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
client = Client(KEY, SECRET)


# функция получает на вход название валюты, возвращает её текущую стоимость
# client.get_all_tickers() - получить информацию о монетах (доступных для ввода и вывода) для пользователя
def get_symbol_price(symbol):
    prices = client.get_all_tickers()
    df = pd.DataFrame(prices)
    return float(df[df['symbol'] == symbol]['price'])


def get_wallet_balance():
    status = client.futures_account()
    balance = round(float(status['totalWalletBalance']), 2)
    return balance


# функция запрашивает с площадки последние 500 свечей по пять минут и возвращает датафрейм с нужными столбцами

def get_futures_klines(symbol, limit, pointer):
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
        prt(f'Ошибка при получении истории последних свечей: \n{e}', pointer)


# функция открытия позиции принимает название валюты, тип сделки (short/long) и сумму ставки,
# собирает параметры и отправляет POST запрос с параметрами для открытия позиции на /fapi/v1/batchOrders
# close_price - берет текущую цену + 1%. Зачем нужен?
# batchOrders — список параметров заказа в формате JSON. https://binance-docs.github.io/apidocs/futures/en/#place-multiple-orders-trade

def open_position(symbol, s_l, quantity_l, stop_percent, round_n, pointer):
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
        prt(f'Ошибка открытия позиции: \n{e}', pointer)


# функция закрытия позиции принимает название валюты, тип сделки (short/long) и сумму ставки,
# собирает параметры и отправляет POST-запрос с параметрами для закрытия позиции на /fapi/v1/order
# https://binance-docs.github.io/apidocs/futures/en/#cancel-order-trade

def close_position(symbol, s_l, quantity_l, stop_percent, round_n, pointer):
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
        prt(f'Ошибка закрытия позиции: \n{e}', pointer)


def get_opened_positions(symbol, pointer):
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
        prt(f'Ошибка при получении данных по открытой позиции: \n{e}', pointer)


# Close all orders

def check_and_close_orders(symbol):
    a = client.futures_get_open_orders(symbol=symbol)
    if len(a) > 0:
        client.futures_cancel_all_open_orders(symbol=symbol)


# INDICATORS


# функция принимает итоговые значения свечей и количество свечей по которым будет считать угол наклона
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


# True Range and Average True Range indicator
# функция получает на вход df с данными последних n свечек, и считает TR и ATR
# TR - истинный диапазон, ATR - средний истинный диапазон, инфо - https://bcs-express.ru/novosti-i-analitika/indikator-average-true-range-opredeliaem-volatil-nost
# ATR находится на низких значениях, когда на рынке затишье и формируется боковик. После продолжительного боковика
# можно ожидать появление мощного тренда (нисходящего или восходящего). Тогда индикатор начинает расти, свидетельствуя о росте волатильности.
def indATR(source_DF, n):
    df = source_DF.copy()
    df['H-L'] = abs(df['high'] - df['low'])
    df['H-PC'] = abs(df['high'] - df['close'].shift(1))
    df['L-PC'] = abs(df['low'] - df['close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1, skipna=False)
    df['ATR'] = df['TR'].rolling(n).mean()
    df_temp = df.drop(['H-L', 'H-PC', 'L-PC'], axis=1)
    return df_temp


# find local mimimum / local maximum

def isLCC(DF, i):
    df = DF.copy()
    LCC = 0
    if df['close'][i - 1] >= df['close'][i] <= df['close'][i + 1] and df['close'][i + 1] > df['close'][i - 1]:
        # найдено Дно
        LCC = i - 1
    return LCC


def isHCC(DF, i):
    df = DF.copy()
    HCC = 0
    if df['close'][i - 1] <= df['close'][i] >= df['close'][i + 1] and df['close'][i + 1] < df['close'][i - 1]:
        # найдена вершина
        HCC = i
    return HCC


def getMaxMinChannel(DF, n):
    maxx = 0
    minn = DF['low'].max()
    for i in range(1, n):
        if maxx < DF['high'][len(DF) - i]:
            maxx = DF['high'][len(DF) - i]
        if minn > DF['low'][len(DF) - i]:
            minn = DF['low'][len(DF) - i]
    return maxx, minn


# generate data frame with all needed data

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


# функция проверяет локальный минимум/максимум, близость к краю канала и текущий угол наклона тренда и возвращает
# long, short или ''
def check_if_signal(symbol, POS_IN_CHANNEL_L, POS_IN_CHANNEL_S, SLOPE_L, SLOPE_S, klines, atr, pointer):
    try:
        ohlc = get_futures_klines(symbol, 100, pointer)
        prepared_df = PrepareDF(ohlc)
        mean_atr = prepared_df[80:95]['ATR'].mean()
        delta = prepared_df['close'][0] - prepared_df['close'][klines]
        signal = ""  # return value

        i = 98  # 99 - текущая незакрытая свечка, 98 - последняя закрытая свечка, нужно проверить 97-ю росла она или падала

        if isLCC(prepared_df, i - 1) > 0 and prepared_df['close'][0] * round(klines/10000, 3) >= delta:
            # found bottom - OPEN LONG
            if prepared_df['position_in_channel'][i - 1] < POS_IN_CHANNEL_L and prepared_df['slope'][i - 1] < -SLOPE_L and mean_atr < atr:
                # found a good enter point for LONG
                signal = 'long'

        if isHCC(prepared_df, i - 1) > 0 and delta >= prepared_df['close'][0] * -round(klines/10000, 3):
            # found top - OPEN SHORT
            if prepared_df['position_in_channel'][i - 1] > POS_IN_CHANNEL_S and prepared_df['slope'][i - 1] > SLOPE_S and mean_atr < atr:
                # found a good enter point for SHORT
                signal = 'short'

        return signal
    except Exception as e:
        prt(f'Ошибка в функции проверки сигнала: \n{e}', pointer)


telegram_delay = 12
bot_token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("CHAT_ID")


def getTPSLfrom_telegram(SYMBOL, stop_percent, round_n, pointer):
    try:
        strr = 'https://api.telegram.org/bot' + bot_token + '/getUpdates'
        response = requests.get(strr)
        rs = response.json()
        if len(rs['result']) > 0:
            rs2 = rs['result'][-1]
            rs3 = rs2['message']
            textt = rs3['text']
            datet = rs3['date']

            if (time.time() - datet) < telegram_delay:
                if 'quit' in textt:
                    prt('Завершение работы скрипта', pointer)
                    quit()
                if 'exit' in textt:
                    prt('Завершение работы скрипта', pointer)
                    exit()
                if 'hello' in textt:
                    telegram_bot_sendtext('Hello. How are you?')
                if 'close_pos' in textt:
                    position = get_opened_positions(SYMBOL, pointer)
                    open_sl = position[0]
                    quantity = position[1]
                    close_position(SYMBOL, open_sl, abs(quantity), stop_percent, round_n, pointer)
                    prt('Позиция закрыта в ручном режиме', pointer)
    except Exception as e:
        print(f'Ошибка подключения к телеграм: \n{e}')


def telegram_bot_sendtext(bot_message):
    try:
        bot_token2 = bot_token
        bot_chatID = chat_id
        send_text = 'https://api.telegram.org/bot' + bot_token2 + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
        response = requests.get(send_text)
        return response.json()
    except Exception as e:
        print(f'Ошибка отправки сообщения в телеграм: \n{e}')


def prt(message, pointer):
    # telegram message
    telegram_bot_sendtext(pointer + ': ' + message)
    print(pointer + ': ' + message)
