"""Filing a support mailbox: replies thread, duplicates are skipped, robots are ignored."""

from __future__ import annotations

import imaplib
from datetime import date
from email.message import EmailMessage

import pytest
from app.core.registry import Registry
from app.core.results import Ctx
from app.fields.types import DateTimeField, StatusField, TextAreaField, TextField
from app.providers.memory import MemoryProvider
from app.resources.resource import Resource

from starter_module.helpdesk import ingest as helpdesk_ingest
from starter_module.helpdesk import logic as helpdesk
from starter_module.helpdesk import mailbox

ME = "support@example.com"


def mail(subject="Help", body="Please help", *, frm="Robin <robin@example.com>", message_id=None,
         in_reply_to=None, references=None, headers=None, html=None, attachments=0, to=ME) -> bytes:
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = frm, to, subject
    m["Date"] = "Tue, 03 Nov 2026 10:00:00 +0200"
    if message_id:
        m["Message-ID"] = message_id
    if in_reply_to:
        m["In-Reply-To"] = in_reply_to
    if references:
        m["References"] = references
    for key, value in (headers or {}).items():
        m[key] = value
    if html is not None:
        m.set_content("fallback") if body is None else None
        m.add_alternative(html, subtype="html") if body is not None else m.set_content(html, subtype="html")
    else:
        m.set_content(body)
    for i in range(attachments):
        m.add_attachment(b"data", maintype="application", subtype="pdf", filename=f"f{i}.pdf")
    return m.as_bytes()


class FakeMailbox:
    def __init__(self, *raws: bytes) -> None:
        self.raws = {str(i + 1): r for i, r in enumerate(raws)}
        self.fetched: list[str] = []

    async def headers(self, since: date):
        out = []
        for uid, raw in self.raws.items():
            parsed = mailbox.parse_mail(raw)
            has_id = b"Message-ID" in raw
            out.append((uid, parsed.message_id if has_id else ""))
        return out

    async def fetch(self, uid: str) -> bytes:
        self.fetched.append(uid)
        return self.raws[uid]


def resources(tickets: MemoryProvider, messages: MemoryProvider) -> Registry:
    registry = Registry()
    registry.add_resource(Resource(
        "tickets", provider=tickets, audited=False, timeline=False,
        fields=[TextField("id", in_form=False), TextField("reference", in_form=False),
                TextField("subject"), TextField("requester_name"), TextField("requester_email"),
                StatusField("state", choices=[("new", "New", "blue"), ("open", "Open", "amber"),
                                              ("resolved", "Resolved", "green"),
                                              ("closed", "Closed", "grey")], default="new"),
                TextField("source"), TextField("thread_message_id"),
                DateTimeField("reminded_at")]))
    registry.add_resource(Resource(
        "ticket_messages", provider=messages, audited=False, timeline=False,
        fields=[TextField("id", in_form=False), TextField("ticket_id"), TextField("direction"),
                TextField("author"), TextAreaField("body"), TextField("message_id"),
                TextField("in_reply_to"), TextField("references"),
                DateTimeField("sent_at"), DateTimeField("received_at")]))
    return registry


@pytest.fixture
def stores():
    return MemoryProvider([]), MemoryProvider([])


@pytest.fixture
async def registry(stores):
    registry = resources(*stores)
    await registry.bind()
    yield registry
    await registry.close()


def rows(store: MemoryProvider) -> list[dict]:
    return list(store._rows.values())


async def run(registry, *raws, **kw):
    box = FakeMailbox(*raws)
    return await helpdesk_ingest.ingest(registry, box, Ctx.system(), **kw), box


# -- parsing -------------------------------------------------------------------


