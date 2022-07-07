import requests
import os

bot_token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("CHAT_ID")


def send_photo_file(file):
    files = {'document': open(file, 'rb')}
    res = requests.post(f'{"https://api.telegram.org/bot"}{bot_token}/sendDocument?chat_id={chat_id}', files=files)
    return res
