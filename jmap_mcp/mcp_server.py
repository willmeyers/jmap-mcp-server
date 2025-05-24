import logging
from datetime import datetime
from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP

from jmap_mcp.jmap_client import JMAPClient, JMAPError
from jmap_mcp.config import config
from jmap_mcp.logging_config import setup_logging

logger = logging.getLogger(__name__)

mcp = FastMCP("JMAP MCP Server")


@mcp.tool()
async def list_mailboxes() -> str:
    """List all mailboxes in the Fastmail account with email counts"""
    try:
        async with JMAPClient() as client:
            mailboxes = await client.get_mailboxes()

            result_lines = ["# Mailboxes", ""]

            for mailbox in mailboxes:
                name = mailbox.get("name", "Unknown")
                role = mailbox.get("role", "")
                total_emails = mailbox.get("totalEmails", 0)
                unread_emails = mailbox.get("unreadEmails", 0)

                role_display = f" ({role})" if role else ""
                result_lines.append(
                    f"**{name}**{role_display}: {unread_emails}/{total_emails} unread/total emails"
                )

            if not mailboxes:
                result_lines.append("No mailboxes found.")

            return "\n".join(result_lines)

    except JMAPError as e:
        error_msg = f"JMAP error: {e}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error listing mailboxes: {e}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def search_email(
    query: str = "",
    mailbox: str = "",
    sender: str = "",
    subject: str = "",
    unread_only: bool = False,
    limit: int = 20,
) -> str:
    """Search for emails using various criteria like text, sender, subject, etc.

    Args:
        query: Text to search for in email content
        mailbox: Mailbox name or role (e.g., 'inbox', 'sent', 'drafts')
        sender: Sender email address to filter by
        subject: Text to search for in subject line
        unread_only: Only return unread emails
        limit: Maximum number of emails to return (1-100)
    """
    try:
        async with JMAPClient() as client:
            # Build filter conditions
            filter_conditions = {}

            if query:
                filter_conditions["text"] = query

            if sender:
                filter_conditions["from"] = sender

            if subject:
                filter_conditions["subject"] = subject

            if unread_only:
                filter_conditions["notKeyword"] = "$seen"

            if mailbox:
                # Find mailbox by name
                mailboxes = await client.get_mailboxes()
                target_mailbox = None
                for mb in mailboxes:
                    if (
                        mb.get("name", "").lower() == mailbox.lower()
                        or mb.get("role") == mailbox.lower()
                    ):
                        target_mailbox = mb
                        break

                if target_mailbox:
                    filter_conditions["inMailbox"] = target_mailbox["id"]
                else:
                    return f"Mailbox '{mailbox}' not found"

            # Search for emails
            search_results = await client.search_emails(
                filter_conditions=filter_conditions if filter_conditions else None,
                limit=min(max(limit, 1), 100),
            )

            email_ids = search_results.get("ids", [])

            if not email_ids:
                return "No emails found matching the search criteria."

            # Get email details
            emails = await client.get_emails(
                ids=email_ids,
                properties=[
                    "id",
                    "subject",
                    "from",
                    "to",
                    "receivedAt",
                    "preview",
                    "keywords",
                ],
            )

            result_lines = [f"# Search Results ({len(emails)} emails)", ""]

            for email in emails:
                subject = email.get("subject", "(No subject)")
                from_addr = email.get("from", [{}])[0].get("email", "Unknown sender")
                received_at = email.get("receivedAt", "")
                preview = email.get("preview", "")
                is_unread = "$seen" not in email.get("keywords", [])

                # Format date
                try:
                    if received_at:
                        dt = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
                        date_str = dt.strftime("%Y-%m-%d %H:%M")
                    else:
                        date_str = "Unknown date"
                except Exception:
                    date_str = received_at

                unread_indicator = " 🔴" if is_unread else ""

                result_lines.extend(
                    [
                        f"## {subject}{unread_indicator}",
                        f"**From:** {from_addr}",
                        f"**Date:** {date_str}",
                        f"**Preview:** {preview[:200]}{'...' if len(preview) > 200 else ''}",
                        f"**ID:** {email.get('id')}",
                        "",
                    ]
                )

            return "\n".join(result_lines)

    except JMAPError as e:
        error_msg = f"JMAP error: {e}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error searching emails: {e}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def read_email(email_id: str, include_html: bool = False) -> str:
    """Read the full content and details of an email by ID

    Args:
        email_id: The ID of the email to read
        include_html: Whether to include HTML body information
    """
    if not email_id:
        return "Error: email_id parameter is required"

    try:
        async with JMAPClient() as client:
            emails = await client.get_emails(
                ids=[email_id],
                properties=[
                    "id",
                    "subject",
                    "from",
                    "to",
                    "cc",
                    "bcc",
                    "replyTo",
                    "receivedAt",
                    "sentAt",
                    "size",
                    "preview",
                    "keywords",
                    "bodyStructure",
                    "textBody",
                    "htmlBody",
                ],
            )

            if not emails:
                return f"Email with ID '{email_id}' not found"

            email = emails[0]

            result_lines = []

            subject = email.get("subject", "(No subject)")
            is_unread = "$seen" not in email.get("keywords", [])
            unread_indicator = " 🔴" if is_unread else ""

            result_lines.extend(
                [
                    f"# {subject}{unread_indicator}",
                    "",
                    "## Email Details",
                    "",
                ]
            )

            from_addresses = email.get("from", [])
            if from_addresses:
                from_list = []
                for addr in from_addresses:
                    name = addr.get("name", "")
                    email_addr = addr.get("email", "")
                    if name:
                        from_list.append(f"{name} <{email_addr}>")
                    else:
                        from_list.append(email_addr)
                result_lines.append(f"**From:** {', '.join(from_list)}")

            to_addresses = email.get("to", [])
            if to_addresses:
                to_list = []
                for addr in to_addresses:
                    name = addr.get("name", "")
                    email_addr = addr.get("email", "")
                    if name:
                        to_list.append(f"{name} <{email_addr}>")
                    else:
                        to_list.append(email_addr)
                result_lines.append(f"**To:** {', '.join(to_list)}")

            cc_addresses = email.get("cc", [])
            if cc_addresses:
                cc_list = []
                for addr in cc_addresses:
                    name = addr.get("name", "")
                    email_addr = addr.get("email", "")
                    if name:
                        cc_list.append(f"{name} <{email_addr}>")
                    else:
                        cc_list.append(email_addr)
                result_lines.append(f"**CC:** {', '.join(cc_list)}")

            received_at = email.get("receivedAt", "")
            sent_at = email.get("sentAt", "")

            try:
                if received_at:
                    dt = datetime.fromisoformat(received_at.replace("Z", "+00:00"))
                    result_lines.append(
                        f"**Received:** {dt.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                    )

                if sent_at and sent_at != received_at:
                    dt = datetime.fromisoformat(sent_at.replace("Z", "+00:00"))
                    result_lines.append(
                        f"**Sent:** {dt.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                    )
            except Exception:
                if received_at:
                    result_lines.append(f"**Received:** {received_at}")
                if sent_at:
                    result_lines.append(f"**Sent:** {sent_at}")

            size = email.get("size", 0)
            if size:
                if size < 1024:
                    size_str = f"{size} bytes"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                result_lines.append(f"**Size:** {size_str}")

            result_lines.append("")

            text_body_parts = email.get("textBody", [])
            html_body_parts = email.get("htmlBody", [])

            if text_body_parts:
                result_lines.extend(
                    [
                        "## Email Content (Text)",
                        "",
                    ]
                )

                # For now, we'll use the preview if available, or indicate that body parts need to be downloaded
                # In a full implementation, you would download the body parts using the blobId
                preview = email.get("preview", "")
                if preview:
                    result_lines.extend(
                        [
                            preview,
                            "",
                            "*Note: This is a preview. Full body content requires separate download.*",
                            "",
                        ]
                    )
                else:
                    result_lines.extend(
                        [
                            "*Email body content available but requires separate download.*",
                            "",
                        ]
                    )

            if include_html and html_body_parts:
                result_lines.extend(
                    [
                        "## Email Content (HTML)",
                        "",
                        "*HTML content available but requires separate download.*",
                        "",
                    ]
                )

            body_structure = email.get("bodyStructure", {})
            if body_structure:
                result_lines.extend(
                    [
                        "## Body Structure",
                        "",
                        f"**Type:** {body_structure.get('type', 'Unknown')}",
                    ]
                )

                if "size" in body_structure:
                    result_lines.append(f"**Size:** {body_structure['size']} bytes")

                sub_parts = body_structure.get("subParts", [])
                if sub_parts:
                    result_lines.append(f"**Parts:** {len(sub_parts)} parts")
                    for i, part in enumerate(sub_parts, 1):
                        part_type = part.get("type", "Unknown")
                        result_lines.append(f"  {i}. {part_type}")

                result_lines.append("")

            return "\n".join(result_lines)

    except JMAPError as e:
        error_msg = f"JMAP error: {e}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error reading email: {e}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
async def send_draft(
    to: List[str],
    subject: str = "",
    text_body: str = "",
    html_body: str = "",
    cc: List[str] = None,
    bcc: List[str] = None,
    send_immediately: bool = False,
) -> str:
    """Create an email draft and optionally send it immediately

    Args:
        to: List of recipient email addresses (required)
        subject: Email subject line
        text_body: Plain text email body content
        html_body: HTML email body content
        cc: List of CC recipient email addresses
        bcc: List of BCC recipient email addresses
        send_immediately: Whether to send the email immediately after creating the draft
    """
    try:
        if not subject and not text_body and not html_body:
            return "Error: At least one of subject, text_body, or html_body is required"

        if not to:
            return "Error: At least one 'to' address is required"

        def parse_addresses(addresses):
            """Convert address list to JMAP format."""
            if not addresses:
                return []

            result = []
            for addr in addresses:
                if isinstance(addr, str):
                    # Simple email address
                    result.append({"email": addr})
                elif isinstance(addr, dict):
                    # Already in correct format or has name/email
                    if "email" in addr:
                        result.append(addr)
                    else:
                        return f"Error: Invalid address format: {addr}"
                else:
                    return f"Error: Invalid address type: {type(addr)}"
            return result

        parsed_to = parse_addresses(to)
        parsed_cc = parse_addresses(cc) if cc else []
        parsed_bcc = parse_addresses(bcc) if bcc else []

        if isinstance(parsed_to, str):
            return parsed_to
        if isinstance(parsed_cc, str):
            return parsed_cc
        if isinstance(parsed_bcc, str):
            return parsed_bcc

        async with JMAPClient() as client:
            try:
                email_id = await client.create_draft(
                    subject=subject,
                    to_addresses=parsed_to,
                    cc_addresses=parsed_cc if parsed_cc else None,
                    bcc_addresses=parsed_bcc if parsed_bcc else None,
                    text_body=text_body if text_body else None,
                    html_body=html_body if html_body else None,
                )

                result_lines = [
                    "# Email Draft Created",
                    "",
                    f"**Subject:** {subject}",
                    f"**To:** {', '.join([addr.get('email', '') for addr in parsed_to])}",
                ]

                if parsed_cc:
                    result_lines.append(
                        f"**CC:** {', '.join([addr.get('email', '') for addr in parsed_cc])}"
                    )

                if parsed_bcc:
                    result_lines.append(
                        f"**BCC:** {', '.join([addr.get('email', '') for addr in parsed_bcc])}"
                    )

                result_lines.extend(
                    [
                        f"**Email ID:** {email_id}",
                        "",
                    ]
                )

                if text_body:
                    result_lines.extend(
                        [
                            "**Text Content:**",
                            text_body[:200] + ("..." if len(text_body) > 200 else ""),
                            "",
                        ]
                    )

                if send_immediately:
                    try:
                        success = await client.send_email(email_id)
                        if success:
                            result_lines.extend(
                                [
                                    "✅ **Email sent successfully!**",
                                    "",
                                ]
                            )
                        else:
                            result_lines.extend(
                                [
                                    "❌ **Failed to send email.** The draft has been saved.",
                                    "",
                                ]
                            )
                    except Exception as send_error:
                        result_lines.extend(
                            [
                                f"❌ **Error sending email:** {send_error}",
                                "The draft has been saved and can be sent manually.",
                                "",
                            ]
                        )
                else:
                    result_lines.extend(
                        [
                            "📝 **Draft saved.** Use the Fastmail interface to send it, or call this tool again with send_immediately=true.",
                            "",
                        ]
                    )

                return "\n".join(result_lines)

            except JMAPError as e:
                error_msg = f"Failed to create draft: {e}"
                logger.error(error_msg)
                return error_msg

    except Exception as e:
        error_msg = f"Unexpected error creating email draft: {e}"
        logger.error(error_msg)
        return error_msg


def main():
    """Main entry point for the MCP server."""
    setup_logging(level=config.log_level, log_file=config.log_file)

    logger.info("Starting JMAP MCP server...")

    try:
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    main()
