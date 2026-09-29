"""Read the helpdesk mailbox inside the app ("Caixa de entrada"), through Microsoft Graph or IMAP — the same
connection used to import email replies (MAIL_REPLY_PROVIDER, GRAPH_MAIL_USER / IMAP_*)."""
from __future__ import annotations

import asyncio
import base64
import email
import imaplib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime

import httpx

from app.config import settings

logger = logging.getLogger(__name__)
GRAPH = "https://graph.microsoft.com/v1.0"
PAGE_SIZE = 25


class MailboxError(Exception):
    """Shown to the user (pt-PT)."""


@dataclass
class MailSummary:
    id: str
    subject: str
    from_name: str
    from_email: str
    received_at: str
    is_read: bool
    preview: str
    has_attachments: bool
    internet_message_id: str = ""


@dataclass
class MailAttachment:
    name: str
    content_type: str
    size: int
    content: bytes | None = None


@dataclass
class MailMessage(MailSummary):
    body: str = ""
    to: str = ""
    attachments: list[MailAttachment] = field(default_factory=list)


def mailbox_address() -> str:
    return (settings.graph_mail_user or settings.imap_username or settings.mail_username or settings.mail_from or "").strip()


def _iso(dt: datetime | None) -> str:
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


class GraphProvider:
    name = "graph"

    def __init__(self) -> None:
        self.mailbox = mailbox_address()

    async def _headers(self, text_body: bool = False) -> dict:
        from app.services.email_ingest import _get_graph_token
        token = await asyncio.to_thread(_get_graph_token)
        if not token:
            raise MailboxError("Não foi possível autenticar no Microsoft 365 (verifique as credenciais Azure e a permissão Mail.ReadWrite).")
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        if text_body:
            headers["Prefer"] = 'outlook.body-content-type="text"'
        return headers

    async def _call(self, method: str, path: str, text_body: bool = False, **kw) -> dict:
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.request(method, f"{GRAPH}/users/{self.mailbox}{path}", headers=await self._headers(text_body), **kw)
        if r.status_code == 403:
            raise MailboxError("O Microsoft 365 recusou o acesso à caixa (falta a permissão Mail.ReadWrite na app registration).")
        if r.status_code == 404:
            raise MailboxError("Mensagem ou caixa de correio não encontrada.")
        if r.status_code >= 400:
            raise MailboxError(f"Erro do Microsoft 365 ({r.status_code}).")
        return r.json() if r.content else {}

    @staticmethod
    def _summary(m: dict) -> MailSummary:
        sender = (m.get("from") or {}).get("emailAddress") or {}
        return MailSummary(
            id=m["id"], subject=m.get("subject") or "(sem assunto)", from_name=sender.get("name") or "",
            from_email=(sender.get("address") or "").lower(), received_at=m.get("receivedDateTime") or "",
            is_read=bool(m.get("isRead")), preview=(m.get("bodyPreview") or "")[:300],
            has_attachments=bool(m.get("hasAttachments")), internet_message_id=m.get("internetMessageId") or "",
        )

    async def list(self, page: int) -> tuple[list[MailSummary], bool]:
        data = await self._call("GET", "/mailFolders/inbox/messages", params={
            "$top": str(PAGE_SIZE + 1), "$skip": str((page - 1) * PAGE_SIZE), "$orderby": "receivedDateTime desc",
            "$select": "id,subject,from,receivedDateTime,isRead,bodyPreview,hasAttachments,internetMessageId",
        })
        rows = data.get("value") or []
        return [self._summary(m) for m in rows[:PAGE_SIZE]], len(rows) > PAGE_SIZE

    async def get(self, message_id: str, with_content: bool = False) -> MailMessage:
        m = await self._call("GET", f"/messages/{message_id}", text_body=True, params={
            "$select": "id,subject,from,toRecipients,receivedDateTime,isRead,bodyPreview,hasAttachments,internetMessageId,body",
        })
        s = self._summary(m)
        to = ", ".join((r.get("emailAddress") or {}).get("address", "") for r in m.get("toRecipients") or [])
        attachments: list[MailAttachment] = []
        if s.has_attachments:
            data = await self._call("GET", f"/messages/{message_id}/attachments")
            for a in data.get("value") or []:
                if a.get("@odata.type") != "#microsoft.graph.fileAttachment":
                    continue
                content = base64.b64decode(a["contentBytes"]) if with_content and a.get("contentBytes") else None
                attachments.append(MailAttachment(a.get("name") or "anexo", a.get("contentType") or "", int(a.get("size") or 0), content))
        return MailMessage(**s.__dict__, body=((m.get("body") or {}).get("content") or "").strip(), to=to, attachments=attachments)

    async def set_read(self, message_id: str, read: bool) -> None:
        await self._call("PATCH", f"/messages/{message_id}", json={"isRead": read})

    async def archive(self, message_id: str) -> None:
        await self._call("POST", f"/messages/{message_id}/move", json={"destinationId": "archive"})


