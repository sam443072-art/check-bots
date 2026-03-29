import os
import requests
import firebase_admin
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from firebase_admin import credentials, db
from dotenv import load_dotenv

# Cargar variables de entorno del panel de Render
load_dotenv()

app = FastAPI()

# Configuración desde el panel de Environment de Render
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

# --- INICIALIZACIÓN DE FIREBASE ---
# Render guarda los "Secret Files" en /etc/secrets/ o en la raíz
cred_path = "/etc/secrets/firebase_credentials.json" if os.path.exists("/etc/secrets/firebase_credentials.json") else "firebase_credentials.json"

try:
    if not firebase_admin._apps:
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://fog-astra-default-rtdb.firebaseio.com/'
            })
            print(f"✅ Firebase conectado exitosamente desde: {cred_path}")
        else:
            print(f"❌ ERROR: No se encontró el archivo de credenciales en {cred_path}")
except Exception as e:
    print(f"❌ ERROR CRÍTICO al iniciar Firebase: {e}")

# --- DISEÑO CIBERPUNK PARA LA RESPUESTA ---
def get_html_response(mensaje, color):
    return f"""
    <html>
        <head>
            <style>
                body {{ background-color: #0a0a0a; color: {color}; font-family: 'Courier New', monospace; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
                .container {{ border: 2px solid {color}; padding: 40px; box-shadow: 0 0 20px {color}; text-align: center; background: rgba(0,0,0,0.8); }}
                h1 {{ text-transform: uppercase; letter-spacing: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{mensaje}</h1>
                <p>Astra Security System v2.1</p>
            </div>
        </body>
    </html>
    """

@app.get("/callback")
async def callback(code: str):
    try:
        # 1. Intercambiar el código de Discord por un Token de acceso
        data = {{
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI
        }}
        
        r = requests.post('https://discord.com/api/v10/oauth2/token', data=data)
        token_data = r.json()
        
        if "access_token" not in token_data:
            print(f"⚠️ Error de autenticación Discord: {token_data}")
            return HTMLResponse(content=get_html_response("Error de Autenticación", "#ff0000"), status_code=400)

        token = token_data['access_token']

        # 2. Obtener la lista de servidores y datos del usuario
        headers = {{'Authorization': f'Bearer {{token}}'}}
        guilds = requests.get('https://discord.com/api/v10/users/@me/guilds', headers=headers).json()
        user_info = requests.get('https://discord.com/api/v10/users/@me', headers=headers).json()

        # 3. Consultar la Blacklist en Firebase
        blacklist = db.reference('blacklist_servers').get() or {{}}
        
        enemigos_detectados = []
        for g in guilds:
            if str(g['id']) in blacklist:
                enemigos_detectados.append(f"{{g['name']}} (ID: {{g['id']}})")

        # 4. Resultado del escaneo
        if enemigos_detectados:
            reporte = {{
                "usuario": f"{{user_info['username']}}",
                "user_id": user_info['id'],
                "servidores_enemigos": enemigos_detectados
            }}
            db.reference(f'reportes_insides/{{user_info["id"]}}').set(reporte)
            
            return HTMLResponse(content=get_html_response("ACCESO DENEGADO: INSIDE DETECTADO", "#ff0033"))

        return HTMLResponse(content=get_html_response("VERIFICACIÓN EXITOSA: BIENVENIDO", "#00ffff"))

    except Exception as e:
        print(f"❌ ERROR EN EL PROCESO: {{e}}")
        return HTMLResponse(content=get_html_response("ERROR INTERNO DEL SISTEMA", "#ffff00"), status_code=500)