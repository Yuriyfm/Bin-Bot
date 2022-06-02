from dotenv import load_dotenv
from pathlib import Path
import time
import datetime
import random
import os
from functions import get_symbol_price, get_wallet_balance, open_position, close_position, \
    get_opened_positions, check_and_close_orders, getTPSLfrom_telegram, prt, check_if_signal, get_current_atr
from binance import Client

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
SECRET = os.getenv("SECRET")
SYMBOL = 'ETHUSDT'
client = Client(KEY, SECRET)

STOP_PRICE = 0
ATR_RATE = 0.2
pointer = str(f'{SYMBOL}-{random.randint(1000, 9999)}')
KLINES = 100
price = get_symbol_price(SYMBOL)


DEAL = {}
STAT = {'start': time.time(), 'positive': 0, 'negative': 0, 'balance': 0, 'deals': []}


def main(step):
    global STEP_STOP_PRICE
    global STAT
    global DEAL
    global max_position
    global STOP_PRICE

    current_price = get_symbol_price(SYMBOL)
    atr_stop_percent = round(get_current_atr(SYMBOL, pointer) / 100, 3)
    if step == 1:
        prt(f'\nПлюсовых: {STAT["positive"]} '
            f'\nМинусовых: {STAT["negative"]} '
            f'\nprofit %: {round(STAT["balance"], 2)}, '
            f'\nБаланс: {get_wallet_balance()}'
            f'\nТекущий курс: {current_price}'
            f'\nТекущая сделка: {DEAL}'
            f'\nCделки:\n'
            + str(STAT['deals']), pointer)

    try:
        getTPSLfrom_telegram(SYMBOL)
        position = get_opened_positions(SYMBOL, pointer)
        open_sl = position[0]
        if open_sl == "":  # no position
            # close all stop loss orders
            check_and_close_orders(SYMBOL)
            signal = check_if_signal(SYMBOL,  pointer, KLINES)

            if signal == 'long':
                balance = get_wallet_balance()
                max_position = round(balance * 0.2 / price, 3)
                now = datetime.datetime.now()
                open_position(SYMBOL, signal, max_position, atr_stop_percent * ATR_RATE, 3, pointer)
                DEAL['type'] = signal
                DEAL['start time'] = now.strftime("%d-%m-%Y %H:%M")
                DEAL['start price'] = current_price
                STOP_PRICE = current_price * (1 - atr_stop_percent * ATR_RATE)
                prt(f'Открыл {signal} {max_position}{SYMBOL} на {round(max_position * current_price, 2)}$, по курсу {current_price}', pointer)

            elif signal == 'short':
                balance = get_wallet_balance()
                max_position = round(balance * 0.2 / price, 3)
                now = datetime.datetime.now()
                open_position(SYMBOL, signal, max_position, atr_stop_percent * ATR_RATE, 3, pointer)
                DEAL['type'] = signal
                DEAL['start time'] = now.strftime("%d-%m-%Y %H:%M")
                DEAL['start price'] = current_price
                STOP_PRICE = current_price * (1 + atr_stop_percent * ATR_RATE)
                prt(f'Открыл {signal} {max_position}{SYMBOL} на {round(max_position * current_price, 2)}$, по курсу {current_price}', pointer)

        else:
            entry_price = position[5]  # enter price
            quantity = position[1]


            if open_sl == 'long':
                if current_price * (1 - atr_stop_percent * ATR_RATE) > STOP_PRICE:
                    STOP_PRICE = current_price * (1 - atr_stop_percent * ATR_RATE)
                if step % 60 == 0:
                    prt(f'long\nВход: {entry_price}\nТекущая: {current_price},\nСтоп: {round(STOP_PRICE, 2)},'
                        f'\nТекущий %:{round((current_price /  entry_price - 1) * 100, 2)}'
                        f'\nATR: {atr_stop_percent * 100}', pointer)
                if current_price < STOP_PRICE:
                    # stop loss
                    close_position(SYMBOL, open_sl, round(abs(quantity), 3), atr_stop_percent * ATR_RATE,  pointer)
                    profit = round(((current_price / entry_price - 1) * 100) - 0.045, 3)
                    if profit > 0:
                        STAT['positive'] += 1
                    else:
                        STAT['negative'] += 1
                    STAT['balance'] += profit
                    DEAL['profit'] = profit
                    DEAL['finish price'] = current_price
                    prt(f'Завершил сделку {open_sl} с результатом {profit}% по курсу {current_price}', pointer)
                    # STAT['deals'].append(DEAL)
                    DEAL = {}
                    STEP_STOP_PRICE = None

            if open_sl == 'short':
                if current_price * (1 + atr_stop_percent * ATR_RATE) < STOP_PRICE:
                    STOP_PRICE = current_price * (1 + atr_stop_percent * ATR_RATE)
                if step % 60 == 0:
                    prt(f'short\nВход: {entry_price}\nТекущая: {current_price},\nСтоп: {round(STOP_PRICE, 2)},'
                        f'\nТекущий %:{round((1 - current_price /  entry_price) * 100, 2)}'
                        f'\nATR: {atr_stop_percent * 100}', pointer)
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
                    prt(f'Завершил сделку {open_sl} с результатом {profit}% по курсу {current_price}', pointer)
                    # STAT['deals'].append(DEAL)
                    DEAL = {}
                    STEP_STOP_PRICE = None

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

