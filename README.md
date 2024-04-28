# WebWatchNotify

WebWatchNotify is an application designed to monitor specific files
on websites and notify you via Telegram whenever there's a change.

## Features

1. **Multiple Site Monitoring:**
Allows users to monitor multiple websites for file changes simultaneously.
2. **Specific File Tracking:**
Enables monitoring of specific files within the website's HTML.
3. **Telegram Integration:**
Sends real-time notifications to a specified Telegram group or channel when
changes are detected.
4. **JSON Configuration:**
Allows users to easily set up the websites to monitor and the Telegram
details using JSON configuration files.

## Technologies Used

- Python
- Requests or BeautifulSoup for HTTP requests and web scraping
- Python Telegram Bot API

## Prerequisites

- Two Telegram bots with API keys
- Python 3.x
- pip

## Installation

1. Clone the repository

   ```sh
   git clone https://github.com/username/WebWatchNotify.git
   ```

2. Navigate into the cloned repository

   ```sh
   cd WebWatchNotify
   ```

3. Install the dependencies

   ```sh
   pip install -r requirements.txt
   ```

4. Configure the app by editing the `config.json` file.
The configuration includes the website link,
the steps to get to location of the file within the website's HTML,
the Telegram Bots API keys, and the target Telegram group or channel ID.

   ```json
   {
     "configs": [
       {
         "name": "Example name",
         "website": "https://example.com",
         "steps": [
           {
             "method": "find_text",
             "params": { "text": "Informatyka I stopnia  " }
           },
           { "method": "parent" },
           { "method": "find_next_sibling" },
           {
             "method": "find_text",
             "params": { "text": "Plan zajęć II semestr " }
           },
           { "method": "parent" },
           { "method": "parent" },
           { "method": "get_attribute", "params": { "name": "href" } }
         ],
         "bot_token": "your_telegram_bot_api_key",
         "read_bot_token": "your_telegram_read_bot_api_key",
         "chat_id": "your_telegram_group_id",
         "schedule_interval": "1"
       }
     ]
   }
   ```

## Usage

Once the app is running, it will start monitoring the file at the location
specified in the `config.json` file within the website's HTML.
When a change is detected, it will send a message with the result of parsing
to the specified Telegram group or channel.

```sh
   python3 WebWatchNotify.py config.json
```

There is check_once mode which will only check the file once
and send a message if there is a change.

```sh
python3 WebWatchNotify.py config.json --check_once
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.
