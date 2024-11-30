# NBKRIST Telegram Attendance Bot

This project is a **Telegram bot** designed to fetch and display attendance information for students based on their academic year, year of study, branch, and roll number. It uses **Selenium** for web scraping and the **PyTelegramBotAPI** library for interacting with Telegram.

---

## Features

- **Channel Membership Enforcement**: Users must join a specific Telegram channel to use the bot.
- **Step-by-Step User Input**: Guides users through selecting academic year, year of study, branch, section, and roll number.
- **Attendance Retrieval**: Automatically logs into the attendance system, navigates pages, and fetches attendance details.
- **Error Handling**: Logs errors to a file and gracefully handles exceptions to improve user experience.
- **Multi-Threading**: Handles user requests in parallel without blocking.

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/attendance-bot.git
cd attendance-bot
```

### 2. Install Dependencies

Install the required Python libraries using:

```bash
pip install -r requirements.txt
```

### 3. Configure `config.json`

Create a `config.json` file in the root directory with the following structure:

```json
{
    "api_key": "YOUR_TELEGRAM_BOT_API_KEY",
    "chrome_path": "/path/to/google-chrome",
    "chromedriver_path": "/path/to/chromedriver",
    "login_credentials": [
        {
            "username": "YOUR_USERNAME",
            "password": "YOUR_PASSWORD"
        }
    ]
}
```

- Replace `YOUR_TELEGRAM_BOT_API_KEY` with your Telegram Bot API key.
- Update the paths to Chrome and ChromeDriver.
- Add login credentials for the attendance system.

### 4. Install Chrome and ChromeDriver

Ensure that **Google Chrome** and **ChromeDriver** are installed on your system:

- [Google Chrome Download](https://www.google.com/chrome/)
- [ChromeDriver Download](https://chromedriver.chromium.org/)

### 5. Run the Bot

Start the bot by executing:

```bash
python demo1_bot.py
```

---

## Usage

1. Start the bot by sending the `/start` command on Telegram.
2. Join the required channel as prompted.
3. Follow the bot’s instructions to input your academic details and roll number.
4. Retrieve your attendance details.

---

## Dependencies

- **Telebot**: For interacting with Telegram's API.
- **Selenium**: For web scraping and automating the browser.
- **BeautifulSoup**: For parsing HTML content.
- **Logging**: For error tracking and monitoring bot activities.
- **Threading**: For handling concurrent user requests.

---

## Folder Structure

```plaintext
attendance-bot/
├── demo1_bot.py        # Main bot script
├── config.json         # Configuration file (not included in repo)
├── requirements.txt    # Python dependencies
├── bot.log             # Log file for debugging (generated at runtime)
```

---

## Logging and Debugging

- All logs are stored in `bot.log`.
- Logs are rotated automatically when they exceed 5 MB.
- Use logs to debug errors such as login failures or web scraping issues.

---

## Contribution Guidelines

1. Fork the repository.
2. Create a new feature branch.
3. Submit a pull request with a detailed description.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Support

If you encounter any issues or need assistance, feel free to open an issue on the repository.
