from dotenv import load_dotenv
from pathlib import Path
import pandas as pd
import copy
import time
import datetime
import random
import os
import requests
from functions import get_symbol_price, get_wallet_balance, open_position, close_position, \
    get_opened_positions, check_and_close_orders, getTPSLfrom_telegram, prt
from binance import Client

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
SECRET = os.getenv("SECRET")
SYMBOL = 'ETHUSDT'
client = Client(KEY, SECRET)


STEP_PRICE = None
STEP = 0
REMAINDER = 1
stop_percent = 0.004
pointer = str(f'{SYMBOL}-{random.randint(1000, 9999)}')
KLINES = 100
balance = get_wallet_balance()
price = get_symbol_price(SYMBOL)
max_position = round(balance * 0.1 / price, 3)


eth_profit_array = [[round(price * 0.004, 3), 2], [round(price * 0.006, 3), 3], [round(price * 0.010, 3), 3], [round(price * 0.014, 3), 2]]


DEAL = {}

STAT = {'start': time.time(), 'positive': 0, 'negative': 0, 'balance': 0, 'deals': []}

profit_array = copy.copy(eth_profit_array)


def get_futures_klines(symbol, limit, pointer):
    try:
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
    except Exception as e:
        prt(f'Ошибка при получении истории последних свечей: \n{e}', pointer)


def PrepareDF(DF):
    df = DF.iloc[:, [0, 1, 2, 3, 4, 5]]
    df.columns = ["date", "open", "high", "low", "close", "volume"]
    df['SMA_25'] = df['close'].rolling(window=25).mean()
    df['SMA_7'] = df['close'].rolling(window=7).mean()
    df = df.set_index('date')
    df = df.reset_index()
    return df


def check_if_signal(SYMBOL,  pointer, KLINES):
    try:
        ohlc = get_futures_klines(SYMBOL, KLINES, pointer)
        df = PrepareDF(ohlc)
        signal = ""  # return value
        prev_delta_sma = df['SMA_7'][98] < df['SMA_25'][98]
        cur_delta_sma = df['SMA_7'][99] > df['SMA_25'][99]


        if prev_delta_sma and cur_delta_sma:
            signal = 'long'

        if not prev_delta_sma and not cur_delta_sma:
            signal = 'short'

        return signal
    except Exception as e:
        prt(f'Ошибка в функции проверки сигнала: \n{e}', pointer)



