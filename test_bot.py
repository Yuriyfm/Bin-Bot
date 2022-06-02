from indicators import *
from functions import *
import datetime

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
SYMBOL = 'ETHUSDT'

df = get_futures_klines(SYMBOL, 200, 'eth', 1)
df = prepareDF(df)
df['SMA_100'] = sma(df['close'], 100)
df['slope'] = get_slope(df['SMA_100'], 14)
print(df)