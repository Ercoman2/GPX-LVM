import os
import io
import re
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import ctranslate2
import pyonmttok
from huggingface_hub import snapshot_download

# CONFIGURACIÓ
INPUT_FOLDER_ID = "1GZsLfYHcS3vLnQNNXys3ObkO4G7AZqxN"
OUTPUT_FOLDER_ID = "1maaBuxjxzGkVQetrdI-RfmxTte81yIWr"
YOUR_GOOGLE_EMAIL = "enricluzan@gmail.com"

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN")

# Autenticació Google Drive
creds = Credentials(
    token=None,
    refresh_token=REFRESH_TOKEN,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    scopes=["https://www.googleapis.com/auth/drive"]
)
creds.refresh(Request())
service = build("drive", "v3", credentials=creds)

# 1. Trobar l'únic fitxer SRT a la carpeta d'entrada
results = service.files().list(
    q=f"'{INPUT_FOLDER_ID}' in parents and trashed=false",
    fields="files(id, name)"
).execute()
files = results.get("files", [])
if len(files) == 0:
    print("No s'ha trobat cap fitxer SRT a la carpeta d'entrada")
    exit()
elif len(files) > 1:
    print("Hi ha més d'un fitxer SRT, es processarà només el primer")
file = files[0]
file_id = file["id"]
file_name = file["name"]
print(f"Fitxer SRT trobat: {file_name}")

# 2. Baixar el fitxer SRT localment
request = service.files().get_media(fileId=file_id)
fh = io.FileIO(file_name, "wb")
downloader = MediaIoBaseDownload(fh, request)
done = False
while not done:
    status, done = downloader.next_chunk()
fh.close()
print(f"✅ Fitxer SRT baixat localment: {file_name}")

# 3. Descarregar i preparar model Aina català->castellà
print("🔄 Descarregant i preparant model Aina català->castellà...")
model_dir_es = snapshot_download(repo_id="projecte-aina/aina-translator-ca-es", revision="main")
tokenizer_es = pyonmttok.Tokenizer(mode="none", sp_model_path=model_dir_es + "/spm.model")
translator_es = ctranslate2.Translator(model_dir_es)

# 3b. Descarregar i preparar model Aina català->anglès
print("🔄 Descarregant i preparant model Aina català->anglès...")
model_dir_en = snapshot_download(repo_id="projecte-aina/aina-translator-ca-en", revision="main")
tokenizer_en = pyonmttok.Tokenizer(mode="none", sp_model_path=model_dir_en + "/spm.model")
translator_en = ctranslate2.Translator(model_dir_en)

# Funció per traduir línies d’un fitxer SRT amb un model donat
def translate_srt_lines(lines, tokenizer, translator):
    output_lines = []
    for line in lines:
        if re.match(r"^\d+$", line.strip()) or re.match(r"^\d{2}:\d{2}:\d{2},\d{3} -->", line) or line.strip() == "":
            output_lines.append(line)
        else:
            tokens = tokenizer.tokenize(line.strip())[0]
            translated = translator.translate_batch([tokens])
            detokenized = tokenizer.detokenize(translated[0][0]["tokens"])
            output_lines.append(detokenized + "\n")
    return output_lines

# 4. Carregar SRT original
with open(file_name, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 5. Traduir a castellà
output_lines_es = translate_srt_lines(lines, tokenizer_es, translator_es)
output_file_es = "es.srt"
with open(output_file_es, "w", encoding="utf-8") as f_out:
    f_out.writelines(output_lines_es)
print(f"✅ Traducció a castellà completada i guardada a {output_file_es}")

# 6. Traduir a anglès
output_lines_en = translate_srt_lines(lines, tokenizer_en, translator_en)
output_file_en = "en.srt"
with open(output_file_en, "w", encoding="utf-8") as f_out:
    f_out.writelines(output_lines_en)
print(f"✅ Traducció a anglès completada i guardada a {output_file_en}")

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


# 5. Pujar el fitxer traduït a Google Drive a la carpeta de sortida
file_metadata = {"name": output_file, "parents": [OUTPUT_FOLDER_ID]}
media = MediaFileUpload(output_file, resumable=True)
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
file_id_out = response.get("id")
print(f"☁️ Fitxer {output_file} pujat a Drive amb ID: {file_id_out}")

# 8. Pujar fitxer anglès a Drive
file_metadata_en = {"name": output_file_en, "parents": [OUTPUT_FOLDER_ID]}
media_en = MediaFileUpload(output_file_en, resumable=True)
request_en = service.files().create(
    body=file_metadata_en,
    media_body=media_en,
    fields="id"
)
response = None
while response is None:
    status, response = request_en.next_chunk()
    if status:
        print(f"☁️ Pujant {int(status.progress() * 100)}% anglès")
file_id_out_en = response.get("id")
print(f"☁️ Fitxer {output_file_en} pujat a Drive amb ID: {file_id_out_en}")
