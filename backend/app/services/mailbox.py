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
from email.utils import getaddresses, parseaddr, parsedate_to_datetime

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
    cc: str = ""
    attachments: list[MailAttachment] = field(default_factory=list)


def _mid(message_id: str) -> str:
    """Microsoft 365 message ids may contain "/" or "+": escape them in the URL path."""
    from urllib.parse import quote
    return quote(message_id, safe="")


def _html(text: str) -> str:
    """Plain text typed in the app as the HTML Outlook expects (escaped, line breaks kept)."""
    import html
    return html.escape(text).replace("\n", "<br>")


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
        try:
            async with httpx.AsyncClient(timeout=40) as client:
                r = await client.request(method, f"{GRAPH}/users/{self.mailbox}{path}", headers=await self._headers(text_body), **kw)
        except httpx.TimeoutException as exc:
            raise MailboxError("O Microsoft 365 demorou demasiado a responder. Tente novamente.") from exc
        except httpx.HTTPError as exc:
            raise MailboxError(f"Não foi possível contactar o Microsoft 365 ({exc.__class__.__name__}).") from exc
        if r.status_code == 403:
            raise MailboxError("O Microsoft 365 recusou o pedido (verifique as permissões Mail.ReadWrite e Mail.Send da app registration).")
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
        m = await self._call("GET", f"/messages/{_mid(message_id)}", text_body=True, params={
            "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,isRead,bodyPreview,hasAttachments,internetMessageId,body",
        })
        s = self._summary(m)
        to = ", ".join((r.get("emailAddress") or {}).get("address", "") for r in m.get("toRecipients") or [])
        cc = ", ".join((r.get("emailAddress") or {}).get("address", "") for r in m.get("ccRecipients") or [])
        attachments: list[MailAttachment] = []
        if s.has_attachments:
            # Reading only needs names and sizes; the files themselves are downloaded only to copy or forward them
            params = None if with_content else {"$select": "id,name,contentType,size,isInline"}
            data = await self._call("GET", f"/messages/{_mid(message_id)}/attachments", params=params)
            for a in data.get("value") or []:
                if a.get("isInline"):
                    continue  # images inside the text (e.g. signature logos)
                if with_content and a.get("@odata.type") != "#microsoft.graph.fileAttachment":
                    continue
                content = base64.b64decode(a["contentBytes"]) if with_content and a.get("contentBytes") else None
                attachments.append(MailAttachment(a.get("name") or "anexo", a.get("contentType") or "", int(a.get("size") or 0), content))
        return MailMessage(**s.__dict__, body=((m.get("body") or {}).get("content") or "").strip(), to=to, cc=cc, attachments=attachments)

    async def set_read(self, message_id: str, read: bool) -> None:
        await self._call("PATCH", f"/messages/{_mid(message_id)}", json={"isRead": read})

    async def archive(self, message_id: str) -> None:
        await self._call("POST", f"/messages/{_mid(message_id)}/move", json={"destinationId": "archive"})

    async def reply(self, message_id: str, text: str, reply_all: bool = False) -> None:
        # Outlook quotes the original message and keeps the conversation together
        await self._call("POST", f"/messages/{_mid(message_id)}/{'replyAll' if reply_all else 'reply'}", json={"comment": _html(text)})

    async def forward(self, message_id: str, recipients: list[tuple[str, str]], text: str) -> None:
        await self._call("POST", f"/messages/{_mid(message_id)}/forward", json={
            "comment": _html(text),
            "toRecipients": [{"emailAddress": {"address": a, "name": n or a}} for a, n in recipients],
        })

    async def delete(self, message_id: str) -> None:
        # To "Itens eliminados": can still be recovered in Outlook
        await self._call("POST", f"/messages/{_mid(message_id)}/move", json={"destinationId": "deleteditems"})


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
            to=_decode_header_value(msg.get("To", "")), cc=_decode_header_value(msg.get("Cc", "")), attachments=attachments,
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

    async def delete(self, message_id: str) -> None:
        raise MailboxError("Eliminar só está disponível com o Microsoft 365 (Graph).")

    async def reply(self, message_id: str, text: str, reply_all: bool = False) -> None:
        m = await self.get(message_id)
        own = mailbox_address().lower()
        to = [m.from_email]
        cc: list[str] = []
        if reply_all:
            cc = [a for _, a in getaddresses([m.to, m.cc]) if a and a.lower() not in {own, m.from_email}]
        subject = m.subject if m.subject.lower().startswith(("re:", "res:")) else f"RE: {m.subject}"
        headers = {"In-Reply-To": m.internet_message_id, "References": m.internet_message_id} if m.internet_message_id else {}
        await _smtp_send(to, cc, subject, f"{text}\n\n{_quote(m)}", headers)

    async def forward(self, message_id: str, recipients: list[tuple[str, str]], text: str) -> None:
        m = await self.get(message_id, with_content=True)
        subject = m.subject if m.subject.lower().startswith(("fw:", "fwd:", "enc:")) else f"FW: {m.subject}"
        await _smtp_send([a for a, _ in recipients], [], subject, f"{text}\n\n{_quote(m, forward=True)}", {}, m.attachments)


def _quote(m: MailMessage, forward: bool = False) -> str:
    head = "---------- Mensagem encaminhada ----------" if forward else "---------- Mensagem original ----------"
    return (f"{head}\nDe: {m.from_name} <{m.from_email}>\nData: {m.received_at}\nAssunto: {m.subject}\nPara: {m.to}\n\n"
            f"{m.body or m.preview}")


async def _smtp_send(to: list[str], cc: list[str], subject: str, text: str, headers: dict,
                     attachments: list[MailAttachment] | None = None) -> None:
    """Send from the helpdesk address through the configured SMTP (used with IMAP mailboxes)."""
    import os
    import shutil
    import tempfile
    from fastapi_mail import FastMail, MessageSchema, MessageType
    from app.services.email_service import _get_conf
    if not settings.mail_server:
        raise MailboxError("O envio de email (SMTP) não está configurado no servidor.")
    tmp_dir = tempfile.mkdtemp(prefix="helpdesk-fwd-")
    files = []
    try:
        for a in attachments or []:
            if a.content is None:
                continue
            path = os.path.join(tmp_dir, os.path.basename(a.name) or "anexo")
            with open(path, "wb") as f:
                f.write(a.content)
            files.append(path)
        message = MessageSchema(subject=subject, recipients=to, cc=cc, body=text, subtype=MessageType.plain,
                                headers=headers or None, attachments=files)
        await FastMail(_get_conf()).send_message(message)
    except MailboxError:
        raise
    except Exception as exc:
        raise MailboxError(f"O email não foi enviado: {exc}") from exc
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


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
