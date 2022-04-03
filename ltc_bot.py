import copy
import time
import datetime
import random
import os
from functions import get_symbol_price, get_wallet_balance, open_position, close_position, \
    get_opened_positions, check_and_close_orders, check_if_signal, getTPSLfrom_telegram, prt, get_futures_klines, indATR

SECRET = os.getenv("SECRET")
SYMBOL = 'LTCUSDT'
SLOPE_S = 45
SLOPE_L = 20
POS_IN_CHANNEL_S = 0.8
POS_IN_CHANNEL_L = 0.3
KLINES = 70

STEP_PRICE = None
STEP = 0
REMAINDER = 1
ROUND = 3
stop_percent = 0.008
pointer = str(f'{SYMBOL}-{random.randint(1000, 9999)}')
ATR = indATR(get_futures_klines(SYMBOL, 500, pointer), 14)['ATR'].mean()

price = get_symbol_price(SYMBOL)
balance = get_wallet_balance()
max_position = round((balance * 0.3) / price, 3)


eth_profit_array = [[round(price * 0.008, 3), 2], [round(price * 0.012, 3), 3],
                    [round(price * 0.016, 3), 3], [round(price * 0.020, 3), 2]]

DEAL = {}

STAT = {'start': time.time(), 'positive': 0, 'negative': 0, 'balance': 0, 'deals': []}

profit_array = copy.copy(eth_profit_array)




def main(step):
    global profit_array
    global STEP_PRICE
    global DEAL
    global STAT
    global STEP
    global REMAINDER

    if step == 1:
        prt(f'Плюсовых: {STAT["positive"]} '
            f'\nМинусовых: {STAT["negative"]} '
            f'\nРезультат USD: {round(STAT["balance"], 2)} '
            f'\nCделки:\n'
            + str(STAT['deals']), pointer)

    try:
        getTPSLfrom_telegram(SYMBOL, stop_percent, ROUND, pointer)
        position = get_opened_positions(SYMBOL, pointer)
        open_sl = position[0]
        if open_sl == "":  # no position
            # close all stop loss orders
            check_and_close_orders(SYMBOL)
            signal = check_if_signal(SYMBOL, POS_IN_CHANNEL_L, POS_IN_CHANNEL_S, SLOPE_L, SLOPE_S, KLINES, ATR, pointer)
            profit_array = copy.copy(eth_profit_array)

            if signal == 'long':
                now = datetime.datetime.now()
                open_position(SYMBOL, signal, max_position, stop_percent, ROUND, pointer)
                DEAL['type'] = signal
                DEAL['start_time'] = now.strftime("%d-%m-%Y %H:%M")
                prt(f'Открыл {signal} на {max_position} {SYMBOL}', pointer)
                STAT['deals'].append(DEAL)
                STEP_PRICE = None
                STEP = 0
                REMAINDER = 1
                DEAL = {}

            elif signal == 'short':
                now = datetime.datetime.now()
                open_position(SYMBOL, signal, max_position, stop_percent, ROUND, pointer)
                DEAL['type'] = signal
                DEAL['start_time'] = now.strftime("%d-%m-%Y %H:%M")
                prt(f'Открыл {signal} на {max_position} {SYMBOL}', pointer)
                STAT['deals'].append(DEAL)
                STEP_PRICE = None
                STEP = 0
                REMAINDER = 1
                DEAL = {}

        else:

            entry_price = position[5]  # enter price
            current_price = get_symbol_price(SYMBOL)
            quantity = position[1]
            if open_sl == 'long':
                stop_price = entry_price * (1 - stop_percent) if STEP_PRICE is None else STEP_PRICE * (1 - stop_percent)
                if current_price < stop_price:
                    # stop loss
                    close_position(SYMBOL, open_sl, round(abs(quantity), ROUND), stop_percent, ROUND, pointer)
                    profit_array = copy.copy(eth_profit_array)

                    STEP += 1
                    profit = round(abs(quantity) * (current_price - entry_price), ROUND)
                    if profit < 0:
                        STAT['negative'] += 1
                    else:
                        STAT['positive'] += 1
                    DEAL[STEP] = profit
                    STAT['balance'] += profit
                    prt(
                        f'Завершил сделку {open_sl} {abs(quantity)} {SYMBOL}, остаток {round(REMAINDER * 100)}% на шаге {STEP}', pointer)

                else:
                    temp_arr = copy.copy(profit_array)
                    for j in range(0, len(temp_arr) - 1):
                        delta = temp_arr[j][0]
                        contracts = temp_arr[j][1]
                        if current_price > (entry_price + delta):
                            # take profit
                            if len(profit_array) > 1:
                                close_position(SYMBOL, open_sl, round(abs(quantity), ROUND), stop_percent, ROUND, pointer)
                            else:
                                close_position(SYMBOL, open_sl, round(abs(quantity), ROUND), stop_percent, ROUND, pointer)
                            profit = round((max_position * (contracts / 10)) * (current_price - entry_price), ROUND)
                            STEP += 1
                            REMAINDER -= (contracts / 10)
                            DEAL[STEP] = profit
                            STAT['positive'] += 1
                            STAT['balance'] += profit
                            STEP_PRICE = current_price
                            prt(f'Закрыл {abs(1 - REMAINDER) * 100}% сделки {open_sl}, шаг {STEP}', pointer)
                            del profit_array[0]

            if open_sl == 'short':
                stop_price = entry_price * (1 + stop_percent) if STEP_PRICE is None else STEP_PRICE * (1 + stop_percent)
                if current_price > stop_price:
                    # stop loss
                    profit_array = copy.copy(eth_profit_array)
                    close_position(SYMBOL, open_sl, round(abs(quantity), ROUND), stop_percent, ROUND, pointer)
                    profit_array = copy.copy(eth_profit_array)

                    STEP += 1
                    profit = round(abs(quantity) * (entry_price - current_price), 3)
                    if profit < 0:
                        STAT['negative'] += 1
                    else:
                        STAT['positive'] += 1
                    DEAL[STEP] = profit
                    STAT['balance'] += profit
                    prt(
                        f'Завершил сделку {open_sl} {abs(quantity)} {SYMBOL}, остаток {round(REMAINDER * 100)}% на шаге {STEP}', pointer)

                else:
                    temp_arr = copy.copy(profit_array)
                    for j in range(0, len(temp_arr) - 1):
                        delta = temp_arr[j][0]
                        contracts = temp_arr[j][1]
                        if current_price < (entry_price - delta):
                            # take profit
                            if len(profit_array) > 1:
                                close_position(SYMBOL, open_sl, round(abs(quantity), ROUND), stop_percent, ROUND, pointer)
                            else:
                                close_position(SYMBOL, open_sl, round(abs(quantity), ROUND), stop_percent, ROUND, pointer)
                            profit = round((max_position * (contracts / 10)) * (entry_price - current_price), ROUND)
                            STEP += 1
                            REMAINDER -= (contracts / 10)
                            DEAL[STEP] = profit
                            STAT['positive'] += 1
                            STAT['balance'] += profit
                            STEP_PRICE = current_price
                            prt(f'Закрыл {abs(1 - REMAINDER) * 100}% сделки {open_sl}, шаг {STEP}', pointer)
                            del profit_array[0]
    except Exception as e:
        prt(f'Ошибка в main: \n{e}', pointer)


start_time = time.time()
timeout = time.time() + 60 * 60 * 120  # таймер времени работы бота
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
