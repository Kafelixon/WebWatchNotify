import json
import argparse
import requests
import re
import time
import schedule
from bs4 import BeautifulSoup


class FileWatcher:
    """Class for watching for changes of files on a website"""

    def __init__(self):
        try:
            with open("example.json") as f:
                data = json.load(f)
                configs = data["configs"]
        except (OSError, json.JSONDecodeError) as e:
            print("Cannot read the json config file properly\n", e)
            exit()
        except KeyError as e:
            print("Cannot read json property", e)
            exit()

        self.configs: list[dict] = configs
        self.files: dict = {}

    def scrape_website_for_file_url(self, config: dict) -> str:
        """
        Scrapes a website for a specific file URL based on a set of steps.

        Parameters:
        config (dict): A dictionary containing the website to scrape and the steps to perform. 
                    The website is specified by the "website" key, 
                    and the steps are specified by the "steps" key, which should be a list of steps.

        Returns:
        file_url (str): The file URL extracted from the website after performing all the steps
                    specified in the config. The URL is returned as a string.
        """

        req = requests.get(config["website"])
        soup = BeautifulSoup(req.content, "html.parser")

        for step in config['steps']:
            soup = self.perform_step(soup, step)

        return str(soup)

    def check_and_update_files(self, config, element):
        if config["name"] not in self.files or self.files[config["name"]] != element:
            if config["name"] in self.files:
                print("Changes detected")
            self.files[config["name"]] = element

    def scrape_websites(self):
        for config in self.configs:
            file_url = self.scrape_website_for_file_url(config)
            self.check_and_update_files(config, file_url)

            print(self.files)

    def perform_step(self, element: BeautifulSoup, step: dict) -> BeautifulSoup:
        if element is None:
            raise ValueError(
                'Element is None, check your steps. If you are looking for text, remember the spaces.')
        method = step['method']
        if method == 'find_text':
            return element.find(string=step['params']['text'])
        elif method == 'parent':
            return element.find_parent()
        elif method == 'find_next_sibling':
            return element.find_next_sibling()
        elif method == 'get_attribute':
            return element.get(step['params']['name'])
        else:
            raise ValueError(f'Invalid method: {method}')


def main():
    # Initialize the ArgumentParser object
    parser = argparse.ArgumentParser()

    # Add arguments
    parser.add_argument(
        "json_config", help="The name of the json_config file to process.")
    parser.add_argument("-co", "--check_once", action=argparse.BooleanOptionalAction, default=False,
                        help="Run check once, without scheduler.")

    # Parse the arguments
    args = parser.parse_args()

    watcher = FileWatcher()
    watcher.scrape_websites()
    if not args.check_once:
        print("Scheduler started")
        schedule.every(1).minutes.do(watcher.scrape_websites)
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == '__main__':
    main()
