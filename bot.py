import discord
from discord import app_commands
import requests
from bs4 import BeautifulSoup
import os
from threading import Thread
from flask import Flask

# ==========================================
# 1. SERVIDOR WEB EN PARALELO (Keep-Alive)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "¡Bot de Discord en línea!"

def run_web():
    # Render asigna el puerto automáticamente en esta variable de entorno
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ==========================================
# 2. CONFIGURACIÓN DEL BOT DE DISCORD
# ==========================================
# Render leerá el Token de forma segura desde las Environment Variables
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
            # Sincroniza los comandos slash (/) con Discord
            synced = await self.tree.sync()
            print(f"-> Se sincronizaron {len(synced)} comando(s) correctamente.")
        except Exception as e:
            print(f"-> Error al sincronizar comandos: {e}")

client = MyBot()

# ==========================================
# 3. LÓGICA DE BÚSQUEDA EN GOOGLE SHEETS
# ==========================================
def buscar_en_tabla(termino_busqueda):
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQtxyD8vW8K5yRaI53IpO2zu_seN9Zqq-lvFMWkQj6egxfs6cYGOQ-Rn1GABbij3X2_tACiFoVMT3jo/pubhtml?gid=1783876917"
    
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return "No se pudo acceder a la tabla web de puntuaciones."
        
        soup = BeautifulSoup(response.text, 'html.parser')
        filas = soup.find_all('tr')
        
        for fila in filas:
            celdas = [celda.text.strip() for celda in fila.find_all('td')]
            
            # Si el término que busca el usuario coincide con alguna celda de esta fila
            if any(termino_busqueda.lower() in cld.lower() for cld in celdas):
                try:
                    # Estructura estimada de columnas: [0]Especie, [1]Jugador, [2]Puntaje, [3]Máximo
                    return f"El mejor **{celdas[0]}** es de **{celdas[1]}** con {celdas[2]} puntos, el máximo es de {celdas[3]} puntos."
                except IndexError:
                    continue
                    
        return f"No encontré información sobre '{termino_busqueda}' en la tabla."
        
    except Exception as e:
        return f"Error interno al procesar la tabla: {str(e)}"

# ==========================================
# 4. COMANDO DEL BOT (/bot <término>)
# ==========================================
@client.tree.command(name="bot", description="Busca estadísticas en la tabla interna")
@app_commands.describe(buscar="El término o animal a buscar (ej: timor)")
async def bot_command(interaction: discord.Interaction, buscar: str):
    # Avisamos a Discord que estamos procesando (evita el timeout de 3 segundos)
    await interaction.response.defer()
    
    # Realizamos la búsqueda
    resultado = buscar_en_tabla(buscar)
    
    # Respondemos en el canal de Discord
    await interaction.followup.send(resultado)

# ==========================================
# 5. EJECUCIÓN DEL PROYECTO
# ==========================================
if __name__ == "__main__":
    if not TOKEN:
        print("CRÍTICO: La variable de entorno DISCORD_TOKEN no está configurada en Render.")
    else:
        keep_alive()      # Enciende el servidor web Flask de fondo
        client.run(TOKEN) # Enciende el bot de Discord
