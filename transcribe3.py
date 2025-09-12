import os
import io
import faster-whisper
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.http import MediaFileUpload
from faster_whisper import WhisperModel


# Config
INPUT_FOLDER_ID = "1lP4O_7gzVbrguucycJuPWqmY_QgIKqxB"
OUTPUT_FOLDER_ID = "1JnxA6r8Kf4HWggUWVpoZqcd_UeSdrOpw"
YOUR_GOOGLE_EMAIL = "enricluzan@gmail.com"  # <-- posa-hi el teu email personal

# Assegura't que has guardat aquests secrets a GitHub Actions
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN")

# Autenticació OAuth (usant refresh token)
creds = Credentials(
    token=None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["https://www.googleapis.com/auth/drive"]
)

# refresca per obtenir access token
creds.refresh(Request())
service = build("drive", "v3", credentials=creds)

# 1. Trobar arxius nous a la carpeta d'entrada
results = service.files().list(
    q=f"'{INPUT_FOLDER_ID}' in parents and trashed=false",
    fields="files(id, name)"
).execute()
files = results.get("files", [])

if not files:
    print("No hi ha arxius nous")
    exit()

# 2. Baixar el primer arxiu d'àudio
file_id = files[0]["id"]
file_name = files[0]["name"]
request = service.files().get_media(fileId=file_id)
fh = io.FileIO(file_name, "wb")
downloader = MediaIoBaseDownload(fh, request)
done = False
while not done:
    status, done = downloader.next_chunk()
fh.close()
print(f"✅ Arxiu baixat: {file_name}")

def format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms == 1000:  # corregeix cas límit
        s += 1
        ms = 0
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

# 3. Transcriure amb Whisper
model_size = "projecte-aina/faster-whisper-large-v3-ca-3catparla"
model = WhisperModel(model_size, device="cpu", compute_type="int8")  # o "float16" si tens GPU
segments, info = model.transcribe(file_name, beam_size=5, task="transcribe",language="ca", word_timestamps=True)

# 4. Generar SRT
srt_lines = []
for i, seg in enumerate(segments, start=1):
    start_ts = format_timestamp(seg.start)
    end_ts = format_timestamp(seg.end)
    text = seg.text.strip()
    srt_lines.append(f"{i}")
    srt_lines.append(f"{start_ts} --> {end_ts}")
    srt_lines.append(text)
    srt_lines.append("")

srt_content = "\n".join(srt_lines)

print(f"✅ Arxiu transcrit: {file_name}")

# Fitxers de sortida
srt_file = file_name.rsplit(".", 1)[0] + ".srt"

# Escriure .srt
with open(srt_file, "w", encoding="utf-8") as f:
    f.write(srt_content)

print(f"✅ SRT creat: {srt_file}")

# Autenticació OAuth (usant refresh token)
creds = Credentials(
    token=None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["https://www.googleapis.com/auth/drive"]
)

# refresca per obtenir access token
creds.refresh(Request())
service = build("drive", "v3", credentials=creds)

# 5. Pujar a Google Drive i compartir
def upload_to_drive(local_path, parent_folder_id):
    file_metadata = {"name": os.path.basename(local_path), "parents": [parent_folder_id]}
    media = MediaFileUpload(local_path, resumable=True)
    request = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"☁️ Pujant {int(status.progress() * 100)}%")
    
    file_id = response.get("id")
    print(f"☁️ Fitxer {local_path} pujat a Drive amb ID: {file_id}")

    # Compartir amb el teu compte personal
    permission = {
        "type": "user",
        "role": "writer",
        "emailAddress": YOUR_GOOGLE_EMAIL,
    }
    service.permissions().create(fileId=file_id, body=permission).execute()
    print(f"🔗 Compartit amb {YOUR_GOOGLE_EMAIL}: https://drive.google.com/file/d/{file_id}/view")

upload_to_drive(srt_file, OUTPUT_FOLDER_ID)
