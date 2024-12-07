from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import os
import json
import google.oauth2.credentials
import traceback
import base64

# Carica le variabili d'ambiente da .env
load_dotenv()

app = FastAPI()

# Scopes richiesti per Gmail
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify"
]

# Percorsi di configurazione
TOKEN_FILE = os.getenv("TOKEN_FILE", "/Users/carloscarpati/AI_Projects/GmailApp/token.json")
ATTACHMENT_DIR = os.getenv("ATTACHMENT_DIR", "/Users/carloscarpati/AI_Projects/GmailApp/tmp")  # Default to /tmp/
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")

@app.get("/")
async def home():
    return {"message": "Benvenuto nella Gmail API Web App!"}

@app.get("/authenticate")
async def authenticate():
    # Controlla che GOOGLE_CREDENTIALS sia impostato
    if not GOOGLE_CREDENTIALS:
        raise HTTPException(status_code=500, detail="Credenziali mancanti. Definisci GOOGLE_CREDENTIALS in .env.")

    # Salva le credenziali in un file temporaneo
    temp_credentials_file = "temp_credentials.json"
    with open(temp_credentials_file, "w") as f:
        f.write(GOOGLE_CREDENTIALS)

    # Inizializza il flusso OAuth
    flow = Flow.from_client_secrets_file(temp_credentials_file, scopes=SCOPES)
    flow.redirect_uri = "http://localhost:8000/oauth2callback"

    # Ottieni l'URL di autorizzazione
    auth_url, _ = flow.authorization_url(prompt="consent", include_granted_scopes="true")

    # Rimuovi il file temporaneo
    os.remove(temp_credentials_file)

    return RedirectResponse(auth_url)

@app.get("/oauth2callback")
async def oauth2callback(request: Request):
    try:
        # Controlla che GOOGLE_CREDENTIALS sia definito
        if not GOOGLE_CREDENTIALS:
            raise HTTPException(status_code=500, detail="GOOGLE_CREDENTIALS non trovate nel file .env.")

        # Salva le credenziali in un file temporaneo
        temp_credentials_file = "temp_credentials.json"
        with open(temp_credentials_file, "w") as f:
            f.write(GOOGLE_CREDENTIALS)

        # Inizializza il flusso OAuth
        flow = Flow.from_client_secrets_file(temp_credentials_file, scopes=SCOPES)
        flow.redirect_uri = "http://localhost:8000/oauth2callback"

        # Recupera il codice di autorizzazione dalla richiesta
        code = request.query_params.get("code")
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code non trovato.")

        # Completa il flusso di autorizzazione
        flow.fetch_token(code=code)

        # Salva il token in un file
        credentials = flow.credentials
        credentials_dict = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }

        with open(TOKEN_FILE, "w") as token_file:
            json.dump(credentials_dict, token_file)

        # Rimuovi il file temporaneo
        os.remove(temp_credentials_file)

        return {"message": f"Autenticazione completata con successo, token salvato in {TOKEN_FILE}"}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Errore durante il callback OAuth: {str(e)}")

@app.get("/read-emails")
async def read_emails(
    Label: str = Query(None, description="Filter emails by a specific label"),
    Subject: str = Query(None, description="Filter emails containing this word in the subject"),
    ExactSubject: str = Query(None, description="Filter emails with an exact subject"),
    HasAttachment: bool = Query(False, description="Filter emails with attachments"),
    From: str = Query(None, description="Filter emails from a specific sender"),
    Text: str = Query(None, description="Filter emails containing this text in the body")
):
    try:
        # Verifica che il file token.json esista
        if not os.path.exists(TOKEN_FILE):
            raise HTTPException(status_code=401, detail="Token non trovato. Autenticati tramite /authenticate.")

        # Carica le credenziali
        with open(TOKEN_FILE, "r") as token:
            creds_dict = json.load(token)

        creds = google.oauth2.credentials.Credentials(
            token=creds_dict["token"],
            refresh_token=creds_dict["refresh_token"],
            token_uri=creds_dict["token_uri"],
            client_id=creds_dict["client_id"],
            client_secret=creds_dict["client_secret"],
            scopes=creds_dict["scopes"]
        )

        # Costruisci il servizio Gmail
        service = build("gmail", "v1", credentials=creds)

        # Prepara la query string
        query_string = ""

        if Label:
            query_string += f"label:{Label} "
        if Subject:
            query_string += f"subject:{Subject} "
        if ExactSubject:
            query_string += f'subject:"{ExactSubject}" '
        if HasAttachment:
            query_string += "has:attachment "
        if From:
            query_string += f"from:{From} "
        if Text:
            query_string += f'"{Text}" '

        # Recupera le email
        results = service.users().messages().list(userId="me", maxResults=10, q=query_string.strip()).execute()
        messages = results.get("messages", [])
        emails = []

        for message in messages:
            msg = service.users().messages().get(userId="me", id=message["id"]).execute()
            payload = msg.get("payload", {})
            headers = payload.get("headers", [])
            subject = next((header["value"] for header in headers if header["name"] == "Subject"), "No Subject")
            sender = next((header["value"] for header in headers if header["name"] == "From"), "Unknown Sender")
            labels = msg.get("labelIds", [])

            emails.append({
                "id": msg["id"],
                "snippet": msg["snippet"],
                "subject": subject,
                "from": sender,
                "labels": labels
            })

        return {"emails": emails}

    except Exception as e:
        traceback.print_exc()
        return {"error": f"Error: {str(e)}"}

@app.get("/download-attachments/{message_id}")
async def download_attachments(message_id: str):
    try:
        if not os.path.exists(TOKEN_FILE):
            raise HTTPException(status_code=401, detail="Token non trovato. Autenticati tramite /authenticate.")

        with open(TOKEN_FILE, "r") as token:
            creds_dict = json.load(token)

        creds = google.oauth2.credentials.Credentials(
            token=creds_dict["token"],
            refresh_token=creds_dict["refresh_token"],
            token_uri=creds_dict["token_uri"],
            client_id=creds_dict["client_id"],
            client_secret=creds_dict["client_secret"],
            scopes=creds_dict["scopes"]
        )

        service = build("gmail", "v1", credentials=creds)
        message = service.users().messages().get(userId="me", id=message_id).execute()
        parts = message.get("payload", {}).get("parts", [])
        attachments = []

        os.makedirs(ATTACHMENT_DIR, exist_ok=True)

        for part in parts:
            if part.get("filename") and "attachmentId" in part.get("body", {}):
                attachment_id = part["body"]["attachmentId"]
                attachment = service.users().messages().attachments().get(
                    userId="me", messageId=message_id, id=attachment_id
                ).execute()
                file_data = base64.urlsafe_b64decode(attachment["data"].encode("UTF-8"))
                file_path = os.path.join(ATTACHMENT_DIR, part["filename"])
                with open(file_path, "wb") as f:
                    f.write(file_data)
                attachments.append({
                    "filename": part["filename"],
                    "file_path": file_path
                })

        return {"attachments": attachments}

    except Exception as e:
        traceback.print_exc()
        return {"error": f"Error: {str(e)}"}
