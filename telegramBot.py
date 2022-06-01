import telebot

bot = telebot.TeleBot('Здесь впиши токен, полученный от @botfather')

@bot.message_handler(commands=["start"])
def start(m, res=False):
    bot.send_message(m.chat.id, 'Я на связи. Напиши мне что-нибудь )')
