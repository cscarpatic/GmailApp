# GoogleApp - Setup Completo

## 📋 Panoramica

**GoogleApp** è un'applicazione FastAPI che fornisce accesso a Gmail e Google Calendar attraverso:
1. **REST API** - Accesso HTTP diretto (porta 8011)
2. **MCP Server** - Integrazione con AI agents (Claude Desktop, Agent Zero)

---

## 🚀 Quick Start

### 1. Verifica Servizio Attivo

```bash
sudo systemctl status GoogleApp.service
curl http://127.0.0.1:8011/
```

Risposta attesa: `{"message":"Benvenuto nella Google API Web App!"}`

### 2. Accesso Pubblico

```
https://cscarpa-vps.eu/GoogleApp/
```

---

## 📡 Endpoints Disponibili

### **Autenticazione**
- `GET /authenticate` - Avvia OAuth flow
- `GET /oauth2callback` - Callback OAuth

### **Gmail** (prefisso `/gmail/`)
- `GET /gmail/read-emails` - Leggi e filtra email
- `POST /gmail/write-and-send-email` - Invia email (JSON body + file paths)
- `POST /gmail/write-and-send-email-with-uploads` - Invia email (form-data + upload)
- `GET /gmail/download-attachments/{message_id}` - Scarica allegati

### **Calendar** (prefisso `/calendar/`)
- `POST /calendar/create-reminder` - Crea evento calendario
- `GET /calendar/read-reminders` - Leggi eventi
- `DELETE /calendar/remove-reminder?event_id={id}` - Elimina evento

### **Health**
- `GET /health/token` - Diagnostica stato token (mancante/non valido/rete/ok)

---

## 🔐 Autenticazione API

**Tutti gli endpoint** (tranne `/`, `/authenticate`, `/oauth2callback`) richiedono:

```bash
Header: X-API-Key: GoogleApp_SecureKey_2025_Cscarpa_VPS_Protection
```

**Esempio:**
```bash
curl -H "X-API-Key: GoogleApp_SecureKey_2025_Cscarpa_VPS_Protection" \
  https://cscarpa-vps.eu/GoogleApp/gmail/read-emails
```

---

## 🤖 MCP Server (per AI Agents)

### Setup per Claude Desktop

1. **Apri config file:**
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. **Aggiungi configurazione:**

```json
{
  "mcpServers": {
    "google-api": {
      "command": "python3",
      "args": [
        "/var/www/ai/GoogleApp/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/var/www/ai/GoogleApp/venv/lib/python3.12/site-packages"
      }
    }
  }
}
```

3. **Riavvia Claude Desktop**

4. **Verifica strumenti disponibili** (icona 🔌):
   - read_emails
   - send_email
   - download_attachments
   - create_calendar_reminder
   - read_calendar_reminders
   - delete_calendar_reminder

### Setup per Agent Zero

```json
{
  "mcp_servers": {
    "google": {
      "command": ["python3", "/var/www/ai/GoogleApp/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/var/www/ai/GoogleApp/venv/lib/python3.12/site-packages"
      }
    }
  }
}
```

---

## 🛠️ Manutenzione

### Riavviare il Servizio

```bash
sudo systemctl restart GoogleApp.service
```

### Vedere i Log

```bash
sudo journalctl -u GoogleApp.service -f
```

### Testare gli Endpoint

```bash
# Test homepage
curl http://127.0.0.1:8011/

# Test Gmail (con API key)
curl -H "X-API-Key: GoogleApp_SecureKey_2025_Cscarpa_VPS_Protection" \
  http://127.0.0.1:8011/gmail/read-emails
```

### Aggiornare Dipendenze

```bash
cd /var/www/ai/GoogleApp
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart GoogleApp.service
```

---

## 📂 Struttura File

```
/var/www/ai/GoogleApp/
├── main.py                    # FastAPI app principale
├── mcp_server.py              # MCP server per AI agents
├── requirements.txt           # Dipendenze Python
├── tests/                     # Test automatici (unittest)
├── archive/legacy/            # File storici/legacy non usati a runtime
├── .env                       # Configurazione (API keys, paths)
├── token.json                 # OAuth tokens Google
├── tmp/                       # File temporanei e allegati
├── venv/                      # Virtual environment Python
├── CLAUDE.md                  # Documentazione progetto
├── MCP_SETUP.md               # Guida setup MCP
├── SETUP_COMPLETO.md          # Questa guida
└── mcp_config_example.json    # Esempio config Claude Desktop
```

---

## 🔧 Configurazione Avanzata

### Variabili d'Ambiente (.env)

