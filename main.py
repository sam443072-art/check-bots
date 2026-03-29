import os
import requests
import firebase_admin
from fastapi import FastAPI, Request
from firebase_admin import credentials, db
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_credentials.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://fog-astra-default-rtdb.firebaseio.com/'
    })

@app.get("/callback")
async def callback(code: str):
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    r = requests.post('https://discord.com/api/v10/oauth2/token', data=data)
    token_data = r.json()
    
    if "access_token" not in token_data:
        return {"status": "error", "message": "Error al autenticar con Discord."}

    token = token_data['access_token']

    headers = {'Authorization': f'Bearer {token}'}
    guilds = requests.get('https://discord.com/api/v10/users/@me/guilds', headers=headers).json()
    user_info = requests.get('https://discord.com/api/v10/users/@me', headers=headers).json()

    blacklist = db.reference('blacklist_servers').get() or {}
    
    enemigos_detectados = []
    for g in guilds:
        if str(g['id']) in blacklist:
            enemigos_detectados.append(f"{g['name']} (ID: {g['id']})")

    if enemigos_detectados:
        reporte = {
            "usuario": f"{user_info['username']}#{user_info['discriminator']}",
            "user_id": user_info['id'],
            "servidores_enemigos": enemigos_detectados
        }
        db.reference(f'reportes_insides/{user_info["id"]}').set(reporte)
        
        return "❌ ACCESO DENEGADO: Se detecto que perteneces a servidores de tribus enemigas."

    return "✅ VERIFICACION EXITOSA: No se encontraron coincidencias en la lista negra."
