"""
Module to monitor file changes on a website and send alerts via Telegram.
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Callable, List, Any

import requests
import schedule
from bs4 import BeautifulSoup


@dataclass
class StepParams:
    """
    Represents parameters for a step in a configuration for automated tasks.

    Attributes:
        text (str): The text to search for in the HTML content.
        name (str): The name of the attribute to retrieve.
    """

    text: str = ""
    name: str = ""


@dataclass
class Step:
    """
    Represents a step in a configuration for automated tasks.

    Attributes:
        method (str): The method to be executed in this step.
        params (Dict[str, Union[str, None]]): Parameters for the method, stored as key-value pairs.
    """

    method: str
    params: StepParams


@dataclass
class Config:
    """
    Configuration for a specific automation task.

    Attributes:
        name (str): A descriptive name for the configuration.
        website (str): URL of the website associated with the configuration.
        steps (List[Step]): A list of `Step` objects outlining the process to be followed.
        bot_token (str): The bot token for Telegram bot integration.
        read_bot_token (str): The read-only bot token for Telegram bot integration.
        chat_id (str): The chat ID where the bot should send messages.
        schedule_interval (str): The scheduling interval (e.g., '1' for every minute).
    """

    name: str
    website: str
    steps: List[Step]
    bot_token: str
    read_bot_token: str
    chat_id: str
    schedule_interval: str


class WebsiteFileWatcher:
    """Class for monitoring file changes on a website and sending alerts via Telegram."""

    def __init__(self, config_file: str):
        """
        Initialize the WebsiteFileWatcher with configurations from the specified file.
        """
        self.config: list[Config] = self._load_configs(config_file)
        self.files: dict[str, str] = {}

    @staticmethod
    def _load_configs(config_file: str) -> List[Config]:
        """
        Load and parse configuration data from the JSON file into Config objects.
        Handling the case where 'params' key might be missing for some steps.
        """
        try:
            with open(config_file, "r", encoding="UTF-8") as f:
                data = json.load(f)
                return [
                    Config(
                        name=config["name"],
                        website=config["website"],
                        steps=[
                            Step(method=step["method"], params=StepParams(**step.get("params", {})))
                            for step in config["steps"]
                        ],
                        bot_token=config["bot_token"],
                        read_bot_token=config["read_bot_token"],
                        chat_id=config["chat_id"],
                        schedule_interval=config["schedule_interval"],
                    )
                    for config in data["configs"]
                ]
        except (OSError, json.JSONDecodeError) as e:
            print(f"Cannot read the json config file properly: {e}")
            sys.exit()
        except KeyError as e:
            print(f"Missing key in JSON data: {e}")
            sys.exit()

    def _perform_step(self, element: BeautifulSoup, step: Step):
        """
        Perform a step on an element using BeautifulSoup as per the step configuration.
        """
        step_methods: dict[str, Callable[[], Any]] = {
            "find_text": lambda: element.find(string=step.params.text),
            "parent": element.find_parent,
            "find_next_sibling": element.find_next_sibling,
            "get_attribute": lambda: element.get(step.params.name),
        }
        try:
            return step_methods[step.method]()
        except KeyError as exc:
            raise ValueError(f"Invalid method: {step.method}") from exc

    def _scrape_website_for_file_url(self, config: Config) -> str:
        """
        Scrape a specific website for a file URL based on steps in the config.
        """
        req = requests.get(config.website, timeout=10)
        soup = BeautifulSoup(req.content, "html.parser")

        for step in config.steps:
            soup = self._perform_step(soup, step)

        return str(soup)

    def _check_and_update_files(self, config: Config, element: str):
        """
        Check the scraped file and update if there are any changes.
        """
        if self.files.get(config.name) != element:
            if config.name in self.files:
                print("Changes detected")
                self._send_file_to_telegram(config)
            self.files[config.name] = element
        else:
            print("No change in file detected")

    def scrape_websites(self):
        """
        Scrape all websites as per the loaded configurations.
        """
        for config in self.config:
            file_url = self._scrape_website_for_file_url(config)
            print("File URL: ", file_url)
            self._check_and_update_files(config, file_url)

    def _send_file_to_telegram(self, config: Config):
        """
        Send a file to a Telegram chat.
        """
        file_url = self.files[config.name]
        url = (
            "https://api.telegram.org/bot"
            + config.bot_token
            + "/sendDocument?chat_id="
            + config.chat_id
            + "&document="
            + file_url
        )

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            print("New file sent to Telegram")
        else:
            print("Error sending file to Telegram")
            print(response.text)

    def read_last_message_from_telegram(self, config: Config) -> str:
        """
        Read the last message from a Telegram chat.
        """
        url = (
            "https://api.telegram.org/bot"
            + config.read_bot_token
            + "/getUpdates"
            + "?chat_id="
            + config.chat_id
        )

        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print("Error reading last message from Telegram")
            print(response.text)
            return ""
        try:
            last_msg = response.json().get("result", [])[-1]
            last_channel_post = last_msg.get("channel_post", {})
            return last_channel_post.get("text") or last_channel_post.get("document", {}).get(
                "file_name", ""
            )
        except IndexError:
            return ""

    def check_for_file_changes(self):
        """
        Check if there are any changes in the files and send them to Telegram.
        """
        for config in self.config:
            last_msg = self.read_last_message_from_telegram(config)
            file_name = self.files[config.name].split("/")[-1]

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
        for config in self.config:
            schedule.every(int(config.schedule_interval)).minutes.do(  # type: ignore # external lib
                self.scrape_websites
            )
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
    parser.add_argument("json_config", help="The name of the json_config file to process.")
    parser.add_argument(
        "-co",
        "--check_once",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Run check once, without scheduler.",
    )

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