```bash
GOOGLE_CREDENTIALS={"web":{...}}           # Credenziali OAuth Google
TOKEN_FILE=/var/www/ai/GoogleApp/token.json
BASE_URL=https://cscarpa-vps.eu/GoogleApp
API_KEY=GoogleApp_SecureKey_2025_Cscarpa_VPS_Protection
```

### Nginx Reverse Proxy

```nginx
location /GoogleApp/ {
    proxy_pass http://127.0.0.1:8011/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Systemd Service

File: `/etc/systemd/system/GoogleApp.service`

```ini
[Unit]
Description=Hypercorn instance to serve GoogleApp (Gmail & Calendar API)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/ai/GoogleApp
Environment="PATH=/var/www/ai/GoogleApp/venv/bin"
ExecStart=/var/www/ai/GoogleApp/venv/bin/hypercorn main:app --bind 0.0.0.0:8011

[Install]
WantedBy=multi-user.target
```

---

## 🧪 Test Completo

### 1. Test REST API

```bash
# Homepage
curl http://127.0.0.1:8011/

# Diagnostica token
curl -H "X-API-Key: GoogleApp_SecureKey_2025_Cscarpa_VPS_Protection" \
  http://127.0.0.1:8011/health/token

# Leggi email (con autenticazione)
curl -H "X-API-Key: GoogleApp_SecureKey_2025_Cscarpa_VPS_Protection" \
  "http://127.0.0.1:8011/gmail/read-emails?Label=INBOX"

# Invia email
curl -X POST \
  -H "X-API-Key: GoogleApp_SecureKey_2025_Cscarpa_VPS_Protection" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "test@example.com",
    "subject": "Test",
    "body": "Test email"
  }' \
  http://127.0.0.1:8011/gmail/write-and-send-email
```

### 1b. Test automatici

```bash
cd /var/www/ai/GoogleApp
source venv/bin/activate
python -m unittest discover -s tests -p 'test_*.py' -v
```

### 2. Test MCP Server

```bash
cd /var/www/ai/GoogleApp
source venv/bin/activate
python3 mcp_server.py
# Ctrl+C per uscire
```

Output atteso:
```
INFO:google-mcp-server:Starting Google MCP Server...
INFO:google-mcp-server:Connecting to FastAPI backend at http://127.0.0.1:8011
```

---

## 🐛 Troubleshooting

### Il servizio non parte

```bash
sudo systemctl status GoogleApp.service
sudo journalctl -u GoogleApp.service -n 50
```

### Errori OAuth

1. Riautenticare: `https://cscarpa-vps.eu/GoogleApp/authenticate`
2. Verificare `token.json` esiste: `ls -la /var/www/ai/GoogleApp/token.json`

### MCP Server non funziona

1. Verificare Python path:
   ```bash
   ls /var/www/ai/GoogleApp/venv/lib/python3.12/site-packages/mcp
   ```

2. Testare manualmente:
   ```bash
   cd /var/www/ai/GoogleApp
   venv/bin/python3 mcp_server.py
   ```

3. Verificare FastAPI risponde:
   ```bash
   curl http://127.0.0.1:8011/
   ```

### Errori di permessi

```bash
sudo chown -R www-data:www-data /var/www/ai/GoogleApp/
sudo systemctl restart GoogleApp.service
```

---

## 📞 Integrazione con Altri Servizi

GoogleApp è utilizzato da:

- **Classeviva** - Notifiche email per slot colloqui
- **VPN Manager** - Alert via email per token scaduti
- **Parser** - Salvataggio file in `/tmp/`
- **Archiver** - Lettura file da processare

**Nota:** Tutti questi servizi sono stati aggiornati per usare i nuovi endpoint `/gmail/` e `/calendar/`.

---

## 🔄 Aggiornamenti Recenti

### v2.0 - Ottobre 2025
- ✅ Rinominato da GmailApp a GoogleApp
- ✅ Endpoints organizzati con prefissi `/gmail/` e `/calendar/`
- ✅ Porta fissa 8011
- ✅ MCP Server integrato per AI agents
- ✅ Documentazione completa aggiornata
- ✅ Tutti i servizi dipendenti aggiornati

---

## 📚 Documentazione Aggiuntiva

- **CLAUDE.md** - Istruzioni per Claude Code
- **MCP_SETUP.md** - Setup dettagliato MCP con troubleshooting
- **README.md** (in `/var/www/ai/`) - Overview di tutti i servizi

---

**GoogleApp v2.0** | Porta: 8011 | URL: https://cscarpa-vps.eu/GoogleApp/
