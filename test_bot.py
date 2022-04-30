import random
from dotenv import load_dotenv
from pathlib import Path
import os
from functions import get_symbol_price, get_wallet_balance, open_position, close_position, \
    get_opened_positions, check_and_close_orders, check_if_signal, getTPSLfrom_telegram, prt, get_futures_klines, indATR
from binance import Client, ThreadedWebsocketManager, ThreadedDepthCacheManager
from futures_sign import send_signed_request, send_public_request

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
SECRET = os.getenv("SECRET")
SYMBOL = 'ETHUSDT'
client = Client(KEY, SECRET)


SLOPE_S = 20
SLOPE_L = -20
SL_X_L = -3.5
SL_X_S = 4
SL_X_KLINE_L = 85
SL_X_KLINE_S = 90
ATR_S = 11
ATR_L = 11.5
ATR_KLINE_L = 95
ATR_KLINE_S = 117
POS_IN_CHANNEL_S = 0.5
POS_IN_CHANNEL_L = 0.45
SL_X_L_2 = 3.5
KLINES = 120
SL_X_KLINE_L_2 = 110

STEP_PRICE = None
STEP = 0
REMAINDER = 1
ROUND = 3
stop_percent = 0.008
pointer = str(f'{SYMBOL}-{random.randint(1000, 9999)}')

price = get_symbol_price(SYMBOL)
balance = get_wallet_balance()
max_position = round(balance / price, 3)


res = check_if_signal(SYMBOL,  pointer, SLOPE_S, SLOPE_L, SL_X_L, SL_X_S, SL_X_KLINE_L, SL_X_KLINE_S,
                                     ATR_S, ATR_L, ATR_KLINE_L, ATR_KLINE_S, POS_IN_CHANNEL_S, POS_IN_CHANNEL_L,
                                     SL_X_L_2, SL_X_KLINE_L_2, KLINES)
print(res)