def main(step):
    global profit_array
    global STEP_PRICE
    global DEAL
    global STAT
    global STEP
    global REMAINDER
    global balance
    global max_position

    current_price = get_symbol_price(SYMBOL)

    if step == 1:
        prt(f'\nПлюсовых: {STAT["positive"]} '
            f'\nМинусовых: {STAT["negative"]} '
            f'\nprofit USD: {round(STAT["balance"], 2)}, '
            f'\nБаланс: {get_wallet_balance()}'
            f'\nТекущий курс: {current_price}'
            f'\nТекущая сделка: {DEAL}'
            f'\nCделки:\n'
            + str(STAT['deals']), pointer)

    try:
        getTPSLfrom_telegram(SYMBOL, stop_percent, pointer)
        position = get_opened_positions(SYMBOL, pointer)
        open_sl = position[0]
        if open_sl == "":  # no position
            # close all stop loss orders
            check_and_close_orders(SYMBOL)
            signal = check_if_signal(SYMBOL,  pointer, KLINES)
            profit_array = copy.copy(eth_profit_array)

            if signal == 'long':
                balance = get_wallet_balance()
                max_position = round(balance * 0.1 / price, 3)
                now = datetime.datetime.now()
                open_position(SYMBOL, signal, max_position, stop_percent, 3, pointer)
                DEAL['type'] = signal
                DEAL['start_time'] = now.strftime("%d-%m-%Y %H:%M")
                DEAL['start_price'] = current_price
                DEAL['target_price'] = round(current_price * 1.013, 3)
                prt(f'Открыл {signal} на {max_position} {SYMBOL}, по курсу {current_price}', pointer)


            elif signal == 'short':
                balance = get_wallet_balance()
                max_position = round(balance * 0.1 / price, 3)
                now = datetime.datetime.now()
                open_position(SYMBOL, signal, max_position, stop_percent, 3, pointer)
                DEAL['type'] = signal
                DEAL['start_time'] = now.strftime("%d-%m-%Y %H:%M")
                DEAL['start_price'] = current_price
                DEAL['target_price'] = round(current_price * 0.987, 3)
                prt(f'Открыл {signal} на {max_position} {SYMBOL}, по курсу {current_price}', pointer)


        else:

            entry_price = position[5]  # enter price
            quantity = position[1]
            if open_sl == 'long':
                stop_price = entry_price * (1 - stop_percent) if STEP_PRICE is None else STEP_PRICE * 0.999
                if current_price < stop_price:
                    # stop loss
                    close_position(SYMBOL, open_sl, round(abs(quantity), 3), stop_percent, 3, pointer)
                    profit_array = copy.copy(eth_profit_array)
                    STEP += 1
                    profit = round(abs(quantity) * (current_price - entry_price), 3)
                    if STEP == 1:
                        STAT['negative'] += 1
                    DEAL[STEP] = profit
                    STAT['balance'] += profit
                    prt(
                        f'Завершил сделку {open_sl} {abs(quantity)} {SYMBOL}, остаток {round(REMAINDER * 100)}% на шаге {STEP}', pointer)
                    STAT['deals'].append(DEAL)
                    DEAL = {}
                    STEP_PRICE = None
                    STEP = 0
                    REMAINDER = 1

                else:
                    temp_arr = copy.copy(profit_array)
                    for j in range(0, len(temp_arr)):
                        delta = temp_arr[j][0]
                        contracts = temp_arr[j][1]
                        if current_price > (entry_price + delta):
                            # take profit
                            if len(profit_array) > 1:
                                close_position(SYMBOL, open_sl, abs(round(max_position * (contracts/10), 3)), stop_percent, 3, pointer)
                            else:
                                close_position(SYMBOL, open_sl, round(abs(quantity), 3), stop_percent, 3, pointer)


                            profit = round((max_position * (contracts / 10)) * (current_price - entry_price), 3)
                            STEP += 1
                            if STEP == 1:
                                STAT['positive'] += 1
                            REMAINDER -= (contracts / 10)
                            DEAL[STEP] = profit
                            STAT['balance'] += profit
                            STEP_PRICE = current_price
                            prt(f'Закрыл {round((1 - REMAINDER) * 100)}% сделки {open_sl}, шаг {STEP}', pointer)
                            del profit_array[0]
                            if len(profit_array) == 0:
                                STAT['deals'].append(DEAL)
                                DEAL = {}
                                STEP_PRICE = None
                                STEP = 0
                                REMAINDER = 1

            if open_sl == 'short':
                stop_price = entry_price * (1 + stop_percent) if STEP_PRICE is None else STEP_PRICE * 1.001
                if current_price > stop_price:
                    # stop loss
                    close_position(SYMBOL, open_sl, round(abs(quantity), 3), stop_percent, 3, pointer)
                    profit_array = copy.copy(eth_profit_array)
                    STEP += 1
                    profit = round(abs(quantity) * (entry_price - current_price), 3)
                    if STEP == 1:
                        STAT['negative'] += 1
                    DEAL[STEP] = profit
                    STAT['balance'] += profit
                    prt(
                        f'Завершил сделку {open_sl} {abs(quantity)} {SYMBOL}, остаток {round(REMAINDER * 100)}% на шаге {STEP}', pointer)
                    STAT['deals'].append(DEAL)
                    DEAL = {}
                    STEP_PRICE = None
                    STEP = 0
                    REMAINDER = 1

                else:
                    temp_arr = copy.copy(profit_array)
                    for j in range(0, len(temp_arr)):
                        delta = temp_arr[j][0]
                        contracts = temp_arr[j][1]
                        if current_price < (entry_price - delta):
                            # take profit
                            if len(profit_array) > 1:
                                close_position(SYMBOL, open_sl, abs(round(max_position * (contracts/10), 3)), stop_percent, 3, pointer)
                            else:
                                close_position(SYMBOL, open_sl, round(abs(quantity), 3), stop_percent, 3, pointer)
                            profit = round((max_position * (contracts / 10)) * (entry_price - current_price), 3)
                            STEP += 1
                            if STEP == 1:
                                STAT['positive'] += 1
                            REMAINDER -= (contracts / 10)
                            DEAL[STEP] = profit
                            STAT['balance'] += profit
                            STEP_PRICE = current_price
                            prt(f'Закрыл {round((1 - REMAINDER) * 100)}% сделки {open_sl}, шаг {STEP}', pointer)
                            del profit_array[0]
                            if len(profit_array) == 0:
                                STAT['deals'].append(DEAL)
                                DEAL = {}
                                STEP_PRICE = None
                                STEP = 0
                                REMAINDER = 1
    except Exception as e:
        prt(f'Ошибка в main: \n{e}', pointer)


start_time = time.time()
timeout = time.time() + 60 * 60 * 168  # таймер времени работы бота
counter_r = 1

while time.time() <= timeout:
    try:
        main(counter_r)
        counter_r = counter_r + 1
        if counter_r > 360:
            counter_r = 1
        time.sleep(10 - ((time.time() - start_time) % 10.0))  # запрос к площадке каждые 10 секунд
    except KeyboardInterrupt:
        print('\n KeyboardInterrupt. Stopping.')
        exit()