class TestParse:
    def test_plain_mail_is_read(self):
        m = mailbox.parse_mail(mail("Refund [T-7]", "Where is it?", message_id="<a@x>"))
        assert (m.subject, m.body, m.sender_email, m.sender_name) == (
            "Refund [T-7]", "Where is it?", "robin@example.com", "Robin")
        assert m.message_id == "<a@x>" and not m.automatic

    def test_html_only_mail_is_reduced_to_text_without_scripts(self):
        m = mailbox.parse_mail(mail(body="x", html="<style>p{}</style><p>Hello</p><script>alert(1)</script><p>World</p>"))
        assert "alert" not in m.body and "<" not in m.body
        assert "Hello" in m.body and "World" in m.body

    def test_attachments_are_counted_not_stored(self):
        m = mailbox.parse_mail(mail(body="see attached", attachments=2))
        assert m.attachments == 2 and "2 attachment(s) not stored" in m.body

    def test_a_missing_message_id_gets_a_stable_one(self):
        raw = mail()
        assert mailbox.parse_mail(raw).message_id == mailbox.parse_mail(raw).message_id
        assert mailbox.parse_mail(raw).message_id.startswith("<ingest-")

    def test_encoded_headers_are_decoded(self):
        m = mailbox.parse_mail(mail("Päring – töötuskindlustus", frm="Jüri Tamm <jyri@example.ee>"))
        assert m.subject == "Päring – töötuskindlustus" and m.sender_name == "Jüri Tamm"

    @pytest.mark.parametrize("headers,frm", [
        ({"Auto-Submitted": "auto-replied"}, "a@example.com"),
        ({"Precedence": "bulk"}, "a@example.com"),
        ({"List-Id": "<l.example.com>"}, "a@example.com"),
        ({}, "MAILER-DAEMON@example.com"),
        ({}, "noreply@example.com"),
    ])
    def test_robots_are_recognised(self, headers, frm):
        assert mailbox.parse_mail(mail(frm=frm, headers=headers)).automatic

    def test_a_person_is_not_automatic(self):
        assert not mailbox.parse_mail(mail(headers={"Auto-Submitted": "no"})).automatic

    def test_a_huge_body_is_cut(self):
        assert len(mailbox.parse_mail(mail(body="x" * 50_000)).body) < mailbox.MAX_BODY + 50


# -- filing --------------------------------------------------------------------


class TestFiling:
    async def test_a_new_mail_opens_an_email_ticket(self, registry, stores):
        counts, _ = await run(registry, mail("Where is my pay", message_id="<1@x>"))
        assert counts["new_tickets"] == 1
        ticket, = rows(stores[0])
        assert ticket["source"] == "email" and ticket["state"] == "new"
        assert ticket["requester_email"] == "robin@example.com" and ticket["thread_message_id"] == "<1@x>"
        message, = rows(stores[1])
        assert message["direction"] == "in" and message["ticket_id"] == ticket["id"]

    async def test_a_reply_with_the_subject_tag_joins_the_ticket(self, registry, stores):
        await stores[0].create({"reference": "T-5", "subject": "Pay", "state": "open"}, Ctx.system())
        counts, _ = await run(registry, mail("Re: [T-5] Pay", "Thanks", message_id="<2@x>"))
        assert counts == {**counts, "replies": 1, "new_tickets": 0}
        assert len(rows(stores[0])) == 1
        assert rows(stores[1])[0]["ticket_id"] == rows(stores[0])[0]["id"]

    async def test_a_reply_that_lost_the_tag_threads_by_message_id(self, registry, stores):
        ticket = (await stores[0].create({"reference": "T-5", "subject": "Pay", "state": "open"}, Ctx.system())).record
        await stores[1].create(helpdesk.new_message_fields(
            ticket_id=ticket.pk, direction="out", author="Sam", body="hi", message_id="<ours@x>"), Ctx.system())
        counts, _ = await run(registry, mail("Re: Pay", message_id="<3@x>", in_reply_to="<ours@x>"))
        assert counts["replies"] == 1 and len(rows(stores[0])) == 1

    async def test_a_customer_reply_reopens_a_resolved_ticket(self, registry, stores):
        await stores[0].create({"reference": "T-5", "subject": "Pay", "state": "resolved"}, Ctx.system())
        await run(registry, mail("[T-5] Pay", "still broken", message_id="<4@x>"))
        assert rows(stores[0])[0]["state"] == "open"

    async def test_an_open_ticket_keeps_its_state(self, registry, stores):
        await stores[0].create({"reference": "T-5", "subject": "Pay", "state": "new"}, Ctx.system())
        await run(registry, mail("[T-5] Pay", message_id="<5@x>"))
        assert rows(stores[0])[0]["state"] == "new"

    async def test_running_twice_files_nothing_twice(self, registry, stores):
        raws = (mail("A", message_id="<a@x>"), mail("B", message_id="<b@x>"))
        first, _ = await run(registry, *raws)
        second, box = await run(registry, *raws)
        assert first["new_tickets"] == 2 and second["new_tickets"] == 0 and second["duplicates"] == 2
        assert box.fetched == [] and len(rows(stores[0])) == 2

    async def test_a_message_without_an_id_is_still_deduplicated(self, registry, stores):
        raw = mail("No id")
        await run(registry, raw)
        second, _ = await run(registry, raw)
        assert second["duplicates"] == 1 and len(rows(stores[0])) == 1

    async def test_robots_and_our_own_address_are_skipped(self, registry, stores):
        counts, _ = await run(
            registry,
            mail("Out of office", message_id="<r@x>", headers={"Auto-Submitted": "auto-replied"}),
            mail("Bounce", message_id="<b@x>", frm="MAILER-DAEMON@example.com"),
            mail("Copy of ours", message_id="<o@x>", frm=ME),
            ignore_senders=[ME],
        )
        assert counts["automatic"] == 3 and not rows(stores[0])

    async def test_one_bad_message_does_not_stop_the_rest(self, registry, stores):
        class Bad(FakeMailbox):
            async def fetch(self, uid):
                if uid == "1":
                    raise OSError("connection reset")
                return await super().fetch(uid)

        box = Bad(mail("A", message_id="<a@x>"), mail("B", message_id="<b@x>"))
        counts = await helpdesk_ingest.ingest(registry, box, Ctx.system())
        assert counts["failed"] == 1 and counts["new_tickets"] == 1

    async def test_the_limit_leaves_the_rest_for_the_next_run(self, registry, stores):
        raws = [mail(f"S{i}", message_id=f"<{i}@x>") for i in range(5)]
        first, _ = await run(registry, *raws, limit=2)
        second, _ = await run(registry, *raws, limit=10)
        assert first["new_tickets"] == 2 and second["new_tickets"] == 3 and second["duplicates"] == 2

    async def test_nothing_happens_without_a_tickets_resource(self):
        counts = await helpdesk_ingest.ingest(Registry(), FakeMailbox(mail()), Ctx.system())
        assert not any(counts.values())

    async def test_bodies_are_stored_as_text_never_html(self, registry, stores):
        await run(registry, mail(body="x", html="<p onclick=x>Hi <b>there</b></p><script>1</script>", message_id="<h@x>"))
        body = rows(stores[1])[0]["body"]
        assert "<" not in body and "script" not in body.lower()


