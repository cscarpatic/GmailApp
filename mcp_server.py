#!/usr/bin/env python3
"""
MCP Server for GoogleApp
Exposes Gmail and Calendar operations through Model Context Protocol (MCP)
Communicates with FastAPI backend at http://127.0.0.1:8011
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional
import httpx
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("google-mcp-server")

load_dotenv()

# Configuration
BASE_URL = os.getenv("MCP_BASE_URL", "http://127.0.0.1:8011")
API_KEY = os.getenv("API_KEY")

# Create MCP server instance
server = Server("google-api-server")

# HTTP client for FastAPI communication
http_client = httpx.AsyncClient(
    base_url=BASE_URL,
    headers={"X-API-Key": API_KEY} if API_KEY else {},
    timeout=30.0
)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available MCP tools"""
    return [
        types.Tool(
            name="read_emails",
            description="Search and read emails from Gmail with advanced filtering options. Supports filtering by label, subject, sender, attachments, and text content.",
            inputSchema={
                "type": "object",
                "properties": {
                    "Label": {
                        "type": "string",
                        "description": "Filter emails by Gmail label (e.g., 'INBOX', 'UNREAD', 'SENT')"
                    },
                    "ExcludeLabel": {
                        "type": "string",
                        "description": "Exclude emails with this label (e.g., 'SPAM', 'TRASH')"
                    },
                    "Subject": {
                        "type": "string",
                        "description": "Filter emails containing this word in the subject"
                    },
                    "ExactSubject": {
                        "type": "string",
                        "description": "Filter emails with exact subject match"
                    },
                    "HasAttachment": {
                        "type": "boolean",
                        "description": "Filter only emails with attachments",
                        "default": False
                    },
                    "From": {
                        "type": "string",
                        "description": "Filter emails from specific sender email address"
                    },
                    "Text": {
                        "type": "string",
                        "description": "Filter emails containing this text in the body"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of emails to return (default 10)",
                        "default": 10
                    }
                }
            }
        ),
        types.Tool(
            name="send_email",
            description="Send an email via Gmail with optional CC, BCC, and attachments from server file paths",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body content (plain text)"
                    },
                    "cc": {
                        "type": "string",
                        "description": "CC recipient email address (optional)"
                    },
                    "bcc": {
                        "type": "string",
                        "description": "BCC recipient email address (optional)"
                    },
                    "attachment_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of absolute file paths on server to attach (e.g., ['/var/www/ai/GoogleApp/tmp/file.pdf'])"
                    }
                },
                "required": ["to", "subject", "body"]
            }
        ),
        types.Tool(
            name="download_attachments",
            description="Download all attachments from a specific email by message ID and apply 'Downloaded' label to the email",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "Gmail message ID (obtained from read_emails)"
                    }
                },
                "required": ["message_id"]
            }
        ),
        types.Tool(
            name="create_calendar_reminder",
            description="Create a reminder event in Google Calendar with specified time and description",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Event title/summary"
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description (optional)"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in ISO 8601 format (e.g., '2025-10-07T10:00:00')"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time in ISO 8601 format (e.g., '2025-10-07T11:00:00')"
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone identifier (default: 'UTC')",
                        "default": "UTC"
                    }
                },
                "required": ["title", "start_time", "end_time"]
            }
        ),
        types.Tool(
            name="read_calendar_reminders",
            description="List upcoming calendar events/reminders from Google Calendar",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of events to retrieve (default: 30)",
                        "default": 30
                    },
                    "time_min": {
                        "type": "string",
                        "description": "Minimum time in ISO 8601 format (optional, filters events after this time)"
                    },
                    "time_max": {
                        "type": "string",
                        "description": "Maximum time in ISO 8601 format (optional, filters events before this time)"
                    }
                }
            }
        ),
        types.Tool(
            name="delete_calendar_reminder",
            description="Delete a calendar event/reminder by event ID from Google Calendar",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "Calendar event ID (obtained from read_calendar_reminders)"
                    }
                },
                "required": ["event_id"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests"""

    try:
        if not API_KEY:
            raise ValueError("API_KEY non configurata in .env. Impossibile chiamare le API protette.")

        if name == "read_emails":
            return await read_emails(arguments or {})
        elif name == "send_email":
            return await send_email(arguments or {})
        elif name == "download_attachments":
            return await download_attachments(arguments or {})
        elif name == "create_calendar_reminder":
            return await create_calendar_reminder(arguments or {})
        elif name == "read_calendar_reminders":
            return await read_calendar_reminders(arguments or {})
        elif name == "delete_calendar_reminder":
            return await delete_calendar_reminder(arguments or {})
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


# Tool implementations
async def read_emails(args: Dict[str, Any]) -> list[types.TextContent]:
    """Read emails from Gmail"""
    params = {
        "Label": args.get("Label", ""),
        "ExcludeLabel": args.get("ExcludeLabel", ""),
        "Subject": args.get("Subject", ""),
        "ExactSubject": args.get("ExactSubject", ""),
        "HasAttachment": args.get("HasAttachment", False),
        "From": args.get("From", ""),
        "Text": args.get("Text", ""),
        "max_results": args.get("max_results", 10)
    }

    # Remove empty parameters
    params = {k: v for k, v in params.items() if v}

    response = await http_client.get("/gmail/read-emails", params=params)
    response.raise_for_status()

    data = response.json()

    # Format the response nicely
    if "emails" in data and data["emails"]:
        email_list = []
        for email in data["emails"]:
            email_list.append(
                f"ID: {email.get('id', 'N/A')}\n"
                f"From: {email.get('from', 'N/A')}\n"
                f"Subject: {email.get('subject', 'N/A')}\n"
                f"Snippet: {email.get('snippet', 'N/A')}\n"
                f"Labels: {', '.join(email.get('labels', []))}\n"
            )
        formatted = f"Found {len(data['emails'])} email(s):\n\n" + "\n---\n".join(email_list)
    else:
        formatted = "No emails found matching the criteria."

    return [types.TextContent(type="text", text=formatted)]


async def send_email(args: Dict[str, Any]) -> list[types.TextContent]:
    """Send email via Gmail"""
    payload = {
        "to": args["to"],
        "subject": args["subject"],
        "body": args["body"],
        "cc": args.get("cc"),
        "bcc": args.get("bcc"),
        "attachment_paths": args.get("attachment_paths", [])
    }

    response = await http_client.post("/gmail/write-and-send-email", json=payload)
    response.raise_for_status()

    data = response.json()

    result = (
        f"✅ Email sent successfully!\n\n"
        f"Message ID: {data.get('message_id', 'N/A')}\n"
        f"To: {data.get('details', {}).get('to', 'N/A')}\n"
        f"Subject: {data.get('details', {}).get('subject', 'N/A')}\n"
    )

    attachments = data.get('details', {}).get('attachments', [])
    if attachments:
        result += f"Attachments: {', '.join(attachments)}\n"

    return [types.TextContent(type="text", text=result)]


async def download_attachments(args: Dict[str, Any]) -> list[types.TextContent]:
    """Download email attachments"""
    message_id = args["message_id"]

    response = await http_client.get(f"/gmail/download-attachments/{message_id}")
    response.raise_for_status()

    data = response.json()

    attachments = data.get("attachments", [])
    if attachments:
        attachment_list = []
        for att in attachments:
            attachment_list.append(
                f"- {att.get('filename', 'N/A')} → {att.get('file_path', 'N/A')}"
            )
        result = (
            f"✅ Downloaded {len(attachments)} attachment(s):\n\n" +
            "\n".join(attachment_list) +
            f"\n\n{data.get('message', '')}"
        )
    else:
        result = data.get("message", "No attachments found.")

    return [types.TextContent(type="text", text=result)]


async def create_calendar_reminder(args: Dict[str, Any]) -> list[types.TextContent]:
    """Create calendar reminder"""
    params = {
        "title": args["title"],
        "description": args.get("description", ""),
        "start_time": args["start_time"],
        "end_time": args["end_time"],
        "timezone": args.get("timezone", "UTC")
    }

    response = await http_client.post("/calendar/create-reminder", params=params)
    response.raise_for_status()

    data = response.json()

    result = (
        f"✅ Reminder created successfully!\n\n"
        f"Event ID: {data.get('event_id', 'N/A')}\n"
        f"Link: {data.get('htmlLink', 'N/A')}\n"
    )

    return [types.TextContent(type="text", text=result)]


async def read_calendar_reminders(args: Dict[str, Any]) -> list[types.TextContent]:
    """Read calendar reminders"""
    params = {
        "max_results": args.get("max_results", 30)
    }

    if args.get("time_min"):
        params["time_min"] = args["time_min"]
    if args.get("time_max"):
        params["time_max"] = args["time_max"]

    response = await http_client.get("/calendar/read-reminders", params=params)
    response.raise_for_status()

    data = response.json()

    events = data.get("events", [])
    if events:
        event_list = []
        for event in events:
            start = event.get("start", {})
            event_list.append(
                f"ID: {event.get('id', 'N/A')}\n"
                f"Summary: {event.get('summary', 'N/A')}\n"
                f"Start: {start.get('dateTime', start.get('date', 'N/A'))}\n"
                f"Status: {event.get('status', 'N/A')}\n"
            )
        result = f"Found {len(events)} event(s):\n\n" + "\n---\n".join(event_list)
    else:
        result = "No calendar events found."

    return [types.TextContent(type="text", text=result)]


async def delete_calendar_reminder(args: Dict[str, Any]) -> list[types.TextContent]:
    """Delete calendar reminder"""
    event_id = args["event_id"]

    response = await http_client.delete(f"/calendar/remove-reminder?event_id={event_id}")
    response.raise_for_status()

    data = response.json()

    return [types.TextContent(
        type="text",
        text=f"✅ {data.get('message', 'Reminder deleted successfully')}"
    )]


async def main():
    """Run the MCP server"""
    logger.info("Starting Google MCP Server...")
    logger.info(f"Connecting to FastAPI backend at {BASE_URL}")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="google-api-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
