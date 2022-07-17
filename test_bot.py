from indicators import *
from functions import *
import json
import datetime

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
KLINES = 100
SYMBOL = 'ETHUSDT'
SMA_1 = 9
SMA_2 = 31
DF = get_futures_klines(SYMBOL, KLINES, 'pointer', 1)
DF = prepareDF(DF)
DF[f'SMA_{SMA_1}'] = get_sma(DF['close'], SMA_1)
DF[f'SMA_{SMA_2}'] = get_sma(DF['close'], SMA_2)
res = get_last_intersection(DF, SMA_1, SMA_2)
print(res)
# sudo nano /var/lib/docker/volumes/deals_data/_data/deals_data.json


