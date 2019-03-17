import requests
from bs4 import BeautifulSoup
import csv
import re
from PIL import Image
import requests
from io import BytesIO
import pandas as pd
import base64
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from email.utils import make_msgid

def dacha():
    data = []
    url_dacha = """https://www.avito.ru/map/items?s_trg=3&map=0&s=101&categoryId=25&params[202]=1065&params[528]=5476&priceMax=60000&searchArea%5BlatBottom%5D=55.72005475979617&searchArea%5BlonLeft%5D=37.274738034793494&searchArea%5BlatTop%5D=55.79468995796127&searchArea%5BlonRight%5D=37.42367475552823&viewPort%5Bwidth%5D=1015&viewPort%5Bheight%5D=902&page=1&limit=10"""
    r = requests.get(url_dacha)
    items = r.json()
    if items:
        for item in items:
            data.append({'title':'<a href="https://avito.ru{}">{}</a>'.format(item.get['url'], item.get['title']),
                         'price':item.get['pricePure'],
                         'metro':item.get['address'],
                         'photo':get_file("http:{}".format(item.get['image']))
                         })


def sendmail(me, you, list_items):
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
    response = requests.get(url, stream=True)
    img = Image.open(BytesIO(response.content))
    return img

def get_page_data(html):
    data = []
    soup = BeautifulSoup(html, 'lxml')
    divs = soup.find('div', class_='catalog-list')
    ads = divs.find_all('div', class_='item_table')
    for ad in ads:
        try:
            description = ad.find('div', class_='description')
            if (description.find(text=re.compile("author", re.IGNORECASE)) and description.find(text=re.compile("26")) and description.find(text=re.compile("подростковый", re.IGNORECASE))) \
                    or description.find(text=re.compile("sonic", re.IGNORECASE)) or description.find(text=re.compile("cosmic", re.IGNORECASE)):
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

                data.append({'title':'<a href="{}">{}</a>'.format(url, title),
                    'price':price,
                    'metro':metro,
                    'photo':photo})

        except Exception as exc:
            print ("Parse exception {}".format(str(exc)))
            continue

    return data

pd.set_option('display.max_colwidth', -1)

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
    url = "https://avito.ru/moskva?s_trg=3&q=author"
    base_url = "https://avito.ru/moskva?"
    page_part = "p="
    query_par = "&q=author"
    list_items = []

    #total_pages = get_total_pages(get_html(url))

    for i in range(1, 3):
        url_gen = base_url + page_part + str(i) + query_par
        html = get_html(url_gen)
        list_items += get_page_data(html)

    if list_items:
        #df = pd.DataFrame(list_items)
        #df.reset_index(drop=True)
        #html = df.to_html(formatters={'photo': image_formatter, 'price':str, 'title': str, 'metro':str, 'url':str }, escape=False)
        sendmail('dimbler@gmail.com', 'dimbler@gmail.com', list_items)
        print (list_items)

if __name__ == '__main__':
    dacha()