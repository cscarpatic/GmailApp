import asyncio
import requests
from fastapi import FastAPI, Query, Request, HTTPException
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders
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
import httpx
import logging
from xml.etree import ElementTree as ET
from datetime import datetime
import html

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carica le variabili d'ambiente da .env
load_dotenv()

app = FastAPI()

# Directory temporanea per i file
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp")
os.makedirs(TEMP_DIR, exist_ok=True)

# Scopes richiesti per Gmail e YouTube
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    #"https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube", # Aggiungi questo
    "https://www.googleapis.com/auth/youtubepartner", # E questo per i sottotitoli
    "https://www.googleapis.com/auth/calendar"  # New scope for calendar reminders
]

# Percorsi di configurazione
TOKEN_FILE = os.getenv("TOKEN_FILE", "/var/www/ai/GoogleApp/token.json")
ATTACHMENT_DIR = os.getenv("ATTACHMENT_DIR", "/var/www/ai/GoogleApp/tmp/")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
BASE_URL = os.getenv("BASE_URL", "https://cscarpa-vps.eu/GoogleApp")
OAUTH_REDIRECT_URI = "https://cscarpa-vps.eu/GoogleApp/oauth2callback"

@app.get("/")
async def home():
    return {"message": "Benvenuto nella Gmail API Web App!"}

@app.get("/authenticate")
async def authenticate():
    try:
        if not GOOGLE_CREDENTIALS:
            raise HTTPException(status_code=500, detail="Credenziali mancanti. Definisci GOOGLE_CREDENTIALS in .env.")
        
        print("GOOGLE_CREDENTIALS trovate")

        temp_credentials_file = os.path.join(TEMP_DIR, "temp_credentials.json")
        with open(temp_credentials_file, "w") as f:
            f.write(GOOGLE_CREDENTIALS)
        
        print("File temporaneo credenziali salvato")

        flow = Flow.from_client_secrets_file(temp_credentials_file, scopes=SCOPES)
        flow.redirect_uri = OAUTH_REDIRECT_URI
        print(f"Redirect URI configurato: {flow.redirect_uri}")

        auth_url, _ = flow.authorization_url(
            prompt="consent",
            include_granted_scopes="true",
            access_type="offline"
        )
        print(f"Auth URL generato: {auth_url}")
        return RedirectResponse(auth_url)

    except Exception as e:
        print(f"Errore durante la generazione dell'Auth URL: {e}")
        raise HTTPException(status_code=500, detail=f"Errore durante la generazione dell'URL di autorizzazione: {str(e)}")

    finally:
        if os.path.exists(temp_credentials_file):
            os.remove(temp_credentials_file)
            print("File temporaneo credenziali rimosso")

@app.get("/oauth2callback")
async def oauth2callback(request: Request):
    try:
        print("OAuth callback chiamato")
        print(f"Query params: {request.query_params}")
        print(f"URL completo: {request.url}")

        if not GOOGLE_CREDENTIALS:
            raise HTTPException(status_code=500, detail="GOOGLE_CREDENTIALS non trovate nel file .env.")

        temp_credentials_file = os.path.join(TEMP_DIR, "temp_credentials.json")
        with open(temp_credentials_file, "w") as f:
            f.write(GOOGLE_CREDENTIALS)

        flow = Flow.from_client_secrets_file(temp_credentials_file, scopes=SCOPES)
        flow.redirect_uri = OAUTH_REDIRECT_URI

        code = request.query_params.get("code")
        if not code:
            error = request.query_params.get("error", "nessun errore specificato")
            print(f"Errore nell'OAuth callback: {error}")
            raise HTTPException(status_code=400, detail=f"Authorization code non trovato. Errore: {error}")

        print(f"Code ricevuto: {code[:10]}...")  # Stampa solo i primi 10 caratteri per sicurezza
        flow.fetch_token(code=code)

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

        return {"message": f"Autenticazione completata con successo, token salvato in {TOKEN_FILE}"}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Errore durante il callback OAuth: {str(e)}")

    finally:
        if os.path.exists(temp_credentials_file):
            os.remove(temp_credentials_file)

