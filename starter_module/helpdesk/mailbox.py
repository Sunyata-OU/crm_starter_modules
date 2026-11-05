"""Reading a support mailbox, and turning what is in it into plain, safe text.

Two halves, kept apart so the interesting one needs no server to test:

* :func:`parse_mail` turns the raw bytes of one RFC 822 message into an
  :class:`InboundMail` -- headers decoded, a plain-text body, and the facts the
  ingest needs to decide what the message *is* (an auto-reply, say).
* :class:`ImapMailbox` is the thin network half. It only ever reads: it opens
  the folder read-only and fetches with ``BODY.PEEK``, so reading a message
  here never marks it seen. That matters while another system (the old Odoo
  fetchmail, a person in a mail client) is still working the same inbox: this
  must not change what they see.

**Everything inbound is attacker-controlled.** Nothing here returns HTML: an
HTML-only message is reduced to its text, attachments are counted and dropped,
and the body is capped. The helpdesk renders what this returns through the
same autoescaping templates as every other text field.
"""

from __future__ import annotations

import asyncio
import email
import hashlib
import imaplib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from email import policy
from email.message import EmailMessage
from email.utils import parseaddr, parsedate_to_datetime
from html.parser import HTMLParser
from typing import Protocol

#: A message body is cut here. A support mail is a few paragraphs; anything
#: longer is a forwarded thread or an accident, and a row that size helps nobody.
MAX_BODY = 20_000

#: Local parts that are a system talking, not a person: a reply to one is a loop.
_ROBOT_LOCALS = ("mailer-daemon", "postmaster", "no-reply", "noreply", "donotreply", "do-not-reply")


@dataclass(frozen=True, slots=True)
class InboundMail:
    """One received message, reduced to what the helpdesk uses."""

    message_id: str
    in_reply_to: str
    references: str
    sender_name: str
    sender_email: str
    subject: str
    body: str
    received_at: datetime | None
    #: A system, not a person: a bounce, an out-of-office, a list mailing.
    automatic: bool
    #: How many attachments were left out -- noted on the message, never stored.
    attachments: int = 0


class Mailbox(Protocol):
    """What the ingest needs from a mailbox, and nothing about how it is reached."""

    async def headers(self, since: date) -> Sequence[tuple[str, str]]:
        """``(uid, message_id)`` for every message since ``since``.

        ``message_id`` is empty for a message that has none.
        """
        ...

    async def fetch(self, uid: str) -> bytes:
        """The raw message, without marking it seen."""
        ...


# -- parsing ------------------------------------------------------------------


class _Text(HTMLParser):
    """The visible text of an HTML body: no tags, no scripts, no styles."""

    _SKIP = {"script", "style", "head", "title"}
    _BREAK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "blockquote"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip += 1
        elif tag in self._BREAK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip:
            self._skip -= 1
        elif tag in self._BREAK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _Text()
    parser.feed(html or "")
    parser.close()
    return _tidy("".join(parser.parts))


