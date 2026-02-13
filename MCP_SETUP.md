# MCP Server Setup Guide

This guide explains how to set up the Model Context Protocol (MCP) server for GoogleApp to enable AI agents (Claude Desktop, Agent Zero, etc.) to access Gmail and Calendar functionality.

## Overview

The MCP server acts as a bridge between AI agents and the GoogleApp FastAPI backend:

```
AI Agent (Claude/Agent Zero) ←→ MCP Server ←→ FastAPI (port 8011) ←→ Gmail/Calendar APIs
```

## Prerequisites

1. **GoogleApp service running** on port 8011
2. **Python virtual environment** activated
3. **MCP Python package** installed

## Installation

### 1. Install MCP Dependencies

```bash
cd /var/www/ai/GoogleApp
source venv/bin/activate
pip install mcp
```

### 2. Make MCP Server Executable

```bash
chmod +x mcp_server.py
```

### 3. Test MCP Server

```bash
python mcp_server.py
```

You should see: `Starting Google MCP Server...`

Press `Ctrl+C` to stop.

## Configuration

### For Claude Desktop

1. **Locate Claude Desktop config file:**
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux:** `~/.config/Claude/claude_desktop_config.json`

2. **Add GoogleApp MCP server:**

```json
{
  "mcpServers": {
    "gmail-api": {
      "command": "python",
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

3. **Restart Claude Desktop**

4. **Verify:** Look for the 🔌 tools icon in Claude Desktop chat. You should see 6 new tools:
   - `read_emails`
   - `send_email`
   - `download_attachments`
   - `create_calendar_reminder`
   - `read_calendar_reminders`
   - `delete_calendar_reminder`

### For Agent Zero

Add to Agent Zero's MCP configuration file (typically in agent's config directory):

```json
{
  "mcp_servers": {
    "gmail": {
      "command": ["python", "/var/www/ai/GoogleApp/mcp_server.py"],
      "env": {
        "PYTHONPATH": "/var/www/ai/GoogleApp/venv/lib/python3.12/site-packages"
      }
    }
  }
}
```

Restart Agent Zero after configuration.

## Available Tools

### 1. read_emails
Search and filter emails with advanced criteria.

**Parameters:**
- `Label` (optional): Filter by Gmail label (e.g., "INBOX", "UNREAD")
- `ExcludeLabel` (optional): Exclude specific label
- `Subject` (optional): Filter by subject keyword
- `ExactSubject` (optional): Exact subject match
- `HasAttachment` (optional): Only emails with attachments
- `From` (optional): Filter by sender
- `Text` (optional): Search text in email body

**Example:**
```
Use read_emails to find unread emails from john@example.com with attachments
```

### 2. send_email
Send an email with optional attachments.

**Parameters:**
- `to` (required): Recipient email
- `subject` (required): Email subject
- `body` (required): Email content
- `cc` (optional): CC recipient
- `bcc` (optional): BCC recipient
- `attachment_paths` (optional): Server file paths to attach

**Example:**
```
Use send_email to send an email to jane@example.com with subject "Meeting Notes"
and body "Please review the attached document" with attachment
/var/www/ai/GoogleApp/tmp/notes.pdf
```

### 3. download_attachments
Download attachments from a specific email.

**Parameters:**
- `message_id` (required): Email message ID from read_emails

**Example:**
```
Use download_attachments with message_id "18f2a3b4c5d6e7f8" to save
all attachments to /var/www/ai/GoogleApp/tmp/
```

### 4. create_calendar_reminder
Create a Google Calendar event.

**Parameters:**
- `title` (required): Event title
- `description` (optional): Event description
- `start_time` (required): ISO 8601 format (e.g., "2025-10-07T10:00:00")
- `end_time` (required): ISO 8601 format
- `timezone` (optional): Default "UTC"

**Example:**
```
Use create_calendar_reminder to schedule "Team Meeting" on 2025-10-10
from 14:00 to 15:00 UTC
```

### 5. read_calendar_reminders
List upcoming calendar events.

**Parameters:**
- `max_results` (optional): Max events to return (default: 30)
- `time_min` (optional): Filter events after this time
- `time_max` (optional): Filter events before this time

**Example:**
```
Use read_calendar_reminders to show my next 10 calendar events
```

### 6. delete_calendar_reminder
Delete a calendar event by ID.

**Parameters:**
- `event_id` (required): Event ID from read_calendar_reminders

**Example:**
```
Use delete_calendar_reminder to remove event with ID "abc123def456"
```

## Troubleshooting

### MCP Server Won't Start

**Check FastAPI is running:**
```bash
curl http://127.0.0.1:8011/
```

Expected: `{"message":"Benvenuto nella Google API Web App!"}`

**Check API key:**
Verify `API_KEY` is present in `.env` (the MCP server reads it from environment variables).

### Tools Not Appearing in Claude Desktop

1. **Check config file syntax:**
   ```bash
   python -m json.tool ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

2. **Check Python path:**
   ```bash
   ls /var/www/ai/GoogleApp/venv/lib/python3.12/site-packages/mcp
   ```

3. **View Claude Desktop logs:**
   - macOS: `~/Library/Logs/Claude/`
   - Windows: `%APPDATA%\Claude\logs\`
   - Linux: `~/.config/Claude/logs/`

### Permission Errors

Make sure the MCP server can access the FastAPI backend:

```bash
# Test from the server
curl -H "X-API-Key: GoogleApp_SecureKey_2025_Cscarpa_VPS_Protection" \
  http://127.0.0.1:8011/gmail/read-emails
```

## Security Notes

- **API Key:** The MCP server uses the same API key as direct HTTP requests
- **Local Only:** MCP server communicates with FastAPI on localhost (127.0.0.1)
- **No Network Exposure:** MCP uses stdio protocol, no network ports opened
- **OAuth Tokens:** Gmail authentication tokens are managed by FastAPI backend

## Advanced Configuration

### Custom Port

If FastAPI runs on a different port, update `BASE_URL` in `mcp_server.py`:

```python
BASE_URL = "http://127.0.0.1:YOUR_PORT"
```

### Logging

Enable debug logging by modifying `mcp_server.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

Logs will show all HTTP requests to FastAPI backend.

### Multiple AI Agents

You can connect multiple AI agents to the same MCP server. Each agent will have independent access to Gmail/Calendar tools.

## Next Steps

- Test each tool individually in Claude Desktop
- Create automation workflows using multiple tools
- Integrate with Agent Zero for advanced agent capabilities
- Monitor FastAPI logs for tool usage: `sudo journalctl -u GoogleApp.service -f`

## Support

For issues or questions:
1. Check FastAPI backend logs: `sudo journalctl -u GoogleApp.service`
2. Check MCP server output when running manually
3. Verify OAuth authentication: visit `https://cscarpa-vps.eu/GoogleApp/authenticate`

---

**MCP Server Version:** 1.0.0
**FastAPI Backend Port:** 8011
**Protocol:** stdio (Standard Input/Output)
