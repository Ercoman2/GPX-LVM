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

# 3. Models Aina: català a altres idiomes
models = {
    "es": "projecte-aina/aina-translator-ca-es",
    "en": "projecte-aina/aina-translator-ca-en",
    "fr": "projecte-aina/aina-translator-ca-fr",
    "pt": "projecte-aina/aina-translator-ca-pt",
    "it": "projecte-aina/aina-translator-ca-it"
}

tokenizers = {}
translators = {}

print("🔄 Descarregant i preparant models...")
for lang_code, repo_id in models.items():
    print(f"Descarregant model català->{lang_code}...")
    model_dir = snapshot_download(repo_id=repo_id, revision="main")
    tokenizers[lang_code] = pyonmttok.Tokenizer(mode="none", sp_model_path=model_dir + "/spm.model")
    translators[lang_code] = ctranslate2.Translator(model_dir)

# funció per traduir el SRT mantenint timestamps i estructura
def translate_srt_lines(lines, tokenizer, translator):
    output_lines = []
    for line in lines:
        if re.match(r"^\d+$", line.strip()) or re.match(r"^\d{2}:\d{2}:\d{2},\d{3} -->", line) or line.strip() == "":
            output_lines.append(line)
        else:
            tokens = tokenizer.tokenize(line.strip())[0]
            translated = translator.translate_batch([tokens])
            # Adaptació al nou objecte TranslationResult (dep. warning)
            detokenized = tokenizer.detokenize(translated.hypotheses[0])
            output_lines.append(detokenized + "\n")
    return output_lines

# 4. Carregar SRT original
with open(file_name, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 5. Traduir, guardar i pujar per a cada idioma
for lang_code in models.keys():
    print(f"Traduint a {lang_code}...")
    output_lines = translate_srt_lines(lines, tokenizers[lang_code], translators[lang_code])
    output_file = f"{lang_code}.srt"
    with open(output_file, "w", encoding="utf-8") as f_out:
        f_out.writelines(output_lines)
    print(f"✅ Traducció a {lang_code} completada i guardada a {output_file}")

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

    # Pujar a Google Drive
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
            print(f"☁️ Pujant {int(status.progress() * 100)}% fitxer {output_file}")
    file_id_out = response.get("id")
    print(f"☁️ Fitxer {output_file} pujat a Drive amb ID: {file_id_out}")

print("Totes les traduccions completades i pujades.")
