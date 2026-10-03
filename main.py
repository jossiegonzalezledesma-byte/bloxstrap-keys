import os
import sys
import threading
import time

# Agregar directorio actual
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from api_server import run_server
from bot import bot, BOT_TOKEN

def start_api():
    print("[*] Iniciando Servidor API...")
    run_server()

def main():
    print("=" * 60)
    print("  BLOSTRAP 24/7 CLOUD SERVER & DISCORD BOT")
    print("=" * 60)
    
    # 1. Iniciar API Server en un hilo secundario
    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()
    time.sleep(1)

    # 2. Iniciar Bot de Discord en el hilo principal
    token = os.environ.get("DISCORD_BOT_TOKEN", BOT_TOKEN)
    if not token or token == "PEGA_AQUI_EL_TOKEN_DE_TU_BOT" or token == "TU_TOKEN_AQUI":
        print("[!] Advertencia: DISCORD_BOT_TOKEN no configurado.")
    else:
        print("[*] Conectando Bot de Discord a los servidores...")
        bot.run(token)

if __name__ == "__main__":
    main()
