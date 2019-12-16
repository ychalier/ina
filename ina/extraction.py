""" Extraction module

This module provides tools to extract relevant information from the Web. This
includes scraping the INA database, and further extend it with additionnal
information.
"""

import logging
import time
import os
import urllib
import re
import tqdm
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from ina.database import InaEntry
from ina.database import EntryParsingException
from ina.database import load_database, save_database
from ina.tools import slugify
from ina.tools import timed_loop


def scrap_result_page(html):
    """Reads the HTML source code of a result from inatheque.ina.fr and yields
       results as they are found. If an error occurs during the extraction,
       then a None is yielded.
    """
    soup = BeautifulSoup(html, "html.parser")
    table_div = soup.find("div", {"id": Scraper.RESULT_TABLE_ID})
    header_row = True
    for row in table_div.find_all("tr"):
        if header_row:
            header_row = False
            continue
        try:
            result = InaEntry()
            result.parse(row)
            yield result
        except EntryParsingException as err:
            logging.warning("Result extraction error: %s", err)
            yield None


def scrap(options):
    """Scraping action"""
    if not options["skip_confirmation"] and os.path.isfile(options["database"]):
        validation = input(
            "This action will reset the database at %s, continue? (y/n) "
            % os.path.abspath(options["database"])
        )
        if validation.lower() != "y":
            return
    database = open(options["database"], "w")
    database.write(InaEntry.HEADER + "\n")
    scraper = Scraper("/usr/local/bin/geckodriver", delay=options["delay"])
    scraper.initialize_driver()
    scraper.search(options["query"])
    added, ignored = 0, 0
    for result in scraper.get_results():
        if slugify(result.category.collection) not in options["collection_slugs"]:
            ignored += 1
            continue
        added += 1
        result.diffusion.extract_datetime()
        result.attributes.extract_duration()
        database.write(result.serial() + "\n")
    database.close()
    logging.info("Database contains %d entries (%d have been ignored)", added, ignored)


def enrich(options):
    """Enrich options"""
    database = load_database(options)
    collection_filters = set(database)
    if len(options["collection_slugs"]) > 0:
        collection_filters = options["collection_slugs"]
    for slug in collection_filters:
        logging.info("Enriching collection %s", slug)
        for entry in timed_loop(tqdm.tqdm(database[slug]), delay=options["delay"]):
            if entry.credits.link is not None:
                html = urllib.request.urlopen(entry.credits.link).read().decode()
                soup = BeautifulSoup(html, "html.parser")
                element = soup.find("td", {"id": "GEN"})
                if element is not None:
                    text = element.get_text().strip().replace("\t", "")
                    entry.credits.text = text
                    entry.credits.extract_text()
                query_string = urllib.parse.urlencode(
                    {"search_query" : "%s %s" % (entry.title, entry.category.collection)}
                )
                html_content = urllib.request.urlopen(
                    "http://www.youtube.com/results?" + query_string
                )
                search_results = re.findall(
                    r"href=\"\/watch\?v=(.{11})",
                    html_content.read().decode()
                )
                entry.media.video_ids = search_results[:]
                entry.media.remove_duplicate_ids()
    save_database(options, database)

class Scraper:

    """A web scraper for http://inatheque.ina.fr/ main result page, based
       on selenium.
    """

    SEARCH_URL = "http://inatheque.ina.fr/"
    XPATHS = {
        "search_form": "/html/body/div[5]/div/div[1]/div/div[2]/div[3]/form",
        "search_input": ("/html/body/div[5]/div/div[1]/div/div[2]/div[3]/form"
                         "/fieldset[1]/div/input[5]"),
        "next_link": ("/html/body/div[5]/div/div[2]/div[3]/div[3]/div[2]"
                      "/div[3]/div[3]/a"),
        "results_count_div": ("/html/body/div[5]/div/div[2]/div[3]/div[3]"
                              "/div[1]"),
        "results_per_page_select": ("/html/body/div[5]/div/div[1]/div/div[2]"
                                    "/div[3]/form/fieldset[3]/table/tbody/"
                                    "tr[2]/td[2]/select"),
    }
    RESULT_TABLE_ID = "result-tableau-1"

    def __init__(self, driver_executable_path, implicit_wait=10, delay=1.5, max_page_requests=1000):
        self.driver = None
        self.driver_executable_path = driver_executable_path
        self.implicit_wait = implicit_wait
        self.delay = delay
        self.max_page_requests = max_page_requests
        logging.info("Setting driver implicit wait to %f", self.implicit_wait)
        logging.info("Setting driver delay to %f", self.delay)
        logging.info("Setting driver max page requests to %d", self.max_page_requests)

    def initialize_driver(self):
        """Creates the selenium driver"""
        options = Options()
        options.headless = True
        logging.info(
            "Initializing selenium driver at %s",
            os.path.abspath(self.driver_executable_path)
        )
        self.driver = webdriver.Firefox(
            options=options,
            executable_path=self.driver_executable_path
        )
        self.driver.implicitly_wait(self.implicit_wait)

    def search(self, query):
        """Write the query and submit it"""
        logging.info("Driver is reaching URL %s", Scraper.SEARCH_URL)
        self.driver.get(Scraper.SEARCH_URL)
        current_url = self.driver.current_url
        search_input = self.driver.find_element_by_xpath(
            Scraper.XPATHS["search_input"])
        logging.info("Input query is '%s'", query)
        search_input.send_keys(query)
        select = Select(self.driver.find_element_by_xpath(
            Scraper.XPATHS["results_per_page_select"]))
        options = [o.get_attribute('value') for o in select.options]
        select.select_by_value(options[-1])
        form = self.driver.find_element_by_xpath(Scraper.XPATHS["search_form"])
        logging.debug("Submitting search form and waiting for result page")
        form.submit()
        WebDriverWait(self.driver, self.implicit_wait).until(
            EC.url_changes(current_url))
        logging.debug("Reached result page")

    def get_results(self):
        """Yield all results one by one, and only correct ones"""
        last_request = time.time()
        results_count_div = self.driver.find_element_by_xpath(
            Scraper.XPATHS["results_count_div"])
        result_count = int(results_count_div.text.split(" ")[-1])
        result_per_page = int(results_count_div.text.split(" ")[3])
        page_count = 1 + ((result_count - 1) // result_per_page)
        logging.info(
            "Scraper found %d results (%d per page, %d pages)",
            result_count,
            result_per_page,
            page_count
        )
        if page_count > self.max_page_requests:
            page_count = self.max_page_requests
            logging.info("Forcing number of page requests to %d", page_count)
        iterator = tqdm.tqdm(range(1, page_count + 1))
        for i in iterator:
            for j, result in enumerate(scrap_result_page(self.driver.page_source)):
                if result is not None:
                    yield result
                else:
                    logging.warning(
                        "Error while extracting row %d of page %d", j + 1, i)
            if i < page_count:
                next_link = self.driver.find_elements_by_xpath(
                    Scraper.XPATHS["next_link"])
                if len(next_link) == 0:
                    logging.warning("Next link not found")
                    iterator.close()
                    break
                next_link = next_link[0]
                time_since_last_request = time.time() - last_request
                time_to_wait = max(0, self.delay - time_since_last_request)
                next_link.click()
                time.sleep(time_to_wait)
                last_request = time.time()
