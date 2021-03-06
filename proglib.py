import requests
from bs4 import BeautifulSoup
import csv
import re
from PIL import Image
import requests
from io import BytesIO
#import pandas as pd
import base64
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText;
from email.mime.image import MIMEImage

from email.utils import make_msgid
from sendmail import createMessageWithAttachment, SendMessage
import validators
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy.orm import mapper
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import datetime
import argparse

HTTP_PROXY = 'http://zabbix.online-acq.local:8888'

proxyDict = {
              "http"  : HTTP_PROXY,
              "https" : HTTP_PROXY
}

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(dest='list_emails', nargs='*', help='Path to configfile')
    return parser

Base = declarative_base()

class AvitoDB(Base):
    __tablename__ = 'advets'
    id = Column(Integer, primary_key=True)
    url = Column(String)
    title = Column(String)

    def __init__(self, url, title):
        self.url = url
        self.title = title

    def __repr__(self):
        return "<User('%s','%s')>" % (self.url, self.title)


def check_db_data(url, title):
    engine = create_engine('sqlite:///avito.db', echo=True)
    # Создание таблицы
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    check_url = session.query(AvitoDB).filter_by(url=url).first()
    if check_url:
        return True
    else:
        new_advert = AvitoDB(url, title)
        session.add(new_advert)
        session.commit()
        print ("Added advert {} to db {}".format(new_advert.title, new_advert.id))
        return False

def dacha():
    data = {}
    url_dacha = """https://www.avito.ru/map/items?s_trg=3&map=0&s=101&categoryId=25&params[202]=1065&params[528]=5476&priceMax=60000&searchArea%5BlatBottom%5D=55.72005475979617&searchArea%5BlonLeft%5D=37.274738034793494&searchArea%5BlatTop%5D=55.79468995796127&searchArea%5BlonRight%5D=37.42367475552823&viewPort%5Bwidth%5D=1015&viewPort%5Bheight%5D=902&page=1&limit=10"""
    r = requests.get(url_dacha)
    items = r.json()
    if items:
        for item in items.get('items', {}):
            data.update({"https://avito.ru{}".format(item.get('url')): {'title': item.get('title'),
                         'price':item.get('pricePure'),
                         'metro':item.get('address'),
                         'photo':get_file("http:{}".format(item.get('image')))
                         }})
    return  data

def old_sendmail(me, you, list_items):
    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('related')
    msg['Subject'] = "Finded bicycles in AVITO"
    msg['From'] = me
    msg['To'] = you
    msg.preamble = 'This is a multi-part message in MIME format.'

    msgAlternative = MIMEMultipart('alternative')
    msg.attach(msgAlternative)

    msgText = MIMEText('This is the alternative plain text message.')
    msgAlternative.attach(msgText)

    #msg.set_content('This is a plain text body.')
    html = """<b>Finded bycles in AVITO <br><table>"""
    for item in list_items:
        image_cid = make_msgid(domain='avito.ru')

        outbuf = BytesIO()
        item['photo'].save(outbuf, format="PNG")
        my_mime_image = MIMEImage(outbuf.getvalue())
        my_mime_image.add_header('Content-ID', image_cid)
        my_mime_image.add_header('Content-Disposition', 'inline', filename=image_cid)
        outbuf.close()
        msg.attach(my_mime_image)
        html += "<tr><td>{}</td><td>{}</td><td>{}</td><td><img src='cid:{}'></td></tr>".format(item['title'], item['price'], item['metro'], image_cid)
    html += "</table>"
    msgHtml = MIMEText(html, 'html')
    msgAlternative.attach(msgHtml)
    #msg.attach(msgHtml)
    #msg.add_alternative(html, subtype='html')

    import socks
    socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS4, 'zabbix.online-acq.local', 8888)
    socks.wrapmodule(smtplib)

    # Send the email (this example assumes SMTP authentication is required)
    mail = smtplib.SMTP('smtp.gmail.com', 587)

    mail.ehlo()

    mail.starttls()

    mail.login('dimbler', 'WMN3SS75')
    mail.sendmail(me, you, msg.as_string())
    mail.quit()

def get_html(url):
    r = requests.get(url)
    return r.text

def get_total_pages(html):
    soup = BeautifulSoup(html, 'lxml')
    divs = soup.find('div', class_='pagination-pages clearfix')
    pages = divs.find_all('a', class_='pagination-page')[-1].get('href')
    total_pages = pages.split('=')[1].split('&')[0]
    return int(total_pages)

