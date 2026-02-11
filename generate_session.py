from telethon.sync import TelegramClient
import os

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
phone = os.getenv("PHONE_NUMBER")  # Your phone with country code, e.g., +1234567890

client = TelegramClient('session', api_id, api_hash)
client.connect()

if not client.is_user_authorized():
    client.send_code_request(phone)
    client.sign_in(phone, input('Enter the code: '))

print("\n\nSESSION STRING:")
print(client.session.save())