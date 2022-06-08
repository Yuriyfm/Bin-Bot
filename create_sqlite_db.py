import sqlite3

try:
    file_name = 'ma_bot_data.db'
    sqlite_connection = sqlite3.connect(file_name)
    cursor = sqlite_connection.cursor()
    print(f"База данных {file_name} создана и успешно подключена к SQLite")

    record = cursor.fetchall()
    print(record)
    cursor.close()
    sqlite_connection.close()
    print("Соединение с SQLite закрыто")

except sqlite3.Error as error:
    print("Ошибка при подключении к sqlite", error)
