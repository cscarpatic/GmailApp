# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Google API Web Application built with FastAPI that provides email management and Google Calendar integration. The application serves as:
- **REST API** for direct HTTP access to Gmail/Calendar operations
- **MCP Server** for AI agent integration (Claude Desktop, Agent Zero, etc.)

## Architecture

The application is a single-file FastAPI application (`main.py`) with the following key components:

### Core Services
- **Gmail API Integration**: Email reading, sending, attachment management, and label operations
- **Google Calendar Integration**: Event creation, reading, and deletion for reminders
- **OAuth2 Flow**: Complete Google authentication workflow with token management

### Data Flow
- OAuth credentials are stored in `token.json` after authentication
- Temporary files (attachments, credentials) are managed in the `tmp/` directory
- Email attachments are automatically downloaded and emails are labeled as "Downloaded"
- Background task monitors for new emails with attachments every hour

## Development Commands

### Running the Application
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the production server (fixed on port 8011)
python main.py

# Or use uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8011
```

### Testing
Automated tests are available via `unittest`:
```bash
source venv/bin/activate
python -m unittest discover -s tests -p 'test_*.py' -v
```

You can also test endpoints manually via:
- FastAPI auto-generated docs at `/docs`
- Direct HTTP requests to API endpoints

## Configuration

### Environment Variables (`.env`)
- `GOOGLE_CREDENTIALS`: JSON string containing Google OAuth2 client credentials
- `TOKEN_FILE`: Path to OAuth token storage (default: `/var/www/ai/GoogleApp/token.json`)
- `BASE_URL`: Application base URL (default: `https://cscarpa-vps.eu/GoogleApp`)
- `API_KEY`: API key for securing endpoints (default: `GoogleApp_SecureKey_2025_Cscarpa_VPS_Protection`)

### Port Configuration
- The application runs on **fixed port 8011**
- Nginx reverse proxy: `https://cscarpa-vps.eu/GoogleApp/` → `http://127.0.0.1:8011/`
- Local access: `http://localhost:8011/`

### OAuth Configuration
- Redirect URI: `https://cscarpa-vps.eu/GoogleApp/oauth2callback`
- Required scopes: Gmail (read/modify), Calendar

## Key Endpoints

### Authentication
- `GET /authenticate` - Initiate OAuth flow
- `GET /oauth2callback` - Handle OAuth callback

### Email Operations
- `GET /gmail/read-emails` - Filter and retrieve emails with advanced search parameters
- `POST /gmail/write-and-send-email` - Enhanced email sending with JSON body and file path attachments
- `POST /gmail/write-and-send-email-with-uploads` - Enhanced email sending with file uploads
- `GET /gmail/download-attachments/{message_id}` - Download attachments and apply "Downloaded" label

### Health
- `GET /health/token` - Diagnose token status (missing/invalid/network/valid)

### Calendar Services
- `POST /calendar/create-reminder` - Create calendar events
- `GET /calendar/read-reminders` - List calendar events
- `DELETE /calendar/remove-reminder` - Delete calendar events

## Background Services

### Automated Email Monitoring
The application includes a background task (`check_and_download_emails`) that:
- Runs every hour after startup
- Monitors for emails with attachments that haven't been processed
- Automatically downloads attachments
- Applies "Downloaded" label to processed emails

## File Structure

```
/var/www/ai/GoogleApp/
├── main.py                    # Main FastAPI application
├── mcp_server.py              # MCP server for AI agent integration
├── requirements.txt           # Python dependencies
├── tests/                     # Automated API contract tests
├── archive/legacy/            # Historical/legacy snapshots (not used at runtime)
├── .env                       # Environment configuration
├── token.json                 # OAuth tokens (created after authentication)
├── tmp/                       # Temporary files and downloaded attachments
├── venv/                      # Python virtual environment
├── MCP_SETUP.md               # MCP server setup guide
└── mcp_config_example.json    # Example MCP configuration for Claude Desktop
```

## Security

### API Key Authentication
All endpoints (except `/`, `/authenticate`, `/oauth2callback`, and `/docs`) are now protected with API Key authentication.

**Required Header:**
```
X-API-Key: GoogleApp_SecureKey_2025_Cscarpa_VPS_Protection
```

**Public Endpoints (no API key required):**
- `GET /` - Homepage
- `GET /authenticate` - OAuth authentication
- `GET /oauth2callback` - OAuth callback
- `GET /docs` - API documentation

**Protected Endpoints (API key required):**
- All email operations
- All calendar operations
- All attachment operations
- `GET /health/token`

**Security Features:**
- Secure comparison using `secrets.compare_digest()` to prevent timing attacks
- Clear error messages for missing or invalid API keys
- Environment variable storage for API key

## Email Sending Endpoints

### POST /gmail/write-and-send-email
**📁 For attachments using FILE PATHS on server**

