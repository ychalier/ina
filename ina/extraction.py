""" Extraction module

This module provides tools to extract relevant information from the Web. This
includes scraping the INA database, and further extend it with additionnal
information.
"""

import logging
import time
import os
import urllib.request
import tqdm
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select
from ina.database import InaEntry, EntryParsingException, load_database, save_database
from ina.tools import slugify, timed_loop, jaccard


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

    def __init__(self, driver_executable_path, implicit_wait=10, delay=1.5,
                 max_page_requests=1000):
        self.driver = None
        self.driver_executable_path = driver_executable_path
        self.implicit_wait = implicit_wait
        self.delay = delay
        self.max_page_requests = max_page_requests
        logging.debug(
            "Setting driver implicit wait to %f",
            self.implicit_wait
        )
        logging.debug(
            "Setting driver delay to %f",
            self.delay
        )
        logging.debug(
            "Setting driver max page requests to %d",
            self.max_page_requests
        )

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


def enrich_credits(entry):
    """Enrich the credits information of an entry"""
    if entry.credits.link is not None:
        html = urllib.request.urlopen(entry.credits.link).read().decode()
        soup = BeautifulSoup(html, "html.parser")
        element = soup.find("td", {"id": "GEN"})
        if element is not None:
            text = element.get_text().strip().replace("\t", "")
            entry.credits.text = text
            entry.credits.extract_text()


def enrich_media(entry):
    """Enrich media"""
    query_string = urllib.parse.urlencode(
        {"search_query": "%s %s" % (entry.title, entry.category.collection)}
    )
    html = urllib.request.urlopen(
        "http://www.youtube.com/results?" + query_string
    ).read().decode()
    soup = BeautifulSoup(html, "html.parser")
    search_results = list()
    for div in soup.find_all("div", {"class": "yt-lockup-video"}):
        duration_txt = div.find("span", {"class": "video-time"})\
            .get_text().strip()
        if len(duration_txt) == 5:
            duration_txt = "0:" + duration_txt
        duration = 0
        for base, factor in zip([3600, 60, 1], duration_txt.split(":")):
            duration += base * int(factor)
        search_result = {
            "duration": duration,
            "title":
                div.find("h3", {"class": "yt-lockup-title"})
            .find("a").get_text().strip(),
            "video_id":
                div.find("h3", {"class": "yt-lockup-title"})
            .find("a")["href"][-11:],
        }
        if entry.attributes.duration == 0:
            search_result["duration_error"] = 1
        else:
            search_result["duration_error"] =\
                abs(search_result["duration"] -
                    entry.attributes.duration)\
                / entry.attributes.duration
        search_result["title_error"] =\
            1 - jaccard(
                entry.category.collection + " " + entry.title,
                search_result["title"]
            )
        search_results.append(search_result)
    entry.media.video_ids = search_results[:]


def scrap(options):
    """Scrap initial data from https://inatheque.ina.fr/"""
    if options["append"]:
        database = open(options["database"], "a")
    else:
        if not options["skip-confirmation"]\
                and os.path.isfile(options["database"]):
            validation = input(
                "This action will reset the database at %s, continue? (y/n) "
                % os.path.abspath(options["database"])
            )
            if validation.lower() != "y":
                return
        database = open(options["database"], "w")
        database.write(InaEntry.HEADER + "\n")
    scraper = Scraper(
        options["driver-executable-path"],
        delay=options["delay"],
        max_page_requests=options["max-page-requests"]
    )
    scraper.initialize_driver()
    scraper.search(options["query"])
    added, ignored = 0, 0
    for result in scraper.get_results():
        if slugify(result.category.collection) not in options["filter-collections"]:
            ignored += 1
            continue
        added += 1
        result.diffusion.extract_datetime()
        result.attributes.extract_duration()
        database.write(result.serial() + "\n")
    database.close()
    logging.info(
        "Database contains %d entries (%d have been ignored)",
        added,
        ignored
    )


def enrich(options):
    """Enrich the credits and media information of the selected entries"""
    database = load_database(options)
    collection_filters = set(database)
    if len(options["filter-collections"]) > 0:
        collection_filters = options["filter-collections"]
    for slug in collection_filters:
        logging.info("Enriching collection %s", slug)
        iterator = timed_loop(
            tqdm.tqdm(database[slug]), delay=options["delay"])
        for entry in iterator:
            if not options["append"]\
                    or entry.credits.author is None\
                    or entry.credits.director is None:
                enrich_credits(entry)
            if not options["append"] or len(entry.media.video_ids) == 0:
                enrich_media(entry)
    save_database(options, database)
