import pathlib
import re
from datetime import datetime
import sys

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

import logging


ANIMESATURN_URL  = "https://www.animesaturn.me/"
TEMPLATES_FOLDER = pathlib.Path("templates/")
OUTPUT_FILE      = pathlib.Path("animesaturn_filters.txt")

LOG_FILENAME     = "./logs/updates_history.log"
LOG_MAX_LINES    = 100

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(
    logging.Formatter(
        '[%(asctime)s] %(levelname)-8s - %(message)s',
        '%d-%m-%Y %H:%M:%S'
    )
)


file_logger = logging.FileHandler(LOG_FILENAME)
file_logger.setLevel(logging.INFO)
file_logger.setFormatter(
    logging.Formatter(
        '[%(asctime)s] %(levelname)-8s - %(message)s',
        '%d-%m-%Y %H:%M:%S'
    )
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(stdout_handler)

execution_logger = logging.getLogger("execution_logger")
execution_logger.setLevel(logging.INFO)
execution_logger.addHandler(file_logger)


def main():
    # ********** Clean the log **********
    with open(LOG_FILENAME, "a+") as file:
        file.seek(0)
        lines = file.readlines()

        if len(lines) >= LOG_MAX_LINES:
            file.seek(0)
            file.truncate(0)
            file.writelines(lines[-LOG_MAX_LINES:])
            logger.debug(f"Log truncated to match maximum lines ({LOG_MAX_LINES})")



    # ********** Load the template **********
    template = ""
    with open(TEMPLATES_FOLDER / "animesaturn_filters.txt.template", "r") as file:
        template = file.read()


    # ********** Fetch the domains **********
    response = requests.get(ANIMESATURN_URL, allow_redirects=True)
    if not response.ok:
        return False

    # Parse html to find the list of domains
    soup = BeautifulSoup(response.text, features="html.parser")
    domains = list(map(lambda el: el["href"], soup.select("ol > li > a")))
    
    logger.info(f"Found {len(domains)} domains: {', '.join(domains)}")

    # Check which domains are available and which are redirects
    valid_domains = []
    for domain in domains:
        response = requests.get(domain, allow_redirects=True)
        redirects = [ extract_domain(res.url) for res in response.history if res.status_code == 301 ]
        final_url = extract_domain(response.url)

        if not redirects:
            valid_domains.append(final_url)
            continue
        
        redirects.append(final_url)
        logger.warning(f"Redirect detected: {' => '.join(redirects)}")

    logger.info(f"Found {len(valid_domains)} reachable domains: {', '.join(valid_domains)}")

    # Log the current reachable domains
    execution_logger.info(f"Found {len(valid_domains)} reachable domain(s): {','.join(valid_domains)}")

    # ********** Update the template **********
    filter_content = template.format(
        title="AnimeSaturn filters",
        version="1.0.0",
        last_modified=datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        expire="2 days",
        homepage="https://github.com/LukeSavefrogs/animesaturn-adblock/",
        website_domain=",".join([extract_domain(domain) for domain in domains]),
    )


    # ********** Check if something has changed **********
    old_filters = []
    new_filters = [line for line in filter_content.splitlines() if not line.startswith("!")]   # Comments start with an exclamation mark.

    with open(OUTPUT_FILE, "r") as file:
        old_filters = [line for line in file.read().splitlines() if not line.startswith("!")]  # Comments start with an exclamation mark.

    if old_filters == new_filters:
        logger.info("Domains are already up to date.")
        logger.info("Nothing to do here. Exiting..")
        return True


    # ********** Save the new file **********
    logger.info("Changes detected. Updating file..")
    with open(OUTPUT_FILE, "w") as file:
        template = file.write(filter_content)

    logger.info("File 'animesaturn_filters.txt' updated successfully..")
    execution_logger.info("File 'animesaturn_filters.txt' updated successfully")


def extract_domain(url):
    return re.sub(r"^www\.", "", urlparse(url).netloc)


if __name__ == '__main__':
    main()