from dotenv import load_dotenv
from pathlib import Path
import time
import datetime
import random
import os
import json
from functions import get_symbol_price, get_wallet_balance, open_position, close_position, \
    get_opened_positions, check_and_close_orders, getTPSLfrom_telegram, prt, check_if_signal, \
    check_diff, parce_tick_size, check_stop_price_condition
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
pointer = str(f'{random.randint(1000, 9999)}')
KLINES = 100
MAX_PROFIT = 0
SMA_1 = 9
SMA_2 = 31
TICK_SIZE_DICT = parce_tick_size(pointer)
# file_url = 'deals_data/deals_data.json'
# if not os.path.exists(file_url):
#     my_file = open(file_url, "w")
#     my_file.write('[]')
#     my_file.close()

# send_photo_file(file_url)

DEAL = {}
STAT = {'start': datetime.datetime.now() + datetime.timedelta(hours=7), 'positive': 0, 'negative': 0, 'balance': 0}


def main(step):
    global STAT
    global DEAL
    global STOP_PRICE
    global MAX_PROFIT
    global SYMBOL
    global TICK_SIZE_DICT

    if step == 1:
        prt(f'\nПлюсовых: {STAT["positive"]} '
            f'\nМинусовых: {STAT["negative"]} '
            f'\nprofit %: {round(STAT["balance"], 2)}, '
            f'\nБаланс: {get_wallet_balance()}'
            f'\nТекущая сделка: {DEAL}', pointer)

    if SYMBOL == '':
        SYMBOL = check_diff(pointer, SMA_1, SMA_2, KLINES)
    current_price = get_symbol_price(SYMBOL, pointer)
    price_precision = TICK_SIZE_DICT[SYMBOL]['price_precision'] if TICK_SIZE_DICT[SYMBOL]['price_precision'] != 0 else None
    quantity_precision = TICK_SIZE_DICT[SYMBOL]['quantity_precision'] if TICK_SIZE_DICT[SYMBOL]['quantity_precision'] != 0 else None

    try:
        getTPSLfrom_telegram(SYMBOL)
        position = get_opened_positions(SYMBOL, pointer)
        open_sl = position[0]
        if open_sl == "":  # no position
            if step % 6 == 0:
                prt(f'Идет отслеживание валюты: {SYMBOL}, ', pointer)
            # close all stop loss orders
            check_and_close_orders(SYMBOL)
            signal = check_if_signal(SYMBOL,  pointer, KLINES, DEAL)
            if signal == 'restart':
                SYMBOL = ''
            if signal == 'short':
                balance = get_wallet_balance()
                max_position = round(balance * 0.1 / current_price, quantity_precision)
                now = datetime.datetime.now() + datetime.timedelta(hours=7)
                prt(f'try open position', pointer)
                open_position_res = open_position(SYMBOL, signal, max_position, pointer)
                if open_position_res:
                    prt(
                        f'Открыл {signal} {max_position}{SYMBOL} на {round(max_position * current_price, price_precision)}$, по курсу {current_price}',
                        pointer)
                    DEAL['type'] = signal
                    DEAL['start time'] = now.strftime("%d-%m-%Y %H:%M")
                    DEAL["start price"] = current_price

        else:
            quantity = position[1]
            if "start price" in DEAL:
                entry_price = DEAL["start price"]
            else:
                entry_price = position[5]


            if open_sl == 'short':
                now = datetime.datetime.now() + datetime.timedelta(hours=7)
                stop_condition = check_stop_price_condition(SYMBOL, KLINES, pointer, entry_price, current_price)
                if step % 30 == 0:
                    prt(f'short\nВход: {entry_price}\nТекущая: {current_price},\nСтоп: {round(STOP_PRICE, price_precision)},'
                        f'\nТекущий %:{round((1 - current_price /  entry_price) * 100, price_precision)}', pointer)
                if stop_condition:
                    # stop loss
                    close_position_res = close_position(SYMBOL, open_sl, round(abs(quantity), quantity_precision), pointer)
                    if close_position_res:
                        profit = round(((1 - current_price / entry_price) * 100) - 0.045, price_precision)
                        prt(f'Завершил сделку {open_sl} {SYMBOL} с результатом {profit}% по курсу {current_price}, max profit={MAX_PROFIT}', pointer)
                        if profit > 0:
                            STAT['positive'] += 1
                        else:
                            STAT['negative'] += 1
                        STAT['balance'] += profit
                        DEAL['profit'] = profit
                        DEAL['finish price'] = current_price
                        DEAL['finish time'] = now.strftime("%d-%m-%Y %H:%M")
                        DEAL['max profit'] = MAX_PROFIT


                    # with open(file_url, "r") as file:
                    #     data = json.load(file)
                    # data.append(DEAL)
                    # with open(file_url, "w") as file:
                    #     json.dump(data, file)

                    DEAL = {}
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

