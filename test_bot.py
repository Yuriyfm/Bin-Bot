from indicators import *
from functions import *

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
SYMBOL = 'ETHUSDT'

df = get_futures_klines(SYMBOL, 500, '')
df['slope'] = get_slope(df['close'], 7)
mean_slope = df['slope'][431:444].mean()
print(mean_slope)
