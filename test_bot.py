from indicators import *
from functions import *

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
SYMBOL = 'ETHUSDT'

df = get_futures_klines(SYMBOL, 500, '')
df = prepareDF(df)
res = check_stop_price(SYMBOL, 100, '')
print(res)
