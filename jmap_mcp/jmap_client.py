import logging
from typing import Any, Dict, List, Optional

from jmapc import (
    Client,
    EmailQueryFilterCondition,
    MailboxQueryFilterCondition,
    Comparator,
    Ref,
    Address,
    Email,
    EmailAddress,
    EmailBodyPart,
    EmailBodyValue,
    EmailSubmission,
    Envelope,
)
from jmapc.methods import (
    MailboxGet,
    MailboxGetResponse,
    MailboxQuery,
    EmailGet,
    EmailGetResponse,
    EmailQuery,
    EmailQueryResponse,
    EmailSet,
    EmailSubmissionSet,
    IdentityGet,
    IdentityGetResponse,
)

from .auth import FastmailAuth
from .config import config

logger = logging.getLogger(__name__)


class JMAPError(Exception):
    """JMAP API error."""

    def __init__(self, message: str, error_type: str = None, status_code: int = None):
        super().__init__(message)
        self.error_type = error_type
        self.status_code = status_code


class JMAPClient:
    """Client for interacting with Fastmail JMAP API using jmapc library."""

    def __init__(self):
        self._auth = FastmailAuth()
        self._client: Optional[Client] = None

    async def __aenter__(self):
        await self._auth.__aenter__()
        self._client = self._auth.get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._auth.__aexit__(exc_type, exc_val, exc_tb)

    async def get_mailboxes(self) -> List[Dict[str, Any]]:
        """Get list of mailboxes."""
        if not self._client:
            raise JMAPError("Client not initialized")

        try:
            # Query all mailboxes, then get their details
            results = self._client.request(
                [
                    MailboxQuery(),
                    MailboxGet(ids=Ref("/ids")),
                ]
            )

            mailbox_response = results[1].response
            if not isinstance(mailbox_response, MailboxGetResponse):
                raise JMAPError("Unexpected response type from MailboxGet")

            # Convert to the format expected by our MCP tools
            mailboxes = []
            for mailbox in mailbox_response.data:
                mailboxes.append(
                    {
                        "id": mailbox.id,
                        "name": mailbox.name,
                        "role": mailbox.role,
                        "totalEmails": mailbox.total_emails,
                        "unreadEmails": mailbox.unread_emails,
                    }
                )

            return mailboxes

        except Exception as e:
            logger.error(f"Failed to get mailboxes: {e}")
            raise JMAPError(f"Failed to get mailboxes: {e}")

    async def search_emails(
        self,
        filter_conditions: Optional[Dict[str, Any]] = None,
        sort: Optional[List[Dict[str, str]]] = None,
        limit: Optional[int] = None,
        mailbox_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search for emails using JMAP Email/query."""
        if not self._client:
            raise JMAPError("Client not initialized")

        try:
            # Build filter using jmapc's EmailQueryFilterCondition
            filter_kwargs = {}

            if mailbox_id:
                filter_kwargs["in_mailbox"] = mailbox_id

            # Add other filter conditions
            if filter_conditions:
                if "text" in filter_conditions:
                    filter_kwargs["text"] = filter_conditions["text"]
                if "subject" in filter_conditions:
                    filter_kwargs["subject"] = filter_conditions["subject"]
                if "from" in filter_conditions:
                    filter_kwargs["from_addresses"] = filter_conditions["from"]
                if "to" in filter_conditions:
                    filter_kwargs["to"] = filter_conditions["to"]

            # Build sort using jmapc's Comparator
            sort_comparators = []
            if sort:
                for sort_item in sort:
                    sort_comparators.append(
                        Comparator(
                            property=sort_item.get("property", "receivedAt"),
                            is_ascending=sort_item.get("isAscending", False),
                        )
                    )
            else:
                sort_comparators = [
                    Comparator(property="receivedAt", is_ascending=False)
                ]

            # Create query request
            email_filter = (
                EmailQueryFilterCondition(**filter_kwargs) if filter_kwargs else None
            )

            results = self._client.request(
                [
                    EmailQuery(
                        filter=email_filter, sort=sort_comparators, limit=limit or 50
                    )
                ]
            )

            query_response = results[0].response

            return {
                "ids": query_response.ids,
                "total": query_response.total,
                "limit": query_response.limit,
                "position": query_response.position or 0,
            }

        except Exception as e:
            logger.error(f"Failed to search emails: {e}")
            raise JMAPError(f"Failed to search emails: {e}")

    async def get_emails(
        self,
        ids: List[str],
        properties: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get email details by IDs."""
        if not self._client:
            raise JMAPError("Client not initialized")

        try:
            results = self._client.request(
                [
                    EmailGet(
                        ids=ids,
                        properties=properties
                        or [
                            "id",
                            "subject",
                            "from",
                            "to",
                            "cc",
                            "bcc",
                            "receivedAt",
                            "size",
                            "preview",
                            "bodyStructure",
                            "textBody",
                            "htmlBody",
                        ],
                    )
                ]
            )

            email_response = results[0].response
            if not isinstance(email_response, EmailGetResponse):
                logger.error(
                    f"Unexpected response type from EmailGet: {type(email_response)}"
                )
                raise JMAPError("Unexpected response type from EmailGet")

            # Convert to expected format
            emails = []
            for email in email_response.data:
                email_dict = {
                    "id": email.id,
                    "subject": email.subject or "",
                    "from": [
                        {"email": addr.email, "name": addr.name or ""}
                        for addr in (
                            getattr(email, "mail_from", None)
                            or getattr(email, "from", None)
                            or []
                        )
                    ],
                    "to": [
                        {"email": addr.email, "name": addr.name or ""}
                        for addr in (email.to or [])
                    ],
                    "cc": (
                        [
                            {"email": addr.email, "name": addr.name or ""}
                            for addr in (email.cc or [])
                        ]
                        if email.cc
                        else []
                    ),
                    "bcc": (
                        [
                            {"email": addr.email, "name": addr.name or ""}
                            for addr in (email.bcc or [])
                        ]
                        if email.bcc
                        else []
                    ),
                    "receivedAt": (
                        email.received_at.isoformat() if email.received_at else None
                    ),
                    "size": email.size or 0,
                    "preview": email.preview or "",
                }

                # Handle body content
                if hasattr(email, "text_body") and email.text_body:
                    email_dict["textBody"] = email.text_body
                if hasattr(email, "html_body") and email.html_body:
                    email_dict["htmlBody"] = email.html_body

                emails.append(email_dict)

            return emails

        except Exception as e:
            logger.error(f"Failed to get emails: {e}")
            raise JMAPError(f"Failed to get emails: {e}")

    async def create_draft(
        self,
        subject: str,
        to_addresses: List[Dict[str, str]],
        from_address: Optional[Dict[str, str]] = None,
        cc_addresses: Optional[List[Dict[str, str]]] = None,
        bcc_addresses: Optional[List[Dict[str, str]]] = None,
        text_body: Optional[str] = None,
        html_body: Optional[str] = None,
    ) -> str:
        """Create an email draft."""
        if not self._client:
            raise JMAPError("Client not initialized")

        try:
            # Get the Drafts mailbox ID
            drafts_results = self._client.request(
                [
                    MailboxQuery(filter=MailboxQueryFilterCondition(name="Drafts")),
                    MailboxGet(ids=Ref("/ids")),
                ]
            )

            mailbox_response = drafts_results[1].response
            if (
                not isinstance(mailbox_response, MailboxGetResponse)
                or not mailbox_response.data
            ):
                raise JMAPError("Drafts mailbox not found")

            drafts_mailbox_id = mailbox_response.data[0].id

            # Get identity for from address if not provided
            if not from_address:
                identity_results = self._client.request([IdentityGet()])
                identity_response = identity_results[0].response
                if (
                    not isinstance(identity_response, IdentityGetResponse)
                    or not identity_response.data
                ):
                    raise JMAPError("No identity found")

                identity = identity_response.data[0]
                from_address = {"email": identity.email, "name": identity.name or ""}

            # Convert address dicts to EmailAddress objects
            to_email_addresses = [
                EmailAddress(email=addr["email"], name=addr.get("name", ""))
                for addr in to_addresses
            ]
            from_email_addresses = [
                EmailAddress(
                    email=from_address["email"], name=from_address.get("name", "")
                )
            ]

            cc_email_addresses = None
            if cc_addresses:
                cc_email_addresses = [
                    EmailAddress(email=addr["email"], name=addr.get("name", ""))
                    for addr in cc_addresses
                ]

            bcc_email_addresses = None
            if bcc_addresses:
                bcc_email_addresses = [
                    EmailAddress(email=addr["email"], name=addr.get("name", ""))
                    for addr in bcc_addresses
                ]

            # Create email object
            email_kwargs = {
                "mail_from": from_email_addresses,
                "to": to_email_addresses,
                "subject": subject,
                "keywords": {"$draft": True},
                "mailbox_ids": {drafts_mailbox_id: True},
            }

            if cc_email_addresses:
                email_kwargs["cc"] = cc_email_addresses
            if bcc_email_addresses:
                email_kwargs["bcc"] = bcc_email_addresses

            # Add body content
            if text_body:
                email_kwargs["body_values"] = {"body": EmailBodyValue(value=text_body)}
                email_kwargs["text_body"] = [
                    EmailBodyPart(part_id="body", type="text/plain")
                ]

            email = Email(**email_kwargs)

            # Create the draft
            results = self._client.request([EmailSet(create={"draft": email})])

            email_set_response = results[0].response
            if hasattr(email_set_response, "created") and email_set_response.created:
                return email_set_response.created["draft"].id
            else:
                raise JMAPError("Failed to create draft email")

        except Exception as e:
            logger.error(f"Failed to create draft: {e}")
            raise JMAPError(f"Failed to create draft: {e}")

    async def send_email(self, email_id: str) -> bool:
        """Send an email draft."""
        if not self._client:
            raise JMAPError("Client not initialized")

        try:
            # Get the email to extract recipients for the envelope
            email_results = self._client.request(
                [EmailGet(ids=[email_id], properties=["to", "cc", "bcc"])]
            )

            email_response = email_results[0].response
            if (
                not isinstance(email_response, EmailGetResponse)
                or not email_response.data
            ):
                raise JMAPError("Email not found")

            email = email_response.data[0]

            # Get identity for sending
            identity_results = self._client.request([IdentityGet()])
            identity_response = identity_results[0].response
            if (
                not isinstance(identity_response, IdentityGetResponse)
                or not identity_response.data
            ):
                raise JMAPError("No identity found")

            identity = identity_response.data[0]

            # Build recipient list for envelope
            rcpt_to = []
            if email.to:
                rcpt_to.extend([Address(email=addr.email) for addr in email.to])
            if email.cc:
                rcpt_to.extend([Address(email=addr.email) for addr in email.cc])
            if email.bcc:
                rcpt_to.extend([Address(email=addr.email) for addr in email.bcc])

            # Send the email using EmailSubmissionSet
            results = self._client.request(
                [
                    EmailSubmissionSet(
                        create={
                            "send": EmailSubmission(
                                email_id=email_id,
                                identity_id=identity.id,
                                envelope=Envelope(
                                    mail_from=Address(email=identity.email),
                                    rcpt_to=rcpt_to,
                                ),
                            )
                        },
                    )
                ]
            )

            submission_response = results[0].response
            return (
                hasattr(submission_response, "created") and submission_response.created
            )

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise JMAPError(f"Failed to send email: {e}")

    async def get_account_id(self) -> str:
        """Get the primary account ID."""
        if not self._client:
            raise JMAPError("Client not initialized")

        try:
            # jmapc handles account IDs internally
            return "primary"
        except Exception as e:
            logger.error(f"Failed to get account ID: {e}")
            raise JMAPError(f"Failed to get account ID: {e}")
