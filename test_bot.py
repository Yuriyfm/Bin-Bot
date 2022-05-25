from indicators import *
from functions import *

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
SYMBOL = 'ETHUSDT'

df = get_futures_klines(SYMBOL, 100, '')
df = get_bollinger_bands(df)
print(df)