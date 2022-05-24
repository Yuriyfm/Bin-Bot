from indicators import *
from functions import *

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
SYMBOL = 'ETHUSDT'

current_price = get_symbol_price(SYMBOL)
df = get_futures_klines(SYMBOL, 100, 'ETH')
res = get_current_atr(SYMBOL, 'eth')
print(res)

