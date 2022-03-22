import logging
from datetime import datetime
from operator import itemgetter

import coloredlogs
import pandas as pd
import scrapy
from bs4 import BeautifulSoup
from scrapy.crawler import CrawlerProcess

coloredlogs.install()
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

results = []


def next_value(description, soup):
    cells = soup.find_all('div', class_="attribute")
    for cell in cells:
        for desc in cell.find_all('span', class_="name"):
            if desc.next_element.find(description) > -1:
                for value in cell.find_all('span', class_="value"):
                    return value.next_element


class GumtreeApartmentsSpider(scrapy.Spider):
    name = 'gumtreeapartmentsspider'
    start_urls = ['https://www.gumtree.pl/s-mieszkania-i-domy-sprzedam-i-kupie/warszawa/v1c9073l3200008p1']
    start_urls += [
        'https://www.gumtree.pl/s-mieszkania-i-domy-sprzedam-i-kupie/warszawa/page-' + str(
            i) + '/v1c9073l3200008p' + str(i) for i in range(2, 49)
    ]
    found_apartments = []

    custom_settings = {
        'DOWNLOAD_DELAY': 10,
        'ROBOTSTXT_OBEY': True,
        'AUTOTHROTTLE_ENABLED': True,
        'USER_AGENT': 'My Bot (email@myemail.com)'
    }

    top_url = 'https://www.gumtree.pl'

    def parse(self, response):
        self.logger.info('Got successful response from {}'.format(response.url))
        soup = BeautifulSoup(response.body, 'lxml')
        titles = [flat.next_element for flat in soup.find_all('a', class_="href-link tile-title-text")]
        links = ['https://www.gumtree.pl' + link.get('href')
                 for link in soup.find_all('a', class_="href-link tile-title-text")]

        for item_url in links:
            yield scrapy.Request(item_url, self.parse_item)

    def parse_item(self, response):
        self.logger.info('Got successful response from {}'.format(response.url))
        soup = BeautifulSoup(response.body, 'lxml')
        title = soup.find('span', class_="myAdTitle").getText()
        description = ''.join(map(str, soup.find('div', class_="description").find('span').findChildren()))

        values = [flat.next_element for flat in soup.find_all('span', class_="amount")]
        price = float(''.join(c for c in values[0] if c.isdigit()))

        item = {
            "url": response.url,
            "title": title,
            "description": description,
            "price": price
        }

        location = next_value('Lokalizacja', soup)
        district = location.find('a').getText()
        item['District'] = district

        tabular_items = ['m2', 'Data dodania', 'Na sprzedaż przez', 'Rodzaj nieruchomości', 'Liczba pokoi',
                         'Liczba łazienek']

        for label in tabular_items:
            item[label] = next_value(label, soup)

        results.append(item)
        self.logger.info(str(title))
        self.logger.info(str(description))


if __name__ == '__main__':
    process = CrawlerProcess()
    process.crawl(GumtreeApartmentsSpider)
    process.start()
    logger.info('Spider closed')

    data = {}
    for k in results[0].keys():
        data[k] = map(itemgetter(k), results)
    df = pd.DataFrame(data)
    now = datetime.now().strftime("%Y-%m-%d")
    df.to_csv(f"gumtree-{now}.tsv", sep='\t')