def _tidy(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _body_of(message: EmailMessage) -> str:
    part = message.get_body(preferencelist=("plain",))
    if part is not None:
        try:
            return _tidy(part.get_content())
        except (LookupError, UnicodeError):
            pass
    part = message.get_body(preferencelist=("html",))
    if part is not None:
        try:
            return html_to_text(part.get_content())
        except (LookupError, UnicodeError):
            pass
    return ""


def _is_automatic(message: EmailMessage, sender_email: str) -> bool:
    auto = str(message.get("Auto-Submitted") or "").strip().lower()
    if auto and auto != "no":
        return True
    if str(message.get("Precedence") or "").strip().lower() in {"bulk", "junk", "list", "auto_reply"}:
        return True
    if message.get("X-Autoreply") or message.get("X-Autorespond") or message.get("List-Id"):
        return True
    if str(message.get("X-Auto-Response-Suppress") or "").strip():
        return True
    if message.get_content_type() == "multipart/report":
        return True
    local = sender_email.split("@", 1)[0].lower()
    return local in _ROBOT_LOCALS


def synthetic_id(raw: bytes) -> str:
    """A stable Message-ID for a message that has none, so it is still deduplicated."""
    return f"<ingest-{hashlib.sha1(raw).hexdigest()[:32]}@helpdesk.local>"  # noqa: S324 -- not a secret


def parse_mail(raw: bytes) -> InboundMail:
    """One raw message, as the helpdesk will see it."""
    message = email.message_from_bytes(raw, policy=policy.default)
    assert isinstance(message, EmailMessage)  # noqa: S101 -- policy.default yields EmailMessage

    name, address = parseaddr(str(message.get("From") or ""))
    sender_email = address.strip().lower()

    received: datetime | None = None
    try:
        received = parsedate_to_datetime(str(message.get("Date")))
        if received.tzinfo is None:
            received = received.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        received = None

    body = _body_of(message)
    attachments = sum(1 for _ in message.iter_attachments())
    if len(body) > MAX_BODY:
        body = body[:MAX_BODY].rstrip() + "\n\n[message cut]"
    if attachments:
        body = (body + "\n\n" if body else "") + f"[{attachments} attachment(s) not stored]"

    return InboundMail(
        message_id=str(message.get("Message-ID") or "").strip() or synthetic_id(raw),
        in_reply_to=str(message.get("In-Reply-To") or "").strip(),
        references=" ".join(str(message.get("References") or "").split()),
        sender_name=name.strip(),
        sender_email=sender_email,
        subject=" ".join(str(message.get("Subject") or "").split()),
        body=body,
        received_at=received,
        automatic=_is_automatic(message, sender_email),
        attachments=attachments,
    )


# -- the network half ---------------------------------------------------------

_UID = re.compile(rb"UID (\d+)")
_MESSAGE_ID = re.compile(rb"^message-id:\s*(<[^>\r\n]+>)", re.IGNORECASE | re.MULTILINE)


class ImapMailbox:
    """A mailbox read over IMAP, read-only.

    ``imaplib`` is blocking, so every call runs in a worker thread; a connection
    is opened and closed within each call, which costs a little per message but
    means a dropped connection can only ever cost one message, never the run.
    """

    def __init__(self, host: str, *, port: int = 993, username: str = "", password: str = "",
                 ssl: bool = True, folder: str = "INBOX", timeout: float = 30.0) -> None:
        self.host, self.port, self.ssl = host, port, ssl
        self.username, self.password = username, password
        self.folder, self.timeout = folder, timeout

    def _connect(self) -> imaplib.IMAP4:
        client: imaplib.IMAP4 = (
            imaplib.IMAP4_SSL(self.host, self.port, timeout=self.timeout) if self.ssl
            else imaplib.IMAP4(self.host, self.port, timeout=self.timeout)
        )
        client.login(self.username, self.password)
        # readonly: the server will refuse anything that would change a flag.
        status, _ = client.select(f'"{self.folder}"', readonly=True)
        if status != "OK":
            client.logout()
            raise OSError(f"The mailbox has no folder {self.folder!r}.")
        return client

    def _headers(self, since: date) -> list[tuple[str, str]]:
        client = self._connect()
        try:
            status, data = client.uid("SEARCH", "SINCE", since.strftime("%d-%b-%Y"))
            if status != "OK" or not data or not data[0]:
                return []
            uids = data[0].split()
            found: list[tuple[str, str]] = []
            for start in range(0, len(uids), 200):
                chunk = b",".join(uids[start:start + 200]).decode()
                status, rows = client.uid("FETCH", chunk, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])")
                if status != "OK":
                    continue
                for index, row in enumerate(rows):
                    if not isinstance(row, tuple):
                        continue
                    # Servers disagree on where the UID goes: some put it before the
                    # header literal (`1 (UID 7 BODY[...] {n}`), others after it,
                    # as the trailing piece (`b' UID 7)'`). Look in both.
                    after = rows[index + 1] if index + 1 < len(rows) else b""
                    trailing = after if isinstance(after, bytes) else b""
                    uid = _UID.search(row[0] + b" " + trailing)
                    if uid is None:
                        continue
                    match = _MESSAGE_ID.search(row[1])
                    found.append((uid.group(1).decode(), match.group(1).decode() if match else ""))
            return found
        finally:
            client.logout()

    def _fetch(self, uid: str) -> bytes:
        client = self._connect()
        try:
            status, rows = client.uid("FETCH", uid, "(BODY.PEEK[])")
            if status != "OK":
                raise OSError(f"Could not read message {uid}.")
            for row in rows:
                if isinstance(row, tuple):
                    return bytes(row[1])
            raise OSError(f"Message {uid} was empty.")
        finally:
            client.logout()

    def _check(self) -> None:
        self._connect().logout()

    async def headers(self, since: date) -> Sequence[tuple[str, str]]:
        return await asyncio.to_thread(self._headers, since)

    async def fetch(self, uid: str) -> bytes:
        return await asyncio.to_thread(self._fetch, uid)

    async def check(self) -> None:
        """Log in and open the folder; raises if either fails."""
        await asyncio.to_thread(self._check)
