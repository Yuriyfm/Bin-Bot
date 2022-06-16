from indicators import *
from functions import *
import json
import datetime
import sqlite3

from telegramBot import send_photo_file

load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
SYMBOL = 'ETHUSDT'
file_url = '123.txt'
print(send_photo_file(file_url))

# sudo nano /var/lib/docker/volumes/deals_data/_data/deals_data.json


