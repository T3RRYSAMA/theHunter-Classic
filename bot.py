import discord
from discord import app_commands
import requests
import csv
import os
import asyncio
from flask import Flask
from threading import Thread

# ==========================================
# VARIABLES GLOBALES PARA DEPURACIÓN WEB
# ==========================================
datos_depuracion = {
    "ultima_consulta": "Ninguna todavía",
    "ultima_respuesta": "Ninguna todavía",
    "status_tabla": "No consultado",
    "filas_detectadas": 0,
    "ultimo_error": "Ninguno"
}

# ==========================================
# 1. SERVIDOR WEB CON PANEL DE CONTROL
# ==========================================
app = Flask('')

@app.route('/')
def home():
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Panel de Depuración - RI2</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background-color: #f4f6f9; color: #333; }}
            .card {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); max-width: 650px; margin: 0 auto; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #f1f3f5; padding-bottom: 15px; margin-top: 0; }}
            .metric {{ margin: 18px 0; font-size: 16px; display: flex; justify-content: space-between; border-bottom: 1px dashed #f1f3f5; padding-bottom: 8px; }}
            .label {{ font-weight: bold; color: #7f8c8d; }}
            .value {{ color: #2980b9; font-family: monospace; font-size: 15px; text-align: right; max-width: 60%; }}
            .success {{ color: #27ae60; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🛠️ Panel de Depuración (RI2)</h1>
            <div class="metric"><span class="label">Estado del Bot:</span> <span class="success">ONLINE 🟢</span></div>
            <div class="metric"><span class="label">Última consulta (Discord):</span> <span class="value">{datos_depuracion['ultima_consulta']}</span></div>
            <div class="metric"><span class="label">Última respuesta:</span> <span class="value">{datos_depuracion['ultima_respuesta']}</span></div>
            <div class="metric"><span class="label">Código HTTP Google Sheets:</span> <span class="value">{datos_depuracion['status_tabla']}</span></div>
            <div class="metric"><span class="label">Filas totales detectadas:</span> <span class="value">{datos_depuracion['filas_detectadas']}</span></div>
            <div class="metric"><span class="label">Último error registrado:</span> <span class="value" style="color: #c0392b;">{datos_depuracion['ultimo_error']}</span></div>
        </div>
    </body>
    </html>
    """
    return html

def run_web():
    port = int(os.environ.get("PORT", 8080))
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
# 3. LÓGICA DE DETECCIÓN ASÍNCRONA
# ==========================================
# Ejecuta la descarga HTTP en un hilo secundario para evitar congelar el loop de Discord
def descargar_datos_sincrono():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQtxyD8vW8K5yRaI53IpO2zu_seN9Zqq-lvFMWkQj6egxfs6cYGOQ-Rn1GABbij3X2_tACiFoVMT3jo/pub?gid=1783876917&output=csv"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(url, headers=headers, timeout=10)
    response.encoding = 'utf-8'
    return response

async def buscar_en_tabla(termino_busqueda, usuario_discord):
    global datos_depuracion
    datos_depuracion["ultima_consulta"] = f"'{termino_busqueda}' por @{usuario_discord}"
    
    jugadores = ["Alexor", "br1b3b3", "Cecinauta", "Chulen", "Guiyerom", "T3RRYSAMA", "ToraCRF", "VittoSca"]
    
    try:
        # Forzamos que la descarga no bloquee de forma asíncrona
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, descargar_datos_sincrono)
        
        datos_depuracion["status_tabla"] = str(response.status_code)
        
        if response.status_code != 200:
            msg_err = f"Error HTTP {response.status_code}"
            datos_depuracion["ultima_respuesta"] = msg_err
            return f"No se pudo acceder a la tabla (Status: {response.status_code})."
        
        lineas = response.text.splitlines()
        datos_depuracion["filas_detectadas"] = len(lineas)
        
        # ----------------------------------------------------
        # MODO JUGADOR
        # ----------------------------------------------------
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
                respuesta = (
                    f"👤 **Perfil de Cazador:** {jugador_objetivo}\n"
                    f"👑 Posee el puntaje más alto en **{len(animales_liderados)}** especies:\n\n{lista_formateada}"
                )
            else:
                respuesta = f"👤 **Perfil de Cazador:** {jugador_objetivo}\n❌ Actualmente no lidera el ranking en ningún animal."
            
            datos_depuracion["ultima_respuesta"] = respuesta
            return respuesta

        # ----------------------------------------------------
        # MODO ANIMAL
        # ----------------------------------------------------
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
                    respuesta = (
                        f"🦌 **{animal_tabla}**\n"
                        f"🥇 **Máximo Puntaje:** `{max_score_str}` — **{max_player}**\n"
                        f"🌐 *Récord global registrado:* {record_global}"
                    )
                else:
                    respuesta = f"⚠️ Encontré **{animal_tabla}**, pero no hay marcas registradas."
                
                datos_depuracion["ultima_respuesta"] = respuesta
                return respuesta
                    
        msg_vacio = f"❌ No encontré resultados para '{termino_busqueda}' (no coincide con un jugador ni con un animal)."
        datos_depuracion["ultima_respuesta"] = msg_vacio
        return msg_vacio
        
    except Exception as e:
        error_str = str(e)
        datos_depuracion["ultimo_error"] = error_str
        datos_depuracion["ultima_respuesta"] = f"Fallo interno: {error_str}"
        return f"⚠️ Error interno al procesar la tabla: {error_str}"

# ==========================================
# 4. COMANDO DEL BOT
# ==========================================
@client.tree.command(name="bot", description="Busca estadísticas de animales o jugadores")
@app_commands.describe(buscar="Escribe un animal (ej: Corzo) o un jugador (ej: T3RRYSAMA)")
async def bot_command(interaction: discord.Interaction, buscar: str):
    await interaction.response.defer()
    usuario_discord = interaction.user.display_name
    
    # Llamamos a la lógica asíncrona unificada
    resultado = await buscar_en_tabla(buscar, usuario_discord)
    await interaction.followup.send(resultado)

# ==========================================
# 5. CONTROL DE ARRANQUE EN PARALELO
# ==========================================
if __name__ == "__main__":
    # Flask vuelve a correr en un hilo secundario tradicional para compartir memoria global
    proceso_web = Thread(target=run_web)
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
