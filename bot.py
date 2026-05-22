import discord
from discord import app_commands
import requests
from bs4 import BeautifulSoup
import os
import asyncio
from flask import Flask
from threading import Thread

# ==========================================
# 1. SERVIDOR WEB NATIVO (Para Render)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "¡Bot de Discord en línea!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 2. CONFIGURACIÓN DE DISCORD
# ==========================================
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
            print(f"-> Se sincronizaron {len(synced)} comando(s) correctamente.")
        except Exception as e:
            print(f"-> Error sincronizando comandos: {e}")

client = MyBot()

# ==========================================
# 3. LÓGICA DE BÚSQUEDA MEJORADA (Flexible)
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
            # Extraemos el texto de cada celda quitando espacios vacíos
            celdas = [celda.text.strip() for celda in fila.find_all('td') if celda.text.strip()]
            
            if not celdas:
                continue
                
            # Si el término coincide con alguna celda de esta fila
            if any(termino_busqueda.lower() in cld.lower() for cld in celdas):
                # Unimos todos los datos de la fila con una barra separadora
                resultado_formateado = " | ".join(f"**{cld}**" for cld in celdas)
                return f"🔍 **Resultado encontrado:** {resultado_formateado}"
                    
        return f"❌ No encontré información sobre '{termino_busqueda}' en la tabla."
        
    except Exception as e:
        return f"⚠️ Error interno al procesar la tabla: {str(e)}"

# ==========================================
# 4. COMANDO DEL BOT
# ==========================================
@client.tree.command(name="bot", description="Busca estadísticas en la tabla")
@app_commands.describe(buscar="Término o animal a buscar")
async def bot_command(interaction: discord.Interaction, buscar: str):
    await interaction.response.defer()
    resultado = buscar_en_tabla(buscar)
    await interaction.followup.send(resultado)

# ==========================================
# 5. CONTROL DE ARRANQUE SIMULTÁNEO
# ==========================================
if __name__ == "__main__":
    # Arrancamos la web Flask en un hilo secundario
    Thread(target=run_web).start()
    
    # Control e inicio del bot en el hilo principal
    if not TOKEN:
        print("❌ CRÍTICO: La variable DISCORD_TOKEN está vacía en Render.")
    else:
        print(f"🔹 Intentando conectar a Discord... (Longitud del token: {len(TOKEN)} caracteres)")
        try:
            client.run(TOKEN)
        except Exception as e:
            print(f"❌ El proceso del bot falló al iniciar: {e}")
