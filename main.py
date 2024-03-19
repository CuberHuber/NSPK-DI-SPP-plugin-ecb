import datetime
import re

from selenium import webdriver
from logging import config
from ecb import ECB
import pickle
import pandas

from src.spp.types import SPP_document

config.fileConfig('dev.logger.conf')


def driver():
    """
    Selenium web driver
    """
    options = webdriver.ChromeOptions()

    # Параметр для того, чтобы браузер не открывался.
    options.add_argument('headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('window-size=1920x1080')
    options.add_argument("disable-gpu")

    return webdriver.Chrome(options)


doc = SPP_document(id=None, title='Statement by the ECB Governing Council on advancing the Capital Markets Union',
                   abstract=None, text=None,
                   web_link='https://www.ecb.europa.eu/press/pr/date/2024/html/ecb.pr240307~76c2ab2747.en.html',
                   local_link=None, other_data={'category': 'PRESS RELEASE'},
                   pub_date=datetime.datetime(2024, 3, 7, 0, 0),
                   load_date=datetime.datetime(2024, 3, 19, 15, 2, 53, 813160))

parser = ECB(driver(), 10, doc)
docs: list[SPP_document] = parser.content()

print(*docs, sep='\n\r\n')
