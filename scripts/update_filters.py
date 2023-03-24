import pathlib
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

import logging


logging.basicConfig(
    level=logging.INFO, 
    format='[%(asctime)s] %(levelname)-8s - %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S'
)


ANIMESATURN_URL  = "https://www.animesaturn.me/"
TEMPLATES_FOLDER = pathlib.Path("templates/")
OUTPUT_FILE      = pathlib.Path("animesaturn_filters.txt")

def main():
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
    
    logging.info(f"Found {len(domains)} domains: {', '.join(domains)}")

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
        logging.warning(f"Redirect detected: {' => '.join(redirects)}")

    logging.info(f"Found {len(valid_domains)} reachable domains: {', '.join(valid_domains)}")


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
        logging.info("Domains are already up to date.")
        logging.info("Nothing to do here. Exiting..")
        return True


    # ********** Save the new file **********
    logging.info("Changes detected. Updating file..")
    with open(OUTPUT_FILE, "w") as file:
        template = file.write(filter_content)

    logging.info("File 'animesaturn_filters.txt' updated successfully..")


def extract_domain(url):
    return re.sub(r"^www\.", "", urlparse(url).netloc)


if __name__ == '__main__':
    main()