@app.get("/read-emails")
async def read_emails(
    Label: str = Query(None, description="Filter emails by a specific label"),
    ExcludeLabel: str = Query(None, description="Exclude emails with a specific label"),
    Subject: str = Query(None, description="Filter emails containing this word in the subject"),
    ExactSubject: str = Query(None, description="Filter emails with an exact subject"),
    HasAttachment: bool = Query(False, description="Filter emails with attachments"),
    From: str = Query(None, description="Filter emails from a specific sender"),
    Text: str = Query(None, description="Filter emails containing this text in the body")
):
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

        query_string = ""
        if Label:
            query_string += f"label:{Label} "
        if ExcludeLabel:
            query_string += f"-label:{ExcludeLabel} "
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

@app.post("/send-email")
async def send_email(
    to: str = Query(..., description="Email del destinatario"),
    subject: str = Query(..., description="Oggetto dell'email"),
    body: str = Query(..., description="Corpo del messaggio"),
    cc: str = Query(None, description="CC"),
    bcc: str = Query(None, description="BCC"),
    attachments: str = Query(None, description="Lista di filepaths separati da virgola")
):
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

        # Creazione del messaggio
        if attachments:
            message = MIMEMultipart()
            message.attach(MIMEText(body))
        else:
            message = MIMEText(body)
            
        message['to'] = to
        message['subject'] = subject
        if cc:
            message['cc'] = cc
        if bcc:
            message['bcc'] = bcc
        message['from'] = "me"

        # Aggiunta allegati
        if attachments:
            for filepath in attachments.split(','):
                if os.path.exists(filepath):
                    with open(filepath, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(filepath)}",
                    )
                    message.attach(part)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        body = {'raw': raw_message}

        # Invio del messaggio
        message = service.users().messages().send(userId="me", body=body).execute()

        return {
            "message": "Email inviata con successo",
            "message_id": message['id']
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Errore durante l'invio dell'email: {str(e)}")

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

        def extract_attachments(parts, message_id, service):
            extracted = []
            for part in parts:
                if part.get("parts"):
                    extracted.extend(extract_attachments(part.get("parts", []), message_id, service))
                else:
                    if part.get("filename") and part.get("body", {}).get("attachmentId"):
                        attachment_id = part["body"]["attachmentId"]
                        attachment = service.users().messages().attachments().get(
                            userId="me", messageId=message_id, id=attachment_id
                        ).execute()
                        file_data = base64.urlsafe_b64decode(attachment["data"].encode("UTF-8"))

                        os.makedirs(ATTACHMENT_DIR, exist_ok=True)

                        file_path = os.path.join(ATTACHMENT_DIR, part["filename"])
                        with open(file_path, "wb") as f:
                            f.write(file_data)
                        extracted.append({
                            "filename": part["filename"],
                            "file_path": file_path
                        })
            return extracted

        message = service.users().messages().get(userId="me", id=message_id).execute()
        parts = message.get("payload", {}).get("parts", [])
        attachments = extract_attachments(parts, message_id, service)

        labels = service.users().labels().list(userId="me").execute().get("labels", [])
        downloaded_label = next((label for label in labels if label["name"] == "Downloaded"), None)

        if not downloaded_label:
            new_label = {
                "name": "Downloaded",
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show"
            }
            downloaded_label = service.users().labels().create(userId="me", body=new_label).execute()

        if attachments:
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"addLabelIds": [downloaded_label["id"]]}
            ).execute()

        return {
            "attachments": attachments,
            "message": f"Allegati scaricati e label 'Downloaded' assegnata all'email." if attachments else "Nessun allegato trovato."
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Errore durante il download degli allegati: {str(e)}")

@app.get("/get-youtube-captions/{video_id}")
async def get_youtube_captions(
    video_id: str, 
    language: str = Query("en", description="Codice lingua (es: 'en', 'it')"),
    format: str = Query("srt", description="Formato di output (xml, srt, vtt)")
):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            # Prima otteniamo la pagina del video
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            response = await client.get(video_url)
            
            logger.info(f"Ottenuta risposta dalla pagina video: {response.status_code}")

            # Proviamo diversi pattern per i sottotitoli
            patterns = [
                f"https://www.youtube.com/api/timedtext?v={video_id}&lang={language}",
                f"https://www.youtube.com/api/timedtext?v={video_id}&lang={language}&fmt=srv3",
                f"https://www.youtube.com/api/timedtext?v={video_id}&lang={language}&kind=asr",
                f"https://www.youtube.com/api/timedtext?v={video_id}&lang={language}-orig",
                f"https://www.youtube.com/api/timedtext?v={video_id}&lang={language}_orig"
            ]

            for url in patterns:
                logger.info(f"Tentativo con URL: {url}")
                caption_response = await client.get(url)
                
                if caption_response.status_code == 200 and caption_response.text and "<transcript>" in caption_response.text:
                    logger.info("Sottotitoli trovati!")
                    xml_content = caption_response.text
                    
                    if format.lower() == "xml":
                        return {
                            "success": True,
                            "captions": xml_content,
                            "format": "xml",
                            "url": url
                        }
                        
                    # Parse XML content
                    try:
                        root = ET.fromstring(xml_content)
                        subtitles = []
                        
                        for i, text in enumerate(root.findall('.//text'), 1):
                            start = float(text.get('start', 0))
                            duration = float(text.get('dur', 0))
                            content = text.text if text.text else ""
                            
                            if content:  # Ignora sottotitoli vuoti
                                subtitles.append({
                                    'index': i,
                                    'start': start,
                                    'end': start + duration,
                                    'text': html.unescape(content)
                                })
                        
                        if format.lower() == "srt":
                            srt_content = ""
                            for sub in subtitles:
                                srt_content += f"{sub['index']}\n"
                                srt_content += f"{format_time_srt(sub['start'])} --> {format_time_srt(sub['end'])}\n"
                                srt_content += f"{sub['text']}\n\n"
                            
                            return {
                                "success": True,
                                "captions": srt_content,
                                "format": "srt",
                                "url": url
                            }
                        
                        elif format.lower() == "vtt":
                            vtt_content = "WEBVTT\n\n"
                            for sub in subtitles:
                                vtt_content += f"{format_time_vtt(sub['start'])} --> {format_time_vtt(sub['end'])}\n"
                                vtt_content += f"{sub['text']}\n\n"
                                
                            return {
                                "success": True,
                                "captions": vtt_content,
                                "format": "vtt",
                                "url": url
                            }
                            
                    except ET.ParseError as e:
                        logger.error(f"Errore nel parsing XML: {e}")
                        continue

            # Se arriviamo qui, non abbiamo trovato sottotitoli
            return {
                "success": False,
                "error": f"Nessun sottotitolo disponibile per la lingua {language}",
                "video_id": video_id,
                "tested_urls": patterns
            }

    except Exception as e:
        logger.error(f"Errore nel recupero dei sottotitoli: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante il recupero dei sottotitoli: {str(e)}"
        )

def format_time_srt(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds * 1000) % 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

def format_time_vtt(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds * 1000) % 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millisecs:03d}"

