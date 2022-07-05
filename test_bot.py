from indicators import *
from functions import *
import json
import datetime




load_dotenv()
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
KEY = os.getenv("KEY")
SYMBOL = ''


if SYMBOL:
    print('hey')




# sudo nano /var/lib/docker/volumes/deals_data/_data/deals_data.json


