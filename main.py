import os
import requests
import firebase_admin
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from firebase_admin import credentials, db
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# Configuración de variables
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

# Intentar conectar con Firebase
cred_path = "/etc/secrets/firebase_credentials.json" if os.path.exists("/etc/secrets/firebase_credentials.json") else "firebase_credentials.json"

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://fog-astra-default-rtdb.firebaseio.com/'
        })
except Exception as e:
    print(f"Error Firebase: {e}")

def get_html_response(titulo, mensaje, color):
    return f"""
    <html>
        <head>
            <style>
                body {{ background-color: #0a0a0a; color: {color}; font-family: 'Courier New', monospace; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
                .container {{ border: 2px solid {color}; padding: 40px; text-align: center; box-shadow: 0 0 20px {color}; background: rgba(0,0,0,0.9); }}
                h1 {{ margin: 0; font-size: 2em; }}
                p {{ color: #888; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{titulo}</h1>
                <p>{mensaje}</p>
                <p style="font-size: 0.8em;">Astra Security System v2.1</p>
            </div>
        </body>
    </html>
    """

@app.get("/callback")
async def callback(code: str):
    try:
        # 1. Obtener Token
        r = requests.post('https://discord.com/api/v10/oauth2/token', data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI
        })
        token_data = r.json()
        
        if "access_token" not in token_data:
            return HTMLResponse(get_html_response("ERROR", "No se pudo validar con Discord", "#ffcc00"))

        token = token_data['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # 2. Obtener datos del usuario
        user_info = requests.get('https://discord.com/api/v10/users/@me', headers=headers).json()
        guilds = requests.get('https://discord.com/api/v10/users/@me/guilds', headers=headers).json()

        # 3. Revisar Blacklist (CON PROTECCIÓN)
        ref = db.reference('blacklist_servers')
        blacklist = ref.get()
        
        # Si la blacklist no existe, la creamos vacía para que no de error
        if blacklist is None:
            blacklist = {}

        enemigos_encontrados = []
        for g in guilds:
            if str(g['id']) in blacklist:
                enemigos_encontrados.append(g['name'])

        if enemigos_encontrados:
            # Guardar reporte
            db.reference(f'reportes_insides/{user_info["id"]}').set({
                "usuario": user_info['username'],
                "servidores_detectados": enemigos_encontrados
            })
            return HTMLResponse(get_html_response("ACCESO DENEGADO", "Se detectaron servidores enemigos", "#ff0033"))

        return HTMLResponse(get_html_response("VERIFICADO", "Acceso concedido correctamente", "#00ffff"))

    except Exception as e:
        # Esto nos dirá el error real en la pantalla
        return HTMLResponse(get_html_response("FALLO TÉCNICO", f"Detalle: {str(e)}", "#ffaa00"))