@app.post("/create-reminder")
async def create_reminder(
    title: str = Query(..., description="Title of the reminder"),
    description: str = Query(..., description="Description of the reminder"),
    start_time: datetime = Query(..., description="Start time in ISO format"),
    end_time: datetime = Query(..., description="End time in ISO format"),
    timezone: str = Query("UTC", description="Timezone identifier")
):
    try:
        if not os.path.exists(TOKEN_FILE):
            raise HTTPException(status_code=401, detail="Token not found. Authenticate via /authenticate.")

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

        service = build("calendar", "v3", credentials=creds)

        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': timezone,
            },
            'reminders': {
                'useDefault': True,
            },
        }

        event = service.events().insert(
            calendarId='primary',
            body=event
        ).execute()

        return {
            "message": "Reminder created successfully",
            "event_id": event['id'],
            "htmlLink": event['htmlLink']
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error creating reminder: {str(e)}")

@app.get("/read-reminders")
async def read_reminders(
    max_results: int = Query(30, description="Maximum number of events to return"),
    time_min: datetime = Query(None, description="Lower bound for event start time"),
    time_max: datetime = Query(None, description="Upper bound for event end time")
):
    try:
        if not os.path.exists(TOKEN_FILE):
            raise HTTPException(status_code=401, detail="Token not found. Authenticate via /authenticate.")

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

        service = build("calendar", "v3", credentials=creds)
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min.isoformat() + 'Z' if time_min else None,
            timeMax=time_max.isoformat() + 'Z' if time_max else None,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        return {"events": events}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error reading reminders: {str(e)}")

@app.delete("/remove-reminder")
async def remove_reminder(
    event_id: str = Query(..., description="ID of the event to remove")
):
    try:
        if not os.path.exists(TOKEN_FILE):
            raise HTTPException(status_code=401, detail="Token not found. Authenticate via /authenticate.")

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

        service = build("calendar", "v3", credentials=creds)
        service.events().delete(calendarId='primary', eventId=event_id).execute()

        return {"message": "Reminder removed successfully"}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error removing reminder: {str(e)}")

@app.get("/read-reminders")
async def read_reminders(
    max_results: int = Query(10, description="Maximum number of events to return"),
    time_min: datetime = Query(None, description="Lower bound for event start time"),
    time_max: datetime = Query(None, description="Upper bound for event end time")
):
    try:
        if not os.path.exists(TOKEN_FILE):
            raise HTTPException(status_code=401, detail="Token not found. Authenticate via /authenticate.")

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

        service = build("calendar", "v3", credentials=creds)
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min.isoformat() if time_min else None,
            timeMax=time_max.isoformat() if time_max else None,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        return {"events": events}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error reading reminders: {str(e)}")

@app.delete("/remove-reminder")
async def remove_reminder(
    event_id: str = Query(..., description="ID of the event to remove")
):
    try:
        if not os.path.exists(TOKEN_FILE):
            raise HTTPException(status_code=401, detail="Token not found. Authenticate via /authenticate.")

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

        service = build("calendar", "v3", credentials=creds)
        service.events().delete(calendarId='primary', eventId=event_id).execute()

        return {"message": "Reminder removed successfully"}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error removing reminder: {str(e)}")
    try:
        if not os.path.exists(TOKEN_FILE):
            raise HTTPException(status_code=401, detail="Token not found. Authenticate via /authenticate.")

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

        service = build("calendar", "v3", credentials=creds)

        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': timezone,
            },
            'reminders': {
                'useDefault': True,
            },
        }

        event = service.events().insert(
            calendarId='primary',
            body=event
        ).execute()

        return {
            "message": "Reminder created successfully",
            "event_id": event['id'],
            "htmlLink": event['htmlLink']
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error creating reminder: {str(e)}")

@app.get("/get-youtube-captions-by-url")
async def get_youtube_captions_by_url(
    url: str = Query(..., description="URL del video YouTube"),
    language: str = Query("en", description="Codice lingua (es: 'it', 'en')")
):
    try:
        video_id = extract_video_id(url)
        if not video_id:
            raise HTTPException(
                status_code=400,
                detail="URL YouTube non valido o ID video non trovato"
            )
            
        return await get_youtube_captions(video_id, language)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante l'elaborazione dell'URL: {str(e)}"
        )
def extract_video_id(url: str) -> str:
    """
    Estrae l'ID del video da vari formati di URL di YouTube
    """
    import re
    
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)',
        r'(?:youtube\.com\/embed\/)([\w-]+)',
        r'(?:youtube\.com\/v\/)([\w-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

async def check_and_download_emails():
    async with httpx.AsyncClient() as client:
        while True:
            try:
                response = await client.get(
                    f"{BASE_URL}/read-emails",
                    params={"HasAttachment": "yes", "ExcludeLabel": "Downloaded"}
                )

                if response.status_code == 200:
                    emails = response.json().get("emails", [])
                    if emails:
                        for email in emails:
                            # Scarica gli allegati dell'email
                            email_id = email["id"]
                            download_response = await client.get(
                                f"{BASE_URL}/download-attachments/{email_id}"
                            )
                            print(f"{BASE_URL}/download-attachments/{email_id}")
                            if download_response.status_code == 200:
                                print(f"Allegati scaricati per l'email con ID: {email_id}")
                            else:
                                print(f"Errore nel download per l'email con ID: {email_id}")
                    else:
                        print("Nessuna nuova email con allegati da scaricare.")
                else:
                    print(f"Errore nella chiamata a /read-emails: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Errore nel controllo delle email: {str(e)}")

            # Aspetta 60 minuti prima di eseguire di nuovo
            await asyncio.sleep(3600)

@app.on_event("startup")
async def startup_event():
    # Avvia la funzione di monitoraggio al momento dello startup
    asyncio.create_task(check_and_download_emails())
