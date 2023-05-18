import json
import argparse
import requests
from bs4 import BeautifulSoup
import schedule
import time


class WebsiteFileWatcher:
    """Class for monitoring file changes on a website and sending alerts via Telegram."""

    def __init__(self, config_file: str):
        """
        Initialize the WebsiteFileWatcher with configurations from the specified file.
        """
        self.configs: list[dict] = self._load_configs(config_file)["configs"]
        self.files = {}

    @staticmethod
    def _load_configs(config_file: str):
        """
        Load the configuration data from the JSON file.
        """
        try:
            with open(config_file) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Cannot read the json config file properly\n {e}")
            exit()
        except KeyError as e:
            print(f"Cannot read json property {e}")
            exit()

    def _perform_step(self, element: BeautifulSoup, step: dict) -> BeautifulSoup:
        """
        Perform a step on an element using BeautifulSoup as per the step configuration.
        """
        step_methods = {
            'find_text': lambda: element.find(string=step['params']['text']),
            'parent': lambda: element.find_parent(),
            'find_next_sibling': lambda: element.find_next_sibling(),
            'get_attribute': lambda: element.get(step['params']['name']),
        }
        try:
            return step_methods[step['method']]()
        except KeyError:
            raise ValueError(f'Invalid method: {step["method"]}')

    def _scrape_website_for_file_url(self, config: dict) -> str:
        """
        Scrape a specific website for a file URL based on steps in the config.
        """
        req = requests.get(config["website"])
        soup = BeautifulSoup(req.content, "html.parser")

        for step in config['steps']:
            soup = self._perform_step(soup, step)

        return str(soup)

    def _check_and_update_files(self, config, element):
        """
        Check the scraped file and update if there are any changes.
        """
        if self.files.get(config["name"]) != element:
            if config["name"] in self.files:
                print("Changes detected")
                self._send_file_to_telegram(config)
            self.files[config["name"]] = element
        else:
            print("No change in file detected")

    def scrape_websites(self):
        """
        Scrape all websites as per the loaded configurations.
        """
        for config in self.configs:
            file_url = self._scrape_website_for_file_url(config)
            self._check_and_update_files(config, file_url)

    def _send_file_to_telegram(self, config: dict):
        """
        Send a file to a Telegram chat.
        """
        bot_token = config["bot_token"]
        chat_id = config["chat_id"]
        file_url = self.files[config["name"]]
        url = f"https://api.telegram.org/bot{bot_token}/sendDocument?chat_id={chat_id}&document={file_url}"

        response = requests.get(url)
        if response.status_code == 200:
            print("New file sent to Telegram")
        else:
            print("Error sending file to Telegram")
            print(response.text)

    def read_last_message_from_telegram(self, config: dict) -> str:
        """
        Read the last message from a Telegram chat.
        """
        read_bot_token = config["read_bot_token"]
        chat_id = config["chat_id"]
        url = f"https://api.telegram.org/bot{read_bot_token}/getUpdates?chat_id={chat_id}"

        response = requests.get(url)
        if response.status_code != 200:
            print("Error reading last message from Telegram")
            print(response.text)
            return ""

        last_msg = response.json().get("result", [])[-1]
        last_channel_post = last_msg.get("channel_post", {})
        return last_channel_post.get("text") or last_channel_post.get("document", {}).get("file_name", "")

    def check_for_file_changes(self):
        for config in self.configs:
            print("Checking file:", config)
            print("Checking file:", config["name"])
            last_msg = self.read_last_message_from_telegram(config)
            file_name = self.files[config["name"]].split("/")[-1]
            if last_msg != file_name:
                print("Change in file detected")
                self._send_file_to_telegram(config)
            else:
                print("No change in file detected")

    def run_schedule(self):
        """
        Start the scheduler to scrape the websites at specified intervals.
        """
        print("Scheduler started")
        for config in self.configs:
            schedule.every(int(config["schedule_interval"])).minutes.do(
                self.scrape_websites)

        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nProgram terminated by user. Bye!")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "json_config", help="The name of the json_config file to process.")
    parser.add_argument("-co", "--check_once", action=argparse.BooleanOptionalAction, default=False,
                        help="Run check once, without scheduler.")

    return parser.parse_args()


def main():
    """
    Main function to start the file watcher and optionally the scheduler.
    """
    args = parse_arguments()
    watcher = WebsiteFileWatcher(args.json_config)
    watcher.scrape_websites()
    watcher.check_for_file_changes()

    if not args.check_once:
        watcher.run_schedule()


if __name__ == "__main__":
    main()