Enhanced endpoint using JSON request body for emails with file attachments via server paths.

**Request Body (JSON):**
```json
{
  "to": "recipient@example.com",
  "subject": "Your subject here",
  "body": "Your email content here",
  "cc": "cc@example.com",  // optional
  "bcc": "bcc@example.com",  // optional
  "attachment_paths": ["/var/www/ai/GoogleApp/tmp/file1.pdf", "/var/www/ai/GoogleApp/tmp/file2.jpg"]  // optional
}
```

**Example with attachments:**
```bash
curl -X POST "https://cscarpa-vps.eu/GoogleApp/gmail/write-and-send-email" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: GoogleApp_SecureKey_2025_Cscarpa_VPS_Protection" \
  -d '{
    "to": "recipient@example.com",
    "subject": "Email with Server Files",
    "body": "This email includes files from server storage",
    "attachment_paths": ["/var/www/ai/GoogleApp/tmp/document.pdf"]
  }'
```

**Example without attachments:**
```bash
curl -X POST "https://cscarpa-vps.eu/GoogleApp/gmail/write-and-send-email" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: GoogleApp_SecureKey_2025_Cscarpa_VPS_Protection" \
  -d '{
    "to": "recipient@example.com",
    "subject": "Simple Email",
    "body": "This is a simple email without attachments"
  }'
```

### POST /gmail/write-and-send-email-with-uploads
**📤 For attachments using DIRECT FILE UPLOAD**

Endpoint for sending emails with file uploads via multipart form data.

**Form Data Parameters:**
- `to`: Recipient email (required)
- `subject`: Email subject (required)
- `body`: Email content (required)
- `cc`: CC recipients (optional)
- `bcc`: BCC recipients (optional)
- `files`: Multiple file uploads (optional)

**Example with file upload:**
```bash
curl -X POST "https://cscarpa-vps.eu/GoogleApp/gmail/write-and-send-email-with-uploads" \
  -H "X-API-Key: GoogleApp_SecureKey_2025_Cscarpa_VPS_Protection" \
  -F "to=recipient@example.com" \
  -F "subject=Email with Uploaded Files" \
  -F "body=This email includes uploaded files" \
  -F "files=@/local/path/to/document.pdf" \
  -F "files=@/local/path/to/image.jpg"
```

**Example without attachments:**
```bash
curl -X POST "https://cscarpa-vps.eu/GoogleApp/gmail/write-and-send-email-with-uploads" \
  -H "X-API-Key: GoogleApp_SecureKey_2025_Cscarpa_VPS_Protection" \
  -F "to=recipient@example.com" \
  -F "subject=Simple Email via Form" \
  -F "body=This is a simple email via form data"
```

### ⚠️ Common Mistake
**DON'T mix the endpoints:**
- ❌ Don't use JSON with `/gmail/write-and-send-email-with-uploads`
- ❌ Don't use form data with `/gmail/write-and-send-email`
- ❌ Don't use `attachment_paths` with the uploads endpoint
- ❌ Don't use `files` parameter with the JSON endpoint

## Development Notes

### Authentication Flow
1. Visit `/authenticate` to start OAuth flow
2. Complete Google authentication in browser
3. Tokens are automatically saved to `token.json`
4. All subsequent requests use stored tokens

### Error Handling
- Comprehensive exception handling with detailed error messages
- Automatic token refresh for expired credentials
- Graceful handling of missing files or configuration

### Security Considerations
- OAuth tokens and API keys are stored in environment variables
- Temporary credential files are automatically cleaned up
- File paths are validated for attachment operations

### Port Management
- Fixed port **8011** for production stability
- Nginx configured for reverse proxy to port 8011
- MCP server will communicate with FastAPI via `http://127.0.0.1:8011`

## MCP (Model Context Protocol) Integration

This application includes an MCP server that exposes Gmail and Calendar functionality to AI agents.

### Quick Start

1. **Install MCP dependencies:**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Claude Desktop** (or Agent Zero):
   See `MCP_SETUP.md` for detailed instructions

3. **Available MCP Tools:**
   - `read_emails` - Search and filter emails
   - `send_email` - Send emails with attachments
   - `download_attachments` - Download email attachments
   - `create_calendar_reminder` - Create calendar events
   - `read_calendar_reminders` - List calendar events
   - `delete_calendar_reminder` - Delete calendar events

### Configuration Files

- `mcp_server.py` - MCP server implementation
- `mcp_config_example.json` - Example configuration for Claude Desktop
- `MCP_SETUP.md` - Complete setup guide with troubleshooting

### How It Works

```
AI Agent (Claude/Agent Zero)
    ↓
MCP Server (stdio protocol)
    ↓
FastAPI Backend (http://127.0.0.1:8011)
    ↓
Gmail/Calendar APIs
```

The MCP server acts as a bridge, translating AI agent requests into FastAPI HTTP calls with proper authentication.
