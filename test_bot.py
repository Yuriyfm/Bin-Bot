from indicators import *
from functions import *
import datetime

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
SYMBOL = 'ETHUSDT'

df = get_futures_klines(SYMBOL, 100, 'eth', 5)
res = get_sma_250_slope(df, 100, 10)
print(res)
