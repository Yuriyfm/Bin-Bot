from indicators import *
from functions import *

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
SYMBOL = 'ETHUSDT'

current_price = get_symbol_price(SYMBOL)
stop = get_current_atr(SYMBOL, 'eth')
print(current_price * (1 - stop / 100))
