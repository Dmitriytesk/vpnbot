import os
import subprocess
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile
from dotenv import load_dotenv

BOT_TOKEN = "7900977069:AAGGHgnf9GPFqQjCVyffs9uCw1Cu4oySXiI"
load_dotenv()
bot = Bot(token=(BOT_TOKEN))
dp = Dispatcher()
WG_DIR = "/etc/wireguard"
WG_SERVER_CONFIG = f"{WG_DIR}/wg0.conf"
WG_SERVER_IP = "185.58.115.221"

def generate_keys(client_name):
    priv_key = subprocess.getoutput("wg genkey")
    pub_key = subprocess.getoutput(f"echo '{priv_key}' | wg pubkey")
    preshared_key = subprocess.getoutput("wg genpsk")
    last_ip = 2
    if os.path.exists(WG_SERVER_CONFIG):
        with open(WG_SERVER_CONFIG, 'r') as f:
            for line in f:
                if "AllowedIPs" in line:
                    last_ip = max(last_ip, int(line.split("=")[1].strip().split(".")[3]) + 1)
    client_ip = f"10.0.0.{last_ip}"

    client_conf = f"""[Interface]
PrivateKey = {priv_key}
Address = {client_ip}/24
DNS = 8.8.8.8

[Peer]
PublicKey = 1KB2CmDZ/KxAufzXPS109CROiYPHPfO6md2yiEViJXI=
PresharedKey = {preshared_key}
Endpoint = 185.58.115.221:64797
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""

    server_peer = f"""
[Peer]
PublicKey = {pub_key}
PresharedKey = {preshared_key}
AllowedIPs = {client_ip}/32
"""
    with open(WG_SERVER_CONFIG, 'a') as f:
            f.write(server_peer)

    subprocess.run(["sudo", "wg-quick", "down", "wg0"], check=False)
    subprocess.run(["sudo", "wg-quick", "up", "wg0"], check=False)

    return client_conf, client_ip

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🔐 <b>WireGuard Config Bot</b>\n\n"
        "Доступные команды:\n"
        "/create &lt;name&gt; - Создать конфиг\n"
        "/revoke &lt;name&gt; - Удалить клиента\n"
        "/list - Список активных пиров",
        parse_mode=ParseMode.HTML
    )
@dp.message(Command("create"))
async def cmd_create(message: types.Message):    
    if not message.text.split()[1:]:
        return await message.answer("Укажите имя клиента: /create имя_клиента")
    
    client_name = message.text.split()[1]
    config, ip = generate_keys(client_name)

    conf_path = f"/tmp/{client_name}.conf"
    with open(conf_path, 'w') as f:
        f.write(config)

    await message.reply_document(
        FSInputFile(conf_path, filename=f"wg_{client_name}.conf"),
        caption=f"🔑 Конфиг для {client_name} (IP: {ip})"
    )
    # Сохраняем во временный файл
    conf_path = f"/tmp/{client_name}.conf"
    with open(conf_path, 'w') as f:
        f.write(config)

    qr_path = f"/tmp/{client_name}.png"
    subprocess.run(f"qrencode -o {qr_path} < {conf_path}", shell=True)
    await message.reply_photo(FSInputFile(qr_path))
    
    # Удаляем временные файлы
    os.remove(conf_path)
    os.remove(qr_path)

@dp.message(Command("list"))
async def cmd_list(message: types.Message):    
    peers = subprocess.getoutput("sudo wg show wg0")
    await message.answer(f"<pre>{peers}</pre>", parse_mode=ParseMode.HTML)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Я работаю! Скоро обновление...")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
