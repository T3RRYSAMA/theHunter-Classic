import discord
from discord import app_commands
import requests
import csv
import os
import asyncio
from flask import Flask
from multiprocessing import Process

# ==========================================
# 1. SERVIDOR WEB CON PANEL DE CONTROL
# ==========================================
# Nota: Al usar multiprocess, Flask corre aislado para no bloquear a Discord
app = Flask('')

@app.route('/')
def home():
    # Renderizamos una estructura HTML liviana pero efectiva
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Panel de Control - RI2</title>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background-color: #f4f6f9; color: #333; }
            .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); max-width: 650px; margin: 0 auto; }
            h1 { color: #2c3e50; border-bottom: 2px solid #f1f3f5; padding-bottom: 15px; margin-top: 0; }
            .metric { margin: 18px 0; font-size: 16px; display: flex; justify-content: space-between; border-bottom: 1px dashed #f1f3f5; padding-bottom: 8px; }
            .label { font-weight: bold; color: #7f8c8d; }
            .value { color: #2980b9; font-family: monospace; font-size: 15px; text-align: right; }
            .success { color: #27ae60; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🛠️ Servidor Activo (RI2)</h1>
            <div class="metric"><span class="label">Estado del Entorno:</span> <span class="success">ONLINE 🟢</span></div>
            <div class="metric"><span class="label">Motor Web:</span> <span class="value">Aislado mediante Multiprocess</span></div>
            <div class="metric"><span class="label">Monitoreo Render:</span> <span class="value">Recibiendo pings correctamente</span></div>
        </div>
    </body>
    </html>
    """
    return html

def run_web():
    port = int(os.environ.get("PORT", 8080))
    # Desactivamos el reloader para evitar ejecuciones dobles en servidores cloud
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

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
# 3. LÓGICA DE DETECCIÓN DE DATOS
# ==========================================
def buscar_en_tabla(termino_busqueda, usuario_discord):
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQtxyD8vW8K5yRaI53IpO2zu_seN9Zqq-lvFMWkQj6egxfs6cYGOQ-Rn1GABbij3X2_tACiFoVMT3jo/pub?gid=1783876917&output=csv"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    
    jugadores = ["Alexor", "br1b3b3", "Cecinauta", "Chulen", "Guiyerom", "T3RRYSAMA", "ToraCRF", "VittoSca"]
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return f"No se pudo acceder a la tabla (Status: {response.status_code})."
        
        response.encoding = 'utf-8'
        lineas = response.text.splitlines()
        
        # MODO JUGADOR
        jugador_objetivo = next((j for j in jugadores if termino_busqueda.lower() == j.lower()), None)
        
        if jugador_objetivo:
            lector_csv = csv.reader(lineas)
            animales_liderados = []
            
            for fila in lector_csv:
                if len(fila) < 2:
                    continue
                
                animal_tabla = fila[1].strip()
                max_score = -1.0
                max_player = "Nadie"
                max_score_str = "0"
                
                for i, jugador in enumerate(jugadores):
                    col_idx = 2 + i
                    if col_idx < len(fila):
                        val_str = fila[col_idx].strip()
                        try:
                            val_float = float(val_str.replace(',', '.'))
                            if val_float > max_score:
                                max_score = val_float
                                max_player = jugador
                                max_score_str = val_str
                        except ValueError:
                            continue
                
                if max_player == jugador_objetivo and max_score > -1.0:
                    animales_liderados.append(f"• **{animal_tabla}**: `{max_score_str}`")
            
            if animales_liderados:
                lista_formateada = "\n".join(animales_liderados)
                return (
                    f"👤 **Perfil de Cazador:** {jugador_objetivo}\n"
                    f"👑 Posee el puntaje más alto en **{len(animales_liderados)}** especies:\n\n{lista_formateada}"
                )
            else:
                return f"👤 **Perfil de Cazador:** {jugador_objetivo}\n❌ Actualmente no lidera el ranking en ningún animal."

        # MODO ANIMAL
        lector_csv = csv.reader(lineas)
        for fila in lector_csv:
            if len(fila) < 2:
                continue
            
            animal_tabla = fila[1].strip()
            
            if termino_busqueda.lower() in animal_tabla.lower():
                record_global = fila[0].strip()
                max_score = -1.0
                max_player = "Nadie"
                max_score_str = "0"
                
                for i, jugador in enumerate(jugadores):
                    col_idx = 2 + i
                    if col_idx < len(fila):
                        val_str = fila[col_idx].strip()
                        try:
                            val_float = float(val_str.replace(',', '.'))
                            if val_float > max_score:
                                max_score = val_float
                                max_player = jugador
                                max_score_str = val_str
                        except ValueError:
                            continue
                
                if max_score > -1.0:
                    return (
                        f"🦌 **{animal_tabla}**\n"
                        f"🥇 **Máximo Puntaje:** `{max_score_str}` — **{max_player}**\n"
                        f"🌐 *Récord global registrado:* {record_global}"
                    )
                else:
                    return f"⚠️ Encontré **{animal_tabla}**, pero no hay marcas registradas."
                    
        return f"❌ No encontré resultados para '{termino_busqueda}'."
        
    except Exception as e:
        return f"⚠️ Error interno al procesar la tabla: {str(e)}"

# ==========================================
# 4. COMANDO DEL BOT
# ==========================================
@client.tree.command(name="bot", description="Busca estadísticas de animales o jugadores")
@app_commands.describe(buscar="Escribe un animal (ej: Corzo) o un jugador (ej: T3RRYSAMA)")
async def bot_command(interaction: discord.Interaction, buscar: str):
    await interaction.response.defer()
    usuario_discord = interaction.user.display_name
    
    # Ejecutamos la búsqueda pesada de forma asíncrona usando el pool de hilos de Discord
    loop = asyncio.get_running_loop()
    resultado = await loop.run_in_executor(None, buscar_en_tabla, buscar, usuario_discord)
    
    await interaction.followup.send(resultado)

# ==========================================
# 5. CONTROL DE ARRANQUE EN PARALELO
# ==========================================
if __name__ == "__main__":
    # Arrancamos Flask en un proceso totalmente separado del sistema operativo
    proceso_web = Process(target=run_web)
    proceso_web.daemon = True
    proceso_web.start()
    
    if not TOKEN:
        print("❌ CRÍTICO: La variable DISCORD_TOKEN está vacía.")
    else:
        print(f"🔹 Iniciando núcleo de Discord...")
        try:
            client.run(TOKEN)
        except Exception as e:
            print(f"❌ El proceso del bot falló: {e}")
