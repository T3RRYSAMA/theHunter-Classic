import discord
from discord import app_commands
import requests
from bs4 import BeautifulSoup
import os
import asyncio
from flask import Flask
from threading import Thread

# 1. SERVIDOR WEB NATIVO
app = Flask('')

@app.route('/')
def home():
    return "¡Bot de Discord en línea!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. CONFIGURACIÓN DE DISCORD
TOKEN = os.environ.get('DISCORD_TOKEN')

class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        print(f'-> Bot conectado exitosamente como {self.user}')
        try:
            synced = await self.tree.sync()
            print(f"-> Se sincronizaron {len(synced)} comando(s).")
        except Exception as e:
            print(f"-> Error sincronizando: {e}")

client = MyBot()

def buscar_en_tabla(termino_busqueda):
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQtxyD8vW8K5yRaI53IpO2zu_seN9Zqq-lvFMWkQj6egxfs6cYGOQ-Rn1GABbij3X2_tACiFoVMT3jo/pubhtml?gid=1783876917"
    try:
        response = requests.get(url)
        if response.status_code != 200: return "Error al acceder a la tabla."
        soup = BeautifulSoup(response.text, 'html.parser')
        for fila in soup.find_all('tr'):
            celdas = [c.text.strip() for c in fila.find_all('td')]
            if any(termino_busqueda.lower() in cld.lower() for cld in celdas):
                try:
                    return f"El mejor **{celdas[0]}** es de **{celdas[1]}** con {celdas[2]} puntos, el máximo es de {celdas[3]} puntos."
                except IndexError: continue
        return f"No encontré información sobre '{termino_busqueda}'."
    except Exception as e:
        return f"Error: {str(e)}"

@client.tree.command(name="bot", description="Busca estadísticas en la tabla")
@app_commands.describe(buscar="Término a buscar")
async def bot_command(interaction: discord.Interaction, buscar: str):
    await interaction.response.defer()
    await interaction.followup.send(buscar_en_tabla(buscar))

# 3. ARRANQUE SIMULTÁNEO SEGURO
if __name__ == "__main__":
    # Arrancamos la web en un hilo separado antes del bot
    Thread(target=run_web).start()
    
    # Arrancamos el bot en el hilo principal
    if TOKEN:
        client.run(TOKEN)
    else:
        print("Falta la variable DISCORD_TOKEN en Render.")