class ImapProvider:
    name = "imap"
    can_archive = False

    def _connect(self) -> imaplib.IMAP4:
        user = settings.imap_username or settings.mail_username
        password = settings.imap_password or settings.mail_password
        if not settings.imap_server or not user or not password:
            raise MailboxError("A ligação IMAP não está configurada (IMAP_SERVER, IMAP_USERNAME, IMAP_PASSWORD).")
        cls = imaplib.IMAP4_SSL if settings.imap_ssl else imaplib.IMAP4
        client = cls(settings.imap_server, settings.imap_port)
        try:
            client.login(user, password)
            if client.select(settings.imap_folder or "INBOX")[0] != "OK":
                raise MailboxError("Pasta de correio não encontrada.")
        except imaplib.IMAP4.error as exc:
            raise MailboxError(f"O servidor de email recusou a ligação: {exc}") from exc
        return client

    @staticmethod
    def _parse(uid: str, raw: bytes, flags: bytes, with_content: bool = False) -> MailMessage:
        from app.services.email_ingest import _decode_header_value, _extract_text_body
        msg = email.message_from_bytes(raw)
        name, addr = parseaddr(_decode_header_value(msg.get("From", "")))
        try:
            received = _iso(parsedate_to_datetime(msg.get("Date")))
        except (TypeError, ValueError):
            received = ""
        body = _extract_text_body(msg).strip()
        attachments = []
        for part in msg.walk():
            filename = part.get_filename()
            if filename and part.get_content_maintype() != "multipart":
                payload = part.get_payload(decode=True) or b""
                attachments.append(MailAttachment(_decode_header_value(filename), part.get_content_type(), len(payload),
                                                  payload if with_content else None))
        return MailMessage(
            id=uid, subject=_decode_header_value(msg.get("Subject", "")) or "(sem assunto)", from_name=name,
            from_email=addr.lower(), received_at=received, is_read=b"\\Seen" in flags,
            preview=" ".join(body.split())[:300], has_attachments=bool(attachments),
            internet_message_id=(msg.get("Message-ID") or "").strip(), body=body,
            to=_decode_header_value(msg.get("To", "")), attachments=attachments,
        )

    def _fetch(self, client, uid: str) -> tuple[bytes, bytes]:
        status, data = client.uid("FETCH", uid, "(FLAGS BODY.PEEK[])")
        if status != "OK" or not data or not isinstance(data[0], tuple):
            raise MailboxError("Mensagem não encontrada.")
        return data[0][1], data[0][0]

    def _list(self, page: int):
        client = self._connect()
        try:
            status, data = client.uid("SEARCH", None, "ALL")
            uids = (data[0] or b"").split()[::-1]
            chunk = uids[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]
            items = []
            for uid in chunk:
                raw, meta = self._fetch(client, uid.decode())
                m = self._parse(uid.decode(), raw, meta)
                items.append(MailSummary(**{k: getattr(m, k) for k in MailSummary.__dataclass_fields__}))
            return items, len(uids) > page * PAGE_SIZE
        finally:
            try:
                client.logout()
            except Exception:
                pass

    async def list(self, page: int):
        return await asyncio.to_thread(self._list, page)

    def _get(self, uid: str, with_content: bool):
        client = self._connect()
        try:
            raw, meta = self._fetch(client, uid)
            return self._parse(uid, raw, meta, with_content)
        finally:
            try:
                client.logout()
            except Exception:
                pass

    async def get(self, message_id: str, with_content: bool = False) -> MailMessage:
        return await asyncio.to_thread(self._get, message_id, with_content)

    def _set_read(self, uid: str, read: bool):
        client = self._connect()
        try:
            client.uid("STORE", uid, "+FLAGS" if read else "-FLAGS", "(\\Seen)")
        finally:
            try:
                client.logout()
            except Exception:
                pass

    async def set_read(self, message_id: str, read: bool) -> None:
        await asyncio.to_thread(self._set_read, message_id, read)

    async def archive(self, message_id: str) -> None:
        raise MailboxError("Arquivar só está disponível com o Microsoft 365 (Graph).")


def get_provider():
    """The configured mailbox connection, or None when there is none."""
    provider = (settings.mail_reply_provider or "imap").strip().lower()
    if provider == "graph":
        if settings.azure_tenant_id and settings.azure_client_id and settings.azure_client_secret and mailbox_address():
            return GraphProvider()
        return None
    if settings.imap_server and (settings.imap_username or settings.mail_username):
        return ImapProvider()
    return None
