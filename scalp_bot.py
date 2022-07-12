from dotenv import load_dotenv
from pathlib import Path
import time
import datetime
import random
import os
import json
from functions import get_symbol_price, get_wallet_balance, open_position, close_position, \
    get_opened_positions, check_and_close_orders, getTPSLfrom_telegram, prt, check_if_signal, get_current_atr, \
    check_diff, parce_tick_size
from binance import Client

from telegramBot import send_photo_file

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
SECRET = os.getenv("SECRET")
SYMBOL = ''
client = Client(KEY, SECRET)
SYMBOL_LIST = []

STOP_PRICE = 0
ATR_RATE = 0.25
pointer = str(f'{random.randint(1000, 9999)}')
KLINES = 200
MAX_PROFIT = 0
SMA_1 = 9
SMA_2 = 31

# file_url = 'deals_data/deals_data.json'
# if not os.path.exists(file_url):
#     my_file = open(file_url, "w")
#     my_file.write('[]')
#     my_file.close()

# send_photo_file(file_url)

DEAL = {}
STAT = {'start': datetime.datetime.now() + datetime.timedelta(hours=7), 'positive': 0, 'negative': 0, 'balance': 0}


def main(step):
    global STEP_STOP_PRICE
    global STAT
    global DEAL
    global max_position
    global STOP_PRICE
    global MAX_PROFIT
    global SYMBOL

    if step == 1:
        prt(f'\nПлюсовых: {STAT["positive"]} '
            f'\nМинусовых: {STAT["negative"]} '
            f'\nprofit %: {round(STAT["balance"], 2)}, '
            f'\nБаланс: {get_wallet_balance()}'
            f'\nТекущая сделка: {DEAL}', pointer)

    if SYMBOL == '':
        SYMBOL = check_diff(pointer, SMA_1, SMA_2)

    current_price = get_symbol_price(SYMBOL)
    atr_stop_percent = round(get_current_atr(SYMBOL, pointer) / 100, 5)
    TICK_SIZE_DICT = parce_tick_size()
    price_precision = TICK_SIZE_DICT[SYMBOL]['price_precision']

    try:
        getTPSLfrom_telegram(SYMBOL)
        position = get_opened_positions(SYMBOL, pointer)
        open_sl = position[0]
        if open_sl == "":  # no position
            if step % 60 == 0:
                prt(f'Идет отслеживание валюты: {SYMBOL}, ', pointer)
            # close all stop loss orders
            check_and_close_orders(SYMBOL)
            signal = check_if_signal(SYMBOL,  pointer, KLINES, DEAL)
            if signal == 'restart':
                SYMBOL = ''
            if signal == 'short':
                balance = get_wallet_balance()
                max_position = round(balance * 0.1 / current_price, 3)
                now = datetime.datetime.now() + datetime.timedelta(hours=7)
                open_position(SYMBOL, signal, max_position, atr_stop_percent * ATR_RATE, 3, pointer)
                DEAL['type'] = signal
                DEAL['start time'] = now.strftime("%d-%m-%Y %H:%M")
                DEAL['start price'] = current_price
                STOP_PRICE = current_price * (1 + atr_stop_percent * ATR_RATE)
                prt(f'Открыл {signal} {max_position}{SYMBOL} на {round(max_position * current_price, 2)}$, по курсу {current_price}', pointer)

        else:
            entry_price = position[5]  # enter price
            quantity = position[1]

            if open_sl == 'short':
                now = datetime.datetime.now() + datetime.timedelta(hours=7)
                if current_price * (1 + atr_stop_percent * ATR_RATE) < STOP_PRICE:
                    STOP_PRICE = current_price * (1 + atr_stop_percent * ATR_RATE)
                    MAX_PROFIT = round((1 - current_price / entry_price) * 100, 2) if round((1 - current_price / entry_price) * 100, 2) > MAX_PROFIT else MAX_PROFIT
                if step % 60 == 0:
                    prt(f'short\nВход: {entry_price}\nТекущая: {current_price},\nСтоп: {round(STOP_PRICE, 2)},'
                        f'\nТекущий %:{round((1 - current_price /  entry_price) * 100, 2)}'
                        f'\nATR: {round(atr_stop_percent * 100, 2)}', pointer)
                if current_price > STOP_PRICE:
                    # stop loss
                    close_position(SYMBOL, open_sl, round(abs(quantity), 3), atr_stop_percent * ATR_RATE,  pointer)
                    profit = round(((current_price / entry_price - 1) * -100) - 0.045, 3)
                    if profit > 0:
                        STAT['positive'] += 1
                    else:
                        STAT['negative'] += 1
                    STAT['balance'] += profit
                    DEAL['profit'] = profit
                    DEAL['finish price'] = current_price
                    DEAL['finish time'] = now.strftime("%d-%m-%Y %H:%M")
                    DEAL['max profit'] = MAX_PROFIT
                    prt(f'Завершил сделку {open_sl} с результатом {profit}% по курсу {current_price}', pointer)

                    # with open(file_url, "r") as file:
                    #     data = json.load(file)
                    # data.append(DEAL)
                    # with open(file_url, "w") as file:
                    #     json.dump(data, file)

                    DEAL = {}
                    STEP_STOP_PRICE = None
                    MAX_PROFIT = 0
                    SYMBOL = ''

    except Exception as e:
        prt(f'Ошибка в main: \n{e}', pointer)


start_time = time.time()
timeout = time.time() + 60 * 60 * 240  # таймер времени работы бота
counter_r = 1

while time.time() <= timeout:
    try:
        main(counter_r)
        counter_r = counter_r + 1
        if counter_r > 360:
            counter_r = 1
        time.sleep(10 - ((time.time() - start_time) % 10.0))  # запрос к площадке каждые 10 секунд
    except Exception as e:
        print(e)
        prt(e, pointer)
        exit()

