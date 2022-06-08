from indicators import *
from functions import *
import json
import datetime
import sqlite3

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
SYMBOL = 'ETHUSDT'

# df = get_futures_klines(SYMBOL, 200, 'eth', 1)
# df = prepareDF(df)

data1 = {'type': 'short', 'start time': '19-05-2022 15:27', 'start price': 2008.0, 'profit': -0.268, 'finish price': 2020.06}
data2 = {'type': 'short', 'start time': '19-05-2022 15:40', 'start price': 2025.39, 'profit': -0.251, 'finish price': 2037.91}

file_url = 'deals_data.json'
if not os.path.exists(file_url):
    my_file = open("deals_data.json", "w")
    my_file.write('[]')
    my_file.close()

# 1. Read file contents
with open(file_url, "r") as file:
    data = json.load(file)

# 2. Update json object
data.append(data1)

# 3. Write json file
with open(file_url, "w") as file:
    json.dump(data, file)

# docker/volumes/deals_data/deals_data.json
