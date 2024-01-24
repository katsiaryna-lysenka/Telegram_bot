# Telegram Bot for Site Parsing

This Telegram bot is designed to parse product information from a specified website and save the results to a CSV file.

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>

## Install dependencies:

pip install -r requirements.txt

## Create a virtual environment (optional but recommended):

python -m venv .venv
source .venv/bin/activate  # On Windows, use .venv\Scripts\activate.bat

## Set up the necessary environment variables. Create a .env file in the root directory with the following content:

TOKEN=your_telegram_bot_token
DATABASE_URL=sqlite+aiosqlite:///site_parser.db

## Run the script:

python main.py

## Usage
Start the bot by sending the /start command.
Enter your name when prompted.
Provide the link to the category of products you want to parse.
Wait for the bot to complete the parsing process. It will save the results in a file named products.csv.
