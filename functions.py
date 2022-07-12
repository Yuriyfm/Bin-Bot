import requests
import pandas as pd
import time
from dotenv import load_dotenv
from pathlib import Path
import os
from binance import Client
from futures_sign import send_signed_request
from indicators import get_atr, get_slope, get_rsi, get_bollinger_bands, ao, get_sma, get_sma_slope
import numpy as np
import datetime as dt
import random

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
SECRET = os.getenv("SECRET")
client = Client(KEY, SECRET)


# функция получает на вход название валюты, возвращает её текущую стоимость
# client.get_all_tickers() - получить информацию о монетах (доступных для ввода и вывода) для пользователя
def get_symbol_price(symbol):
    response = requests.get(f'https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}')
    if response.status_code == 200:
        x = response.json()
        current_price = float(x['price'])
        return current_price


def get_wallet_balance():
    status = client.futures_account()
    balance = round(float(status['totalWalletBalance']), 2)
    return balance


# функция запрашивает с площадки последние 500 свечей по пять минут и возвращает датафрейм с нужными столбцами
def get_futures_klines(symbol, limit, pointer, time_frame):
    try:
        x = requests.get(
            f'https://www.binance.com/fapi/v1/klines?symbol={symbol}&limit={limit}&interval={time_frame}m')
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


def check_if_signal(SYMBOL, pointer, KLINES, DEAL):
    try:
        df = get_futures_klines(SYMBOL, KLINES, pointer, 1)
        df = prepareDF(df)
        df = get_rsi(df)
        df = get_bollinger_bands(df)

        signal = ""  # return value
        i = KLINES - 1

        # if df['close'][i - 2] < df['lower_band'][i - 2] and df['close'][i - 1] > df['lower_band'][i - 1] and \
        #         df['RSI'][i - 2] < 32 and df['ATR'][i] > 1.5:
        #     signal = 'long'
        #

        if df['close'][i - 2] > df['upper_band'][i - 2] and df['close'][i - 1] < df['upper_band'][i - 1]:
            if df['RSI'][i - 2] > 70 > df['RSI'][i - 1]:
                prt('сигнал на short', pointer)
                return 'short'

        if df['close'][i - 1] < df['upper_band'][i - 1]:
            prt('ниже линии Боллинджера, не совпали условия', pointer)
            return 'restart'

        # if signal == 'long':
        #     DEAL['close i-2'] = df['close'][i - 2]
        #     DEAL['close i-1'] = df['close'][i - 1]
        #     DEAL['close i'] = df['close'][i]
        #     DEAL['lower_band i-2'] = df['lower_band'][i - 2]
        #     DEAL['lower_band i-1'] = df['lower_band'][i - 1]
        #     DEAL['upper_band i-2'] = df['upper_band'][i - 2]
        #     DEAL['upper_band i-1'] = df['upper_band'][i - 1]
        #     DEAL['RSI i-1'] = df['RSI'][i - 1]
        #     DEAL['RSI i-2'] = df['RSI'][i - 2]
        return signal

    except Exception as e:
        prt(f'Ошибка в функции проверки сигнала: \n{e}', pointer)


def check_stop_price(SYMBOL, KLINES, pointer, deal_type):
    ohlc = get_futures_klines(SYMBOL, KLINES, pointer, 1)
    df = prepareDF(ohlc)
    df['ao'] = ao(df['close'], 5, 34)
    stop_long = df['ao'][96] < df['ao'][97] > df['ao'][98]
    stop_short = df['ao'][96] > df['ao'][97] < df['ao'][98]
    if deal_type == 'long':
        return stop_long
    else:
        return stop_short


# функция открытия позиции принимает название валюты, тип сделки (short/long) и сумму ставки,
# собирает параметры и отправляет POST запрос с параметрами для открытия позиции на /fapi/v1/batchOrders
# close_price - берет текущую цену + 1%. Зачем нужен?
# batchOrders — список параметров заказа в формате JSON. https://binance-docs.github.io/apidocs/futures/en/#place-multiple-orders-trade
def open_position(symbol, s_l, quantity_l, stop_percent, round_n, pointer):
    try:
        sprice = get_symbol_price(symbol)

        if s_l == 'long':
            close_price = str(round(sprice * (1 + stop_percent), round_n))
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

