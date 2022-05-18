import copy
import time
import datetime
import random
import os
from functions import get_symbol_price, get_wallet_balance, open_position, close_position, \
    get_opened_positions, check_and_close_orders, check_if_signal, getTPSLfrom_telegram, prt, get_futures_klines, indATR


SECRET = os.getenv("SECRET")
SYMBOL = 'ETHUSDT'
# SLOPE_S = 20
# SLOPE_L = -20
# SL_X_L = -4
# SL_X_S = 3.5
# SL_X_KLINE_L = 85
# SL_X_KLINE_S = 95
# SL_X_KLINE_L_2 = 100
# SL_X_KLINE_S_2 = 75
# ATR_ORIG_S = 9
# ATR_ORIG_L = 12
# ATR_KLINE_L = 95
# ATR_KLINE_S = 117
# POS_IN_CHANNEL_S = 0.5
# POS_IN_CHANNEL_L = 0.45
# SL_X_L_2 = 4.5
# SL_X_S_2 = -5
# KLINES = 120

SLOPE_S = 20
SLOPE_L = -20
SL_X_L = -5
SL_X_S = 3
SL_X_KLINE_L = 75
SL_X_KLINE_S = 80
SL_X_KLINE_L_2 = 120
SL_X_KLINE_S_2 = 105
POS_IN_CHANNEL_S = 0.5
POS_IN_CHANNEL_L = 0.45
SL_X_L_2 = 6.5
SL_X_S_2 = -10
KLINES = 120


STEP_STOP_PRICE = None
STEP = 0
REMAINDER = 1
ROUND = 3
stop_percent = 0.013
pointer = str(f'{SYMBOL}-{random.randint(1000, 9999)}')

price = get_symbol_price(SYMBOL)

balance = get_wallet_balance()
max_position = round(balance * 0.3 / price, ROUND)

# eth_profit_array = [[round(price * 0.013, 3), 3], [round(price * 0.017, 3), 4], [round(price * 0.021, 3), 3]]
eth_profit_array = [[round(price * 0.035, 3), 10]]

DEAL = {}

STAT = {'start': time.time(), 'positive': 0, 'negative': 0, 'balance': 0, 'deals': []}

profit_array = copy.copy(eth_profit_array)




def main(step):
    global profit_array
    global STEP_STOP_PRICE
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
        getTPSLfrom_telegram(SYMBOL, stop_percent, ROUND, pointer)
        position = get_opened_positions(SYMBOL, pointer)
        open_sl = position[0]
        if open_sl == "":  # no position
            # close all stop loss orders
            check_and_close_orders(SYMBOL)
            signal = check_if_signal(SYMBOL,  pointer, SLOPE_S, SLOPE_L, SL_X_L, SL_X_S, SL_X_KLINE_L, SL_X_KLINE_S,
                                     POS_IN_CHANNEL_S, POS_IN_CHANNEL_L, SL_X_L_2, SL_X_S_2, SL_X_KLINE_S_2,
                                     SL_X_KLINE_L_2, KLINES)
            profit_array = copy.copy(eth_profit_array)

            if signal == 'long':
                balance = get_wallet_balance()
                max_position = round(balance * 0.3 / price, ROUND)
                now = datetime.datetime.now()
                open_position(SYMBOL, signal, max_position, stop_percent, ROUND, pointer)
                DEAL['type'] = signal
                DEAL['start_time'] = now.strftime("%d-%m-%Y %H:%M")
                DEAL['start_price'] = current_price
                DEAL['target_price'] = round(current_price * 1.013, 3)
                prt(f'Открыл {signal} на {max_position} {SYMBOL}, по курсу {current_price}', pointer)


            elif signal == 'short':
                balance = get_wallet_balance()
                max_position = round(balance * 0.3 / price, ROUND)
                now = datetime.datetime.now()
                open_position(SYMBOL, signal, max_position, stop_percent, ROUND, pointer)
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
                    close_position(SYMBOL, open_sl, round(abs(quantity), ROUND), stop_percent, ROUND, pointer)
                    profit_array = copy.copy(eth_profit_array)
                    STEP += 1
                    profit = round(abs(quantity) * (current_price - entry_price), ROUND)
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
                                close_position(SYMBOL, open_sl, abs(round(max_position * (contracts/10), ROUND)), stop_percent, ROUND, pointer)
                            else:
                                close_position(SYMBOL, open_sl, round(abs(quantity), ROUND), stop_percent, ROUND, pointer)


                            profit = round((max_position * (contracts / 10)) * (current_price - entry_price), ROUND)
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
                    close_position(SYMBOL, open_sl, round(abs(quantity), ROUND), stop_percent, ROUND, pointer)
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
                                close_position(SYMBOL, open_sl, abs(round(max_position * (contracts/10), ROUND)), stop_percent, ROUND, pointer)
                            else:
                                close_position(SYMBOL, open_sl, round(abs(quantity), ROUND), stop_percent, ROUND, pointer)
                            profit = round((max_position * (contracts / 10)) * (entry_price - current_price), ROUND)
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
        # if counter_r % 20 == 0:
        #     ("script continue running at " + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
        main(counter_r)
        counter_r = counter_r + 1
        if counter_r > 120:
            counter_r = 1
        time.sleep(30 - ((time.time() - start_time) % 30.0))  # запрос к площадке 2 раза в минуту
    except KeyboardInterrupt:
        print('\n KeyboardInterrupt. Stopping.')
        exit()


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


STEP_STOP_PRICE = None
stop_percent = 0.003
pointer = str(f'{SYMBOL}-{random.randint(1000, 9999)}')
KLINES = 100
price = get_symbol_price(SYMBOL)

DEAL = {}
STAT = {'start': time.time(), 'positive': 0, 'negative': 0, 'balance': 0, 'deals': []}


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
        negative_trend = (df['close'][0] - df['close'][99]) > 0
        positive_trend = (df['close'][0] - df['close'][99]) < 0


        if prev_delta_sma and cur_delta_sma and positive_trend:
            signal = 'long'

        if not prev_delta_sma and not cur_delta_sma and negative_trend:
            signal = 'short'

        return signal
    except Exception as e:
        prt(f'Ошибка в функции проверки сигнала: \n{e}', pointer)





