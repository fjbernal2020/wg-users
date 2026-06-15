#!/usr/bin/python3
# -*- coding: utf-8 -*-

import ssl
import smtplib
import mimetypes

from pathlib import Path
from email.message import EmailMessage
# -----------------------------------
class Mail:
    # -----------------------------------
    def __init__(self, server, login, sender, security='tls'):
        host, port = server.split(':', 1) if ':' in server else '', ''
        parts = server.split(':')
        self.server = parts[0]
        self.port = int(parts[1])
        self.user, self.pwd = login.split(':', 1)
        self.sender = sender
        self.security = security
    # -----------------------------------
    def send(self, to, subject, message=None, attachments=None, bcc=None):
        msg = EmailMessage()
        msg['From'] = self.sender
        msg['To'] = to
        if bcc:
            msg['Bcc'] = bcc
        msg['Subject'] = subject

        # ---- Cuerpo ----
        if message.startswith('<html>'):
            msg.set_content('')
            msg.add_alternative(html, subtype='html')
        else:
            msg.set_content(message or '')
        # ---- Adjuntos ----
        if attachments:
            if isinstance(attachments, str):
                attachments = [attachments]

            for file in attachments:
                p = Path(file)
                mime_type, _ = mimetypes.guess_type(p.name)

                if mime_type is None:
                    # Fallback seguro
                    mime_type = 'application/octet-stream'

                maintype, subtype = mime_type.split('/', 1)

                msg.add_attachment(
                    p.read_bytes(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=p.name,
                )
        # ---- Seguridad ----
        context = ssl.create_default_context()

        if self.security=='ssl':
            with smtplib.SMTP_SSL(self.server, self.port, context=context) as s:
                s.login(self.user, self.pwd)
                s.send_message(msg)

        elif self.security=='tls':
            with smtplib.SMTP(self.server, self.port) as s:
                s.starttls(context=context)
                s.login(self.user, self.pwd)
                s.send_message(msg)

        elif self.security==None:
            with smtplib.SMTP(host, port) as s:
                s.login(user, password)
                s.send_message(msg)
# -----------------------------------
