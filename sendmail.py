import httplib2
import os
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from apiclient import errors, discovery
import mimetypes
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
import pickle
from PIL import Image
from io import BytesIO

from email.utils import make_msgid

SCOPES = 'https://www.googleapis.com/auth/gmail.send'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Gmail API Python Send Email'

def get_credentials():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds

def SendMessage(sender, to, subject, msgEncoded):
    credentials = get_credentials()
    service = build('gmail', 'v1', credentials=credentials)
    result = SendMessageInternal(service, "me", msgEncoded)
    return result

def SendMessageInternal(service, user_id, message):
    try:
        message = (service.users().messages().send(userId=user_id, body=message).execute())
        print('Message Id: %s' % message['id'])
        return message
    except errors.HttpError as error:
        print('An error occurred: %s' % error)
        return "Error"
    return "OK"

def CreateMessageHtml(sender, to, subject, msgPlain):
    """Create a message for an email.

    Args:
      sender: Email address of the sender.
      to: Email address of the receiver.
      subject: The subject of the email message.
      message_text: The text of the email message.

    Returns:
      An object containing a base64url encoded email object.
    """
    message = MIMEText(msgPlain)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_string().encode('UTF-8')).decode('ascii')}

from random import choice
import string
def GenPasswd2(length=8, chars=string.ascii_letters + string.digits):
    return ''.join([choice(chars) for i in range(length)])

def createMessageWithAttachment(
        sender, to, subject, list_items):
    """Create a message for an email.

    Args:
      sender: Email address of the sender.
      to: Email address of the receiver.
      subject: The subject of the email message.
      message_text: The text of the email message.
      file: The path to the file to be attached.

    Returns:
      An object containing a base64url encoded email object.
    """
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    #msg = MIMEText(message_text)
    #message.attach(msg)

    html = """<b>{}</b></br></br><table border="1">""".format(subject)
    for key, item in list_items.items():
        try:
            #image_cid = make_msgid(domain='avito.ru')
            image_cid = GenPasswd2(8,string.digits)
            outbuf = BytesIO()
            item.get('photo', Image.new('RGB', (1, 1))).save(outbuf, format="PNG")
            my_mime_image = MIMEImage(outbuf.getvalue(), 'png')
            my_mime_image.add_header('Content-ID', "<{}>".format(image_cid))
            my_mime_image.add_header('Content-Disposition', 'inline', filename=image_cid)
            outbuf.close()
            message.attach(my_mime_image)
        except Exception as exc:
            print ("Cannot attach picture {}".format(str(exc)))
        html += "<tr><td><a href='{}'>{}</a></td><td>{}</td><td>{}</td><td><img src='cid:{}' /></td></tr>".format(key, item.get('title', ''),item.get('price', ''),item.get('metro', ''), image_cid)
    html += "</table>"
    msgHtml = MIMEText(html, 'html')
    """
    content_type = 'application/octet-stream'
    main_type, sub_type = content_type.split('/', 1)
    if main_type == 'text':
        fp = open(file, 'rb')
        msg = MIMEText(fp.read(), _subtype=sub_type)
        fp.close()
    elif main_type == 'image':
        fp = open(file, 'rb')
        msg = MIMEImage(fp.read(), _subtype=sub_type)
        fp.close()
    elif main_type == 'audio':
        fp = open(file, 'rb')
        msg = MIMEAudio(fp.read(), _subtype=sub_type)
        fp.close()
    else:
        fp = open(file, 'rb')
        msg = MIMEBase(main_type, sub_type)
        msg.set_payload(fp.read())
        fp.close()
    filename = os.path.basename(file)
    msg.add_header('Content-Disposition', 'attachment', filename=filename)
    """
    message.attach(msgHtml)

    b64_bytes = base64.urlsafe_b64encode(message.as_bytes())
    b64_string = b64_bytes.decode()
    body = {'raw': b64_string}

    return body


def main():
    to = "dimbler@gmail.com"
    sender = "dimbler@gmail.com"
    subject = "subject"
    msgHtml = "Hi<br/>Html Email"
    msgPlain = "Hi\nPlain Email"
    SendMessage(sender, to, subject, msgPlain)
    # Send message with attachment:
    #SendMessage(sender, to, subject, msgHtml, msgPlain, '/path/to/file.pdf')

if __name__ == '__main__':
    main()