def close_position(symbol, s_l, quantity_l, stop_percent, pointer):
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


# generate data frame with all needed data
def prepareDF(DF):
    df = DF.iloc[:, [0, 1, 2, 3, 4, 5]]
    df.columns = ["date", "open", "high", "low", "close", "volume"]
    df = df.set_index('date')
    df = df.reset_index()
    return df


def get_current_atr(symbol, pointer):
    df = get_futures_klines(symbol, 13, pointer, 1)
    df = prepareDF(df)
    df = get_atr(df, 12)
    cur_atr = df['ATR'][12]
    return cur_atr


telegram_delay = 12
bot_token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("CHAT_ID")


def getTPSLfrom_telegram(pointer):
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
                # if 'close_pos' in textt:
                #     position = get_opened_positions(SYMBOL, pointer)
                #     open_sl = position[0]
                #     quantity = position[1]
                #     close_position(SYMBOL, open_sl, abs(quantity), stop_percent, 3, pointer)
                #     prt('Позиция закрыта в ручном режиме', pointer)
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


def parce_val():
    x = requests.get('https://fapi.binance.com/fapi/v1/ticker/price')
    val_json = x.json()
    work_list = []
    for item in val_json:
        if 'USDT' in item['symbol']:
            work_list.append(item['symbol'])
    time.sleep(1)
    return work_list


def get_last_intersection(DF, SMA_1, SMA_2):
    ints_list = 0
    trend = ''
    for i in range(SMA_2, len(DF)):
        prev_delta_sma = DF[f'SMA_{SMA_1}'][i - 2] < DF[f'SMA_{SMA_2}'][i - 2]
        cur_delta_sma = DF[f'SMA_{SMA_1}'][i - 1] > DF[f'SMA_{SMA_2}'][i - 1]

        if prev_delta_sma and cur_delta_sma:
            trend = 'long'
            ints_list = i
        elif not prev_delta_sma and not cur_delta_sma:
            trend = 'short'
            ints_list = i

    return trend, len(DF) - ints_list, DF['open'][ints_list]


def check_diff(pointer, SMA_1, SMA_2):
        symbol_list = parce_val()
        while True:
            for i in symbol_list:
                try:
                    DF = get_futures_klines(i, 100, pointer, 1)
                    DF = prepareDF(DF)
                    DF[f'SMA_{SMA_1}'] = get_sma(DF['close'], SMA_1)
                    DF[f'SMA_{SMA_2}'] = get_sma(DF['close'], SMA_2)
                    DF = get_rsi(DF)
                    DF = get_bollinger_bands(DF)
                    res = get_last_intersection(DF, SMA_1, SMA_2)
                    print(i)
                    if res[0] == 'long':
                        cur_price = get_symbol_price(i)
                        if 1 - (res[2] / cur_price) >= 0.03 and DF['RSI'][99] > 70 and DF['close'][99] > DF['upper_band'][99]:
                            prt(f'выбрал валюту {i}', pointer)
                            print(f'выбрал валюту {i}')
                            return i
                except Exception as e:
                    prt(f'Ошибка в функции выбора валюты: \n{e}', pointer)
                    print(f'Ошибка в функции выбора валюты: \n{e}')
            prt('нет подходящих валют', pointer)



def parce_tick_size():
    x = requests.get(f'https://fapi.binance.com/fapi/v1/exchangeInfo')
    ts_json = x.json()
    work_dict = {}
    for item in ts_json['symbols']:
        if 'USDT' in item['symbol']:
            work_dict[item['symbol']] = {
                'pricePrecision': item['pricePrecision'],
                'quantityPrecision': item['quantityPrecision']
            }
    time.sleep(1)
    return work_dict


def prt(message, pointer):
    telegram_bot_sendtext(pointer + ': ' + message)
    print(pointer + ': ' + message)