# -- the IMAP half, against a fake imaplib ----------------------------------------


class FakeImap:
    log: list[tuple] = []
    selected: dict = {}
    #: Where the server puts the UID in a header FETCH answer: "before" the literal
    #: (GreenMail) or "after" it, as a trailing piece (the real Zone server).
    uid_style = "before"

    def __init__(self, host, port=993, timeout=None):
        self.host = host

    def login(self, user, password):
        if password != "good":
            raise imaplib.IMAP4.error("bad credentials")

    def select(self, folder, readonly=False):
        FakeImap.selected = {"folder": folder, "readonly": readonly}
        return ("OK", [b"1"])

    def uid(self, command, *args):
        FakeImap.log.append((command, args))
        if command == "SEARCH":
            return ("OK", [b"11 12"])
        if args[1].startswith("(BODY.PEEK[HEADER"):
            if FakeImap.uid_style == "after":
                return ("OK", [(b"3 (BODY[HEADER.FIELDS (MESSAGE-ID)] {20}", b"Message-ID: <a@x>\r\n\r\n"), b" UID 11)",
                               (b"4 (BODY[HEADER.FIELDS (MESSAGE-ID)] {2}", b"\r\n"), b" UID 12)"])
            return ("OK", [(b"1 (UID 11 BODY[HEADER.FIELDS (MESSAGE-ID)] {20}", b"Message-ID: <a@x>\r\n\r\n"), b")",
                           (b"2 (UID 12 BODY[HEADER.FIELDS (MESSAGE-ID)] {2}", b"\r\n"), b")"])
        return ("OK", [(b"1 (UID 11 BODY[] {5}", b"RAW11"), b")"])

    def logout(self):
        pass


class TestImap:
    @pytest.fixture(autouse=True, params=["before", "after"])
    def fake(self, monkeypatch, request):
        FakeImap.log = []
        FakeImap.uid_style = request.param
        monkeypatch.setattr(imaplib, "IMAP4_SSL", FakeImap)

    async def test_it_lists_ids_and_reads_without_marking_anything_seen(self):
        """Run for both server layouts: the UID before the header literal, and after it."""
        box = mailbox.ImapMailbox("imap.test", username="u", password="good")
        assert list(await box.headers(date(2026, 11, 1))) == [("11", "<a@x>"), ("12", "")]
        assert await box.fetch("11") == b"RAW11"
        assert FakeImap.selected["readonly"] is True
        assert all("PEEK" in args[1] for cmd, args in FakeImap.log if cmd == "FETCH")

    async def test_bad_credentials_surface(self):
        box = mailbox.ImapMailbox("imap.test", username="u", password="nope")
        with pytest.raises(imaplib.IMAP4.error):
            await box.check()
