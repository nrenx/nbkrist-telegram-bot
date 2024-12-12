# NBKRIST Telegram Attendance Bot

This project is a **Telegram bot** that fetches and displays attendance and midterm marks for students based on their academic year, year of study, branch, and roll number. It integrates **Selenium** for web scraping and the **PyTelegramBotAPI** library for Telegram interactions.

---

## ✨ Features

- ✅ **Attendance Retrieval**: Automatically fetches student attendance from the college website.
- ✅ **Marks Display**: Dynamically retrieves and displays midterm marks using roll numbers.
- ✅ **Interactive Experience**: Telegram inline buttons and prompts for user-friendly interaction.
- ✅ **Web Automation**: Selenium-powered efficient data extraction.
- ✅ **Secure Data Handling**: Stores user data securely in JSON files.
- ✅ **Scalable Design**: Multi-threading ensures smooth performance for multiple users.
- ✅ **AI Integration**: Enhanced automation and error handling through AI tools.

---

## 🤖 AI Tools and Contributions

This bot was developed with extensive AI support:

### **💡 Idea Generation**
- **ChatGPT**: Assisted in structuring the project and resolving challenges.

### **⚙️ Code Development**
- **Windsurf AI Bot**: Helped write and debug Python scripts.
- **Clinc AI Bot**: Designed user interaction workflows.
- **Auto Copilot Bot**: Enhanced automation with APIs from:
  - 🔑 **GitHub**
  - 🔑 **Google Gemini**
  - 🔑 **Vertex AI**

### **🌐 Platforms and Optimization**
- **Google Gemini AI** and **Vertex AI**: Enabled advanced automation and machine learning workflows.
- **LLMs**: Created efficient and scalable scripts.

---

## 💻 Technologies Used

- **Python Libraries**:
  - `telebot`: Telegram bot functionalities.
  - `selenium`: Web automation.
  - `BeautifulSoup`: HTML parsing.
  - `logging`: Monitoring and debugging.
- **Hosting Platforms**:
  - Google Cloud VM and PythonAnywhere.
- **Data Storage**:
  - JSON for persistent and secure user data storage.

---

## 🛠️ Usage

1. Interact with the bot on Telegram:
   - Provide academic year, class, and roll number details.
   - Retrieve attendance or midterm marks.
2. Automated Selenium scripts handle data retrieval and display it directly in the Telegram chat.

---

## 🔮 Future Enhancements

- 🔔 Add notifications for updates on attendance or marks.
- 📅 Integrate additional educational data (e.g., schedules, results).
- 🤖 Improve AI-driven predictive insights and user interaction.

---

## Dependencies

- **Telebot**: For interacting with Telegram's API.
- **Selenium**: For web scraping and automating the browser.
- **BeautifulSoup**: For parsing HTML content.
- **Logging**: For error tracking and monitoring bot activities.
- **Threading**: For handling concurrent user requests.

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

----

## Folder Structure

```plaintext
attendance-bot/
├── demo1_bot.py        # Main bot script
├── config.json         # Configuration file (not included in repo)
├── requirements.txt    # Python dependencies
├── bot.log             # Log file for debugging (generated at runtime)

```

---

## 🔧 Logging and Debugging

- Logs are stored in `bot.log`.
- Automatic log rotation ensures file size doesn’t exceed 5 MB.
- Use logs to debug issues like login failures or scraping errors.

---

## 🤝 Contribution Guidelines

1. Fork the repository.
2. Create a new feature branch.
3. Submit a pull request with a detailed description of your changes.

---

## 📜 License

To be updated soon.

---

## 💬 Support

If you encounter any issues or need help, open an issue on the repository.
