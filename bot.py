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
# 3. LÓGICA DE BÚSQUEDA MEDIANTE CSV (Corregida)
# ==========================================
def buscar_en_tabla(termino_busqueda):
    global datos_depuracion
    datos_depuracion["ultima_consulta"] = termino_busqueda
    
    # URL corregida usando el conector '&' válido para separar los parámetros de Google
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQtxyD8vW8K5yRaI53IpO2zu_seN9Zqq-lvFMWkQj6egxfs6cYGOQ-Rn1GABbij3X2_tACiFoVMT3jo/pub?gid=1783876917&output=csv"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    
    try:
        response = requests.get(url, headers=headers)
        datos_depuracion["status_tabla"] = str(response.status_code)
        
        if response.status_code != 200:
            msg_err = f"Error HTTP {response.status_code}"
            datos_depuracion["ultima_respuesta"] = msg_err
            return f"No se pudo acceder a la tabla (Status: {response.status_code})."
        
        lineas = response.text.splitlines()
        datos_depuracion["filas_detectadas"] = len(lineas)
        
        lector_csv = csv.reader(lineas)
        
        for fila in lector_csv:
            celdas_limpias = [celda.strip() for celda in fila if celda.strip()]
            
            if not celdas_limpias:
                continue
                
            if any(termino_busqueda.lower() in cld.lower() for cld in celdas_limpias):
                resultado_formateado = " | ".join(f"**{cld}**" for cld in celdas_limpias)
                respuesta = f"🔍 **Resultado encontrado:** {resultado_formateado}"
                datos_depuracion["ultima_respuesta"] = respuesta
                return respuesta
                    
        msg_vacio = f"❌ No encontré información sobre '{termino_busqueda}' en la tabla."
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
    Thread(target=run_web).start()
    
    if not TOKEN:
        print("❌ CRÍTICO: La variable DISCORD_TOKEN está vacía.")
    else:
        print(f"🔹 Intentando conectar a Discord...")
        try:
            client.run(TOKEN)
        except Exception as e:
            print(f"❌ El proceso del bot falló: {e}")