def get_file(url):
    if validators.url(url):
        try:
            response = requests.get(url, stream=True)
            img = Image.open(BytesIO(response.content))
            return img
        except Exception as exc:
            return Image.new('RGB', (1, 1))
    else:
        return Image.new('RGB', (1, 1))

def get_page_data(html):
    data = {}
    soup = BeautifulSoup(html, 'lxml')
    divs = soup.find('div', class_='catalog-list')
    if divs:
        ads = divs.find_all('div', class_='item_table')
        for ad in ads:
            try:
                description = ad.find('div', class_='description')
                if (description.find(text=re.compile("author", re.IGNORECASE)) and description.find(text=re.compile("26")) and (description.find(text=re.compile("подростковый", re.IGNORECASE)) or description.find(text=re.compile("детский", re.IGNORECASE)))) \
                        or description.find(text=re.compile("sonic", re.IGNORECASE)) or description.find(text=re.compile("ultrasonic", re.IGNORECASE)):
                    title = ad.find('div', class_='description').find('h3').text.strip()

                    try:
                        photo_src = ad.find('div', class_='item-photo').find('li', class_='js-item-slider-item').find('img', class_='large-picture-img')['src']
                        if photo_src:
                            photo = get_file("http:{}".format(photo_src))
                        else:
                            photo = b''
                    except:
                        photo = b''

                    try:
                        div = ad.find('div', class_='description').find('h3')
                        url = "https://avito.ru" + div.find('a').get('href')
                    except:
                        url = ''

                    try:
                        price_text = ad.find('div', class_='about').text.strip()
                        price = price_text.encode('cp1251', 'ignore').strip()
                    except:
                        price = ''
                    try:
                        div = ad.find('div', class_='data')
                        metro = div.find_all('p')[-1].text.strip()
                    except:
                        metro = ''

                    data.update({url: {'title': title,
                        'price':price,
                        'metro':metro,
                        'photo':photo}})

            except Exception as exc:
                print ("Parse exception {}".format(str(exc)))
                continue

    return data

def get_thumbnail(path):
    i = Image.open(path)
    i.thumbnail((150, 150), Image.LANCZOS)
    return i

def image_base64(im):
    if isinstance(im, str):
        im = get_thumbnail(im)
    with BytesIO() as buffer:
        im.save(buffer, 'jpeg')
        return base64.b64encode(buffer.getvalue()).decode()

def image_formatter(im):
    return f'<img src="data:image/jpeg;base64,{image_base64(im)}">'

def velo():
    velo = {}

    url = "https://avito.ru/moskva?s_trg=3&q=author"
    base_url = "https://avito.ru/moskva?"
    page_part = "p="
    query_par = "&q=author"

    total_pages = get_total_pages(get_html(url))

    for i in range(1, total_pages):
        url_gen = base_url + page_part + str(i) + query_par
        html = get_html(url_gen)
        velo.update(get_page_data(html))
        #list_items += get_page_data(html)

    return velo
    """
    
    
    if list_items:
        #df = pd.DataFrame(list_items)
        #df.reset_index(drop=True)
        #html = df.to_html(formatters={'photo': image_formatter, 'price':str, 'title': str, 'metro':str, 'url':str }, escape=False)
        old_sendmail('dimbler@gmail.com', 'dimbler@gmail.com', list_items)
        print (list_items)
    """

def get_and_send(type_adverts, list_adverts, emails_to_send):
    keys = [key for key in list_adverts.keys()]
    for key in keys:
        if check_db_data(key, list_adverts.get(key, {}).get('title', '')):
            list_adverts.pop(key)

    if list_adverts:
        for email_to_send in emails_to_send:
            message = createMessageWithAttachment('dimbler@gmail.com', email_to_send, "Найденные {} на avito за {}".format(type_adverts, str(datetime.datetime.now())), list_adverts)
            result = SendMessage('dimbler@gmail.com', email_to_send, "Найденные дачки на avito", message)
            print (result)

def main_avito(args):

    if hasattr(args, 'list_emails'):
        list_emails = args.list_emails

        get_and_send('велики', velo(), list_emails)
        get_and_send('дачки ', dacha(), list_emails)

if __name__ == '__main__':
    main_avito(parse_arguments().parse_args())



