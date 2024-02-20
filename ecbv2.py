"""
Нагрузка плагина SPP

1/2 документ плагина
"""
import datetime
import logging
import time

import dateutil.parser
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common import NoSuchElementException


from src.spp.types import SPP_document


class ECB:
    """
    Класс парсера плагина SPP

    :warning Все необходимое для работы парсера должно находится внутри этого класса

    :_content_document: Это список объектов документа. При старте класса этот список должен обнулиться,
                        а затем по мере обработки источника - заполняться.


    """

    SOURCE_NAME = 'ecb'
    _content_document: list[SPP_document]

    HOST = 'https://www.ecb.europa.eu/pub/pubbydate/html/index.en.html'

    def __init__(self, webdriver: WebDriver, years: list = None, max_count_documents: int = None, *args, **kwargs):
        """
        Конструктор класса парсера

        По умолчанию внего ничего не передается, но если требуется (например: driver селениума), то нужно будет
        заполнить конфигурацию
        """
        # Обнуление списка
        self._content_document = []

        self.driver = webdriver
        self.YEARS = years if years else [None,]
        self.max_count_documents = max_count_documents

        # Логер должен подключаться так. Вся настройка лежит на платформе
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(f"Parser class init completed")
        self.logger.info(f"Set source: {self.SOURCE_NAME}")
        ...

    def content(self) -> list[SPP_document]:
        """
        Главный метод парсера. Его будет вызывать платформа. Он вызывает метод _parse и возвращает список документов
        :return:
        :rtype:
        """
        self.logger.debug("Parse process start")
        self._parse()
        self.logger.debug("Parse process finished")
        return self._content_document

    def _parse(self):
        """
        Метод, занимающийся парсингом. Он добавляет в _content_document документы, которые получилось обработать
        :return:
        :rtype:
        """
        # HOST - это главная ссылка на источник, по которому будет "бегать" парсер
        self.logger.debug(F"Parser enter to {self.HOST}")

        # ========================================
        # Тут должен находится блок кода, отвечающий за парсинг конкретного источника
        # -
        self.driver.set_page_load_timeout(40)

        for year in self.YEARS:
            documents = self.prepared_doc_links(year)
            print(*documents, sep='\n\r')
            for index, doc in enumerate(documents):
                if doc.web_link.endswith('html'):
                    try:
                        self.driver.get(doc.web_link)
                        self.logger.debug('Entered on web page ' + doc.web_link)
                        time.sleep(2)

                        text = self.driver.find_element(By.CLASS_NAME, 'section').text
                        print(text)
                        try:
                            text += '\n\n' + self.driver.find_element(By.CLASS_NAME, 'footnotes').text
                        except:
                            pass
                        doc.text = text
                        doc.load_date = datetime.datetime.now()
                        self._content_document.append(doc)
                        self.logger.info(self._find_document_text_for_logger(doc))
                    except Exception as e:
                        self.logger.error(e)
        # ---
        # ========================================

    def prepared_doc_links(self, year: int = None) -> list[SPP_document]:
        """
        Метод проходит по главной странице, загружает секции и сохраняет заголовки, дату и ссылку на страницу документа
        """

        self._initial_access_source(self.HOST)
        lazy_load = self.driver.find_element(By.CLASS_NAME, 'lazy-load-hit')
        documents: list[SPP_document] = []

        if year:
            self._select_year('//*[@id="year"]', str(year))
            time.sleep(3)

        # Теперь на сайте один контейнер со всеми публикациями
        dl_wrapper = self.driver.find_element(By.CLASS_NAME, 'dl-wrapper')
        sections = dl_wrapper.find_elements(By.XPATH, '//*[@id="main-wrapper"]/main/div[2]/div[3]/div[2]/div[2]/dl')

        height_dl_wrapper = 0
        for section in sections:
            while True:
                # Прокрутка страницы до конца
                self.driver.execute_script("arguments[0].scrollIntoView();", lazy_load)

                # Проверка. Если появятся новые записи, то высота контента изменится
                # ! Можно оценивать количество элементов.
                if dl_wrapper.size['height'] > height_dl_wrapper:
                    height_dl_wrapper = dl_wrapper.size['height']
                    time.sleep(1)
                else:
                    break

            dts = section.find_elements(By.TAG_NAME, "dt")
            dds = section.find_elements(By.TAG_NAME, "dd")
            if len(dts) == len(dds):
                for date, body in zip(dts, dds):
                    try:
                        # self.driver.execute_script("arguments[0].scrollIntoView();", body)
                        doc = SPP_document(
                            None,
                            body.find_element(By.CLASS_NAME, 'title').text,
                            None,
                            None,
                            body.find_element(By.CLASS_NAME, 'title').find_element(By.TAG_NAME,
                                                                                   'a').get_attribute('href'),
                            None,
                            None,
                            dateutil.parser.parse(date.text),
                            None,
                        )
                        try:
                            doc.other_data = {
                                'category': body.find_element(By.CLASS_NAME, 'category').text,
                            }
                        except:
                            pass
                        if doc.web_link.endswith('html'):
                            documents.append(doc)
                            # Ограничение парсинга до установленного параметра self.max_count_documents
                            if len(documents) >= self.max_count_documents:
                                self.logger.debug('Max count documents reached')
                                return documents

                    except Exception as e:
                        self.logger.error(e)
                        continue
            else:
                self.logger.debug('Section parse error')
            break
        return documents

    def _select_year(self, xpath, value):
        """
        Выбирает один пункт из раскрывающегося списка по его xpath
        """
        try:
            select = self.driver.find_element(By.XPATH, xpath)
            options = select.find_elements(By.TAG_NAME, 'option')
            self.logger.debug(F"Filter by class name: {xpath}")
            for option in options:
                if option.get_attribute('value') == value and WebDriverWait(self.driver, 5).until(ec.element_to_be_clickable(option)):
                    # select.click()
                    option.click()
                    self.logger.debug(F"Choice option '{value}' at select by class name: {xpath}")
                    break
            raise f'The selected value {value} is not found'
        except Exception as e:
            self.logger.debug(f'{e}')

    def _initial_access_source(self, url: str, delay: int = 2):
        """
        Первичный доступ к странице с прохождением возможной капчи или модальных окон
        """

        self.driver.get(url)
        self.logger.debug('Entered on web page '+url)
        time.sleep(delay)
        self._agree_cookie_pass()

    def _agree_cookie_pass(self):
        """
        Метод прожимает кнопку agree на модальном окне
        """
        cookie_agree_xpath = '//*[@id="cookieConsent"]/div[1]/div/a[1]'

        try:
            cookie_button = self.driver.find_element(By.XPATH, cookie_agree_xpath)
            if WebDriverWait(self.driver, 5).until(ec.element_to_be_clickable(cookie_button)):
                cookie_button.click()
                self.logger.debug(F"Parser pass cookie modal on page: {self.driver.current_url}")
        except NoSuchElementException as e:
            self.logger.debug(f'modal agree not found on page: {self.driver.current_url}')
        except Exception as e:
            self.logger.error(f'some error occured on page: {self.driver.current_url}. Error: {e}')

    @staticmethod
    def _find_document_text_for_logger(doc: SPP_document):
        """
        Единый для всех парсеров метод, который подготовит на основе SPP_document строку для логера
        :param doc: Документ, полученный парсером во время своей работы
        :type doc:
        :return: Строка для логера на основе документа
        :rtype:
        """
        return f"Find document | name: {doc.title} | link to web: {doc.web_link} | publication date: {doc.pub_date}"
