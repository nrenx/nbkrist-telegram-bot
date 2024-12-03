from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot import types
from user_data_manager import update_user_data, get_user_data
import telebot
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
from logging.handlers import RotatingFileHandler
import re
import threading
from contextlib import contextmanager
import os
import json
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s - %(funcName)s - %(threadName)s',
    handlers=[
        RotatingFileHandler("bot.log", maxBytes=5000000, backupCount=5),  # Max 5 MB per file, keep 5 backups
        logging.StreamHandler()         # Print logs to console
    ]
)

def load_config(path='config.json'):
    """Loads configuration from config.json, handling errors gracefully."""
    try:
        with open(path) as f:
            config = json.load(f)
            return config
    except FileNotFoundError:
        logging.error(f"Error: config.json not found. Using default values.")
        return {
            "api_key": "YOUR_API_KEY",
            "chrome_path": "/usr/bin/google-chrome",
            "chromedriver_path": "/usr/local/bin/chromedriver",
            "login_credentials": []
        }
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding config.json: {e}. Using default values.")
        return {
            "api_key": "YOUR_API_KEY",
            "chrome_path": "/usr/bin/google-chrome",
            "chromedriver_path": "/usr/local/bin/chromedriver",
            "login_credentials": []
        }
    except KeyError as e:
        logging.error(f"Missing key in config.json: {e}. Using default values.")
        return {
            "api_key": "YOUR_API_KEY",
            "chrome_path": "/usr/bin/google-chrome",
            "chromedriver_path": "/usr/local/bin/chromedriver",
            "login_credentials": []
        }

config = load_config()
logging.info(f"Loaded config: {config}") # Added logging
API_KEY = config['api_key']
CHROME_PATH = config['chrome_path']
CHROMEDRIVER_PATH = config['chromedriver_path']
LOGIN_CREDENTIALS = config.get('login_credentials', [])


bot = telebot.TeleBot(API_KEY)

bot_lock = threading.Lock()

def safe_reply_to(message, text, **kwargs):
    with bot_lock:
        try:
            bot.reply_to(message, text, **kwargs)
            logging.info(f"Sent message: {text}")
        except Exception as e:
            logging.exception(f"Error sending message: {e}")

def safe_edit_message_text(call, text, **kwargs):
    with bot_lock:
        try:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, **kwargs)
            logging.info(f"Edited message: {text}")
        except Exception as e:
            logging.exception(f"Error editing message: {e}")

def is_user_in_channel(user_id):
    try:
        member = bot.get_chat_member(chat_id="@nbkrist_helpline", user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logging.exception(f"Error checking channel membership: {e}")
        return False

def require_channel_membership(func):
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        if not is_user_in_channel(user_id):
            markup = InlineKeyboardMarkup()
            join_button = InlineKeyboardButton("Join Channel", url="https://t.me/nbkrist_helpline")
            markup.add(join_button)
            safe_reply_to(message, "You must join our channel (@nbkrist_helpline) to use this bot!,After joining channel enter /start command aging to continu", reply_markup=markup)
            return
        return func(message, *args, **kwargs)
    return wrapper

def require_channel_in_callback(func):
    def wrapper(call, *args, **kwargs):
        user_id = call.from_user.id
        if not is_user_in_channel(user_id):
            markup = InlineKeyboardMarkup()
            join_button = InlineKeyboardButton("Join Channel", url="https://t.me/nbkrist_helpline")
            markup.add(join_button)
            safe_reply_to(call.message, "You must join our channel (@nbkrist_helpline) to use this bot!,After joining channel enter /start command aging to continu", reply_markup=markup)
            return
        return func(call, *args, **kwargs)
    return wrapper

@contextmanager
def open_browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    if not os.path.isfile(CHROME_PATH):
        raise FileNotFoundError(f"Chrome binary not found at {CHROME_PATH}")
    if not os.path.isfile(CHROMEDRIVER_PATH):
        raise FileNotFoundError(f"ChromeDriver not found at {CHROMEDRIVER_PATH}")

    chrome_options.binary_location = CHROME_PATH

    service = Service(CHROMEDRIVER_PATH)

    browser = webdriver.Chrome(service=service, options=chrome_options)
    try:
        yield browser
    except Exception as e:
        logging.exception(f"Error using browser: {e}")
    finally:
        browser.quit()

def handle_user_request(message, academic_year, year_of_study, branch, section, rollno):
    try:
        with open_browser() as browser:
            process_attendance_details(message, academic_year, year_of_study, branch, section, rollno, browser)
    except Exception as e:
        logging.exception(f"Error handling user request: {e}")
        safe_reply_to(message, f"An error occurred while processing your request. Please try again later.  A detailed error has been logged.")

def navigate_to_attendance_page(browser):
    try:
        browser.get("http://103.203.175.90:94/attendance/attendanceTillADate.php")
        logging.info("Navigated to attendance page.")
        return True
    except Exception as e:
        logging.exception(f"Error navigating to attendance page: {e}")
        return False

def login_to_system(browser):
    for cred in LOGIN_CREDENTIALS:
        try:
            # Explicit wait for page load, increased timeout
            WebDriverWait(browser, 120).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

            try:
                username_field = WebDriverWait(browser, 120).until(EC.visibility_of_element_located((By.ID, 'username')))
                password_field = WebDriverWait(browser, 120).until(EC.visibility_of_element_located((By.ID, 'password')))
                submit_button = WebDriverWait(browser, 120).until(EC.element_to_be_clickable((By.XPATH, "//form[@name='frmAttLogin']//input[@type='submit']")))
            except TimeoutException as e:
                logging.error(f"Timeout waiting for login form elements: {e}")
                return False
            except NoSuchElementException as e:
                logging.error(f"Login form elements not found: {e}")
                return False


            username_field.send_keys(cred['username'])
            password_field.send_keys(cred['password'])
            try:
                submit_button.click()
            except ElementClickInterceptedException:
                logging.error("Submit button click intercepted.  Likely another element is covering it.")
                return False

            logging.info("Login submitted.")
            #Added loop to check for continue button
            for i in range(10):
                try:
                    # Attempt to click using link text first
                    continue_button = WebDriverWait(browser, 5).until(EC.element_to_be_clickable((By.LINK_TEXT, "Continue to Login / Requested Page")))
                    continue_button.click()
                    logging.info("Clicked 'Continue to Login' button (link text).")
                    break  # Exit loop if button is clicked
                except (TimeoutException, NoSuchElementException) as e:
                    logging.info(f"Continue to Login button not found (link text) - attempt {i+1}: {e}")
                    time.sleep(2) # Wait before retrying

            try:
                # Fallback to ID if link text fails after multiple attempts
                continue_button = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.ID, "nextPageAnchor")))
                continue_button.click()
                logging.info("Clicked 'Continue to Login' button (ID).")
            except (TimeoutException, NoSuchElementException) as e:
                logging.info(f"Continue to Login button not found (ID): {e}")
            except Exception as e:
                logging.exception(f"Unexpected error while clicking Continue to Login button: {e}")

            try:
                WebDriverWait(browser, 120).until(EC.presence_of_element_located((By.LINK_TEXT, "Attendance")))
                logging.info("Login successful.")
                return True
            except TimeoutException as e:
                logging.error(f"Timeout waiting for Attendance link: {e}")
                return False
            except NoSuchElementException as e:
                logging.error(f"Attendance link not found: {e}")
                return False
            except Exception as e:
                logging.exception(f"Unexpected error after login: {e}")
                return False

        except Exception as e:
            logging.exception(f"Error logging in with credentials {cred}: {e}")
            continue  # Try the next set of credentials
    return False #Login failed with all credentials


def select_form_details(browser, academic_year, year_of_study, branch, section):
    try:
        acadYear = WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.NAME, "acadYear")))
        yearSem = WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.NAME, "yearSem")))
        branch_select = WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.ID, "branch")))
        section_select = WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.NAME, "section")))

        for option in acadYear.find_elements(By.TAG_NAME, "option"):
            if option.get_attribute("value") == academic_year:
                option.click()
                break
        for option in yearSem.find_elements(By.TAG_NAME, "option"):
            if option.get_attribute("value") == year_of_study:
                option.click()
                break
        for option in branch_select.find_elements(By.TAG_NAME, "option"):
            if option.text == branch:
                option.click()
                break
        for option in section_select.find_elements(By.TAG_NAME, "option"):
            if option.get_attribute("value") == section.upper():
                option.click()
                break

        logging.info("Form details selected.")
        return True
    except Exception as e:
        logging.exception(f"Error selecting form details: {e}")
        return False

def click_show_button(browser):
    try:
        show_button = WebDriverWait(browser, 30).until(EC.element_to_be_clickable((By.XPATH, "//input[@type='button'][@value='Show']")))
        show_button.click()
        logging.info("Show button clicked.")
        return True
    except Exception as e:
        logging.exception(f"Error clicking show button: {e}")
        return False

def wait_for_page_load(browser, rollno):
    try:
        WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.ID, rollno)))
        logging.info("Attendance details page loaded.")
        return True
    except Exception as e:
        logging.exception(f"Error waiting for page load: {e}")
        return False

def extract_attendance_data(browser, rollno):
    try:
        html_content = browser.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        tr_tag = soup.find('tr', {'id': rollno})
        if not tr_tag:
            return None

        data = {}
        try:
            td_roll_no = tr_tag.find('td', {'class': 'tdRollNo'})
            data['roll_number'] = td_roll_no.text.strip().replace(' ', '')
        except AttributeError:
            data['roll_number'] = "N/A"
            logging.error("Error: tdRollNo not found.")

        try:
            td_percent = tr_tag.find('td', {'class': 'tdPercent'})
            data['attendance_percentage'] = td_percent.contents[0].strip()
            font_tag = td_percent.find('font')
            if font_tag:
                data['total_classes'] = font_tag.text.strip()
            else:
                data['total_classes'] = "N/A"
        except AttributeError:
            data['attendance_percentage'] = "N/A"
            data['total_classes'] = "N/A"
            logging.error("Error: tdPercent not found.")

        subject_data = {td['title']: td.text.strip() for td in tr_tag.find_all('td') if 'title' in td.attrs}
        data.update(subject_data)
        return data
    except Exception as e:
        logging.exception(f"Error extracting attendance data: {e}")
        return None

def process_attendance_details(message, academic_year, year_of_study, branch, section, rollno, browser):
    try:
        if not re.match(r'^[A-Z0-9]+$', rollno):
            safe_reply_to(message, "Invalid roll number format. Please enter a valid roll number (uppercase alphanumeric characters only).")
            return

        logging.info(f"Processing attendance for roll number: {rollno}, Branch: {branch}, Section: {section}")
        safe_reply_to(message, "Fetching attendance details...")

        if not navigate_to_attendance_page(browser):
            safe_reply_to(message, "Failed to navigate to the attendance page.")
            return
        if not login_to_system(browser):
            safe_reply_to(message, "Failed to log in with any provided credentials.")
            return
        if not select_form_details(browser, academic_year, year_of_study, branch, section):
            safe_reply_to(message, "Failed to select form details.")
            return
        if not click_show_button(browser):
            safe_reply_to(message, "Failed to click the show button.")
            return
        if not wait_for_page_load(browser, rollno):
            safe_reply_to(message, f"Failed to load attendance details for roll number {rollno}.")
            return

        data = extract_attendance_data(browser, rollno)
        if data is None:
            safe_reply_to(message, f"Roll number {rollno} not found in the attendance records.")
            return

        attendance_info = ""
        if data:
            attendance_info = "\n".join([f"{key}: {value}" for key, value in data.items()])
        else:
            attendance_info = "No attendance data found for this roll number."

        safe_reply_to(message, f"Attendance details:\n\n{attendance_info}")

    except Exception as e:
        logging.exception(f"Error while processing attendance details: {e}")
        safe_reply_to(message, f"Failed to retrieve attendance details. A detailed error has been logged. Please try again later.")


@bot.message_handler(commands=['start'])
@require_channel_membership
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    join_button = InlineKeyboardButton("Join Channel (@nbkrist_helpline)", url="https://t.me/nbkrist_helpline")
    markup.add(join_button)
    bot.send_message(
        message.chat.id,
        "Welcome! To use this bot, please join our channel first:\n\nClick the button below to join:",
        reply_markup=markup
    )

    user_id = message.from_user.id

    if not is_user_in_channel(user_id):
        return

    user_name = message.from_user.username or "Unknown"
    first_name = message.from_user.first_name or "Unknown"
    last_name = message.from_user.last_name or "Unknown"

    update_user_data(str(user_id), "username", user_name)
    update_user_data(str(user_id), "first_name", first_name)
    update_user_data(str(user_id), "last_name", last_name)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("1. Academic Year"))
    bot.send_message(message.chat.id, "Please select an option(From below four dots):\n\n1. Academic Year (for attendace)", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "1. Academic Year")
@require_channel_membership
def academic_year_selection(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("2021-22", callback_data="year_2021-22"))
    markup.add(types.InlineKeyboardButton("2022-23", callback_data="year_2022-23"))
    markup.add(types.InlineKeyboardButton("2023-24", callback_data="year_2023-24"))
    markup.add(types.InlineKeyboardButton("2024-25(present-year)", callback_data="year_2024-25"))
    safe_reply_to(message, "Please select the Academic Year:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
@require_channel_in_callback
def callback_query(call):
    try:
        if call.data.startswith("year_"):
            academic_year = call.data.split("_")[1]
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("First", callback_data=f"study_{academic_year}_01"))
            markup.add(types.InlineKeyboardButton("First Yr - First Sem", callback_data=f"study_{academic_year}_11"))
            markup.add(types.InlineKeyboardButton("First Yr - Second Sem", callback_data=f"study_{academic_year}_12"))
            markup.add(types.InlineKeyboardButton("Second Yr - First Sem", callback_data=f"study_{academic_year}_21"))
            markup.add(types.InlineKeyboardButton("Second Yr - Second Sem", callback_data=f"study_{academic_year}_22"))
            markup.add(types.InlineKeyboardButton("Third Yr - First Sem", callback_data=f"study_{academic_year}_31"))
            markup.add(types.InlineKeyboardButton("Third Yr - Second Sem", callback_data=f"study_{academic_year}_32"))
            markup.add(types.InlineKeyboardButton("Final Yr - First Sem", callback_data=f"study_{academic_year}_41"))
            markup.add(types.InlineKeyboardButton("Final Yr - Second Sem", callback_data=f"study_{academic_year}_42"))
            safe_edit_message_text(call, f"Selected Academic Year: {academic_year}\nPlease select the Year of Study:", reply_markup=markup)
        elif call.data.startswith("study_"):
            data = call.data.split("_")
            academic_year = data[1]
            year_of_study = data[2]
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("MECH", callback_data=f"branch_{academic_year}_{year_of_study}_MECH"))
            markup.add(types.InlineKeyboardButton("CSE", callback_data=f"branch_{academic_year}_{year_of_study}_CSE"))
            markup.add(types.InlineKeyboardButton("ECE", callback_data=f"branch_{academic_year}_{year_of_study}_ECE"))
            markup.add(types.InlineKeyboardButton("EEE", callback_data=f"branch_{academic_year}_{year_of_study}_EEE"))
            markup.add(types.InlineKeyboardButton("MTech_PS", callback_data=f"branch_{academic_year}_{year_of_study}_MTech_PS"))
            markup.add(types.InlineKeyboardButton("CIVIL", callback_data=f"branch_{academic_year}_{year_of_study}_CIVIL"))
            markup.add(types.InlineKeyboardButton("MTech_CSE", callback_data=f"branch_{academic_year}_{year_of_study}_MTech_CSE"))
            markup.add(types.InlineKeyboardButton("MTech_ECE", callback_data=f"branch_{academic_year}_{year_of_study}_MTech_ECE"))
            markup.add(types.InlineKeyboardButton("MTech_AMS", callback_data=f"branch_{academic_year}_{year_of_study}_MTech_AMS"))
            markup.add(types.InlineKeyboardButton("IT", callback_data=f"branch_{academic_year}_{year_of_study}_IT"))
            markup.add(types.InlineKeyboardButton("AI_DS", callback_data=f"branch_{academic_year}_{year_of_study}_AI_DS"))
            markup.add(types.InlineKeyboardButton("CSE_DS", callback_data=f"branch_{academic_year}_{year_of_study}_CSE_DS"))
            markup.add(types.InlineKeyboardButton("CSE_AIML", callback_data=f"branch_{academic_year}_{year_of_study}_CSE_AIML"))
            markup.add(types.InlineKeyboardButton("NCC Army", callback_data=f"branch_{academic_year}_{year_of_study}_NCC Army"))
            markup.add(types.InlineKeyboardButton("NCC Naval", callback_data=f"branch_{academic_year}_{year_of_study}_NCC Naval"))
            safe_edit_message_text(call, f"Selected Year of Study: {year_of_study}\nPlease select the Branch:", reply_markup=markup)
        elif call.data.startswith("branch_"):
            data = call.data.split("_")
            academic_year = data[1]
            year_of_study = data[2]
            branch = data[3]
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("A", callback_data=f"section_{academic_year}_{year_of_study}_{branch}_a"))
            markup.add(types.InlineKeyboardButton("B", callback_data=f"section_{academic_year}_{year_of_study}_{branch}_b"))
            markup.add(types.InlineKeyboardButton("C", callback_data=f"section_{academic_year}_{year_of_study}_{branch}_c"))
            markup.add(types.InlineKeyboardButton("D", callback_data=f"section_{academic_year}_{year_of_study}_{branch}_d"))
            markup.add(types.InlineKeyboardButton("E", callback_data=f"section_{academic_year}_{year_of_study}_{branch}_e"))
            markup.add(types.InlineKeyboardButton("F", callback_data=f"section_{academic_year}_{year_of_study}_{branch}_f"))
            markup.add(types.InlineKeyboardButton("G", callback_data=f"section_{academic_year}_{year_of_study}_{branch}_g"))
            markup.add(types.InlineKeyboardButton("H", callback_data=f"section_{academic_year}_{year_of_study}_{branch}_h"))
            markup.add(types.InlineKeyboardButton("I", callback_data=f"section_{academic_year}_{year_of_study}_{branch}_i"))
            markup.add(types.InlineKeyboardButton("J", callback_data=f"section_{academic_year}_{year_of_study}_{branch}_j"))
            safe_edit_message_text(call, f"Selected Branch: {branch}\nPlease select the Section:", reply_markup=markup)
        elif call.data.startswith("section_"):
            data = call.data.split("_")
            academic_year = data[1]
            year_of_study = data[2]
            branch = data[3]
            section = data[4]
            safe_edit_message_text(
                call,
                f"Selected Section: {section}\nPlease enter your roll number (in uppercase):"
            )
            bot.register_next_step_handler(call.message, process_roll_number, academic_year, year_of_study, branch, section)
    except Exception as e:
        logging.exception(f"Error handling callback query: {e}")
        safe_reply_to(call.message, f"An error occurred. Please try again later.")

def process_roll_number(message, academic_year, year_of_study, branch, section):
    rollno = message.text.strip().upper()
    logging.info(f"User entered roll number: {rollno}")
    user_thread = threading.Thread(target=handle_user_request, args=(message, academic_year, year_of_study, branch, section, rollno))
    user_thread.start()

import json

def show_config(message):
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            config_str = json.dumps(config, indent=4)
            safe_reply_to(message, f"Current config:\n```json\n{config_str}\n```\nReply with '1' to change details or '2' to confirm.")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        safe_reply_to(message, f"Error accessing config: {e}")

@bot.message_handler(commands=['settings'])
@require_channel_membership
def handle_settings(message):
    show_config(message)

@bot.message_handler(func=lambda message: message.text == '1')
@require_channel_membership
def handle_change_details(message):
    safe_reply_to(message, "Reply with:\n11. Change API Key\n22. Change Chrome Path\n3. Change ChromeDriver Path\n4. Change Login Credentials\n0. Go Back")

@bot.message_handler(func=lambda message: message.text == '2')
@require_channel_membership
def handle_details_ok(message):
    safe_reply_to(message, "No changes were made. You can continue to use the bot for other features.")

user_settings_state = {}

@bot.message_handler(func=lambda message: message.text in ['11', '22', '3', '4', '0'])
@require_channel_membership
def handle_setting_selection(message):
    chat_id = message.chat.id
    if chat_id not in user_settings_state:
        user_settings_state[chat_id] = {}
    user_settings_state[chat_id]['step'] = 'setting_selection'
    choice = message.text
    if choice == '11':
        user_settings_state[chat_id]['setting'] = 'api_key'
        safe_reply_to(message, "Send the new API key (enter 0 to leave blank):")
        bot.register_next_step_handler(message, handle_api_key_update)
    elif choice == '22':
        user_settings_state[chat_id]['setting'] = 'chrome_path'
        safe_reply_to(message, "Send the new Chrome path (enter 0 to leave blank):")
        bot.register_next_step_handler(message, handle_chrome_path_update)
    elif choice == '3':
        user_settings_state[chat_id]['setting'] = 'chromedriver_path'
        safe_reply_to(message, "Send the new ChromeDriver path (enter 0 to leave blank):")
        bot.register_next_step_handler(message, handle_chromedriver_path_update)
    elif choice == '4':
        user_settings_state[chat_id]['setting'] = 'login_credentials'
        handle_login_credentials_change(message)
    elif choice == '0':
        del user_settings_state[chat_id]
        safe_reply_to(message, "Going back to main menu.")
    else:
        safe_reply_to(message, "Invalid choice. Please select a number from the menu.")


def handle_api_key_update(message):
    new_api_key = message.text.strip()
    update_config("api_key", new_api_key)
    safe_reply_to(message, "API key updated successfully.")
    del user_settings_state[message.chat.id]

def handle_chrome_path_update(message):
    new_chrome_path = message.text.strip()
    update_config("chrome_path", new_chrome_path)
    safe_reply_to(message, "Chrome path updated successfully.")
    del user_settings_state[message.chat.id]

def handle_chromedriver_path_update(message):
    new_chromedriver_path = message.text.strip()
    update_config("chromedriver_path", new_chromedriver_path)
    safe_reply_to(message, "ChromeDriver path updated successfully.")
    del user_settings_state[message.chat.id]

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_cred_"))
@require_channel_in_callback
def handle_edit_credential(call):
    cred_index = int(call.data.split("_")[2])
    safe_edit_message_text(call, f"Send the new username and password for credential {cred_index + 1} (comma-separated, or 0 to leave blank):")
    bot.register_next_step_handler(call.message, handle_cred_update, cred_index)

def handle_cred_update(message, cred_index):
    try:
        new_cred = message.text.strip()
        if new_cred != "0":
            username, password = new_cred.split(",")
            update_config_cred(cred_index, username.strip(), password.strip())
            safe_reply_to(message, f"Credential {cred_index + 1} updated successfully!")
        else:
            safe_reply_to(message, f"Credential {cred_index+1} unchanged")
    except ValueError:
        safe_reply_to(message, "Invalid input. Please provide in 'username,password' format.")

def update_config_cred(cred_index, username, password):
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        if username == "" and password == "":
            if cred_index < len(config['login_credentials']):
                del config['login_credentials'][cred_index]
        else:
            config['login_credentials'][cred_index]['username'] = username
            config['login_credentials'][cred_index]['password'] = password
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)
        show_config(bot.get_updates()[-1].message) # Show updated config
    except (FileNotFoundError, json.JSONDecodeError, IndexError) as e:
        safe_reply_to(bot.get_updates()[-1].message, f"Error updating config: {e}")


def handle_login_credentials_change(message):
    credentials = config.get("login_credentials", [])
    reply_text = "Reply with:\n"
    for i, cred in enumerate(credentials):
        reply_text += f"{chr(ord('a') + i)}. Edit Credential {i + 1}\n"
    reply_text += "d. Add New Credential\n0. Go Back"
    safe_reply_to(message, reply_text)
    bot.register_next_step_handler(message, handle_cred_selection)

def handle_cred_selection(message):
    chat_id = message.chat.id
    if chat_id not in user_settings_state:
        user_settings_state[chat_id] = {}
    user_settings_state[chat_id]['step'] = 'cred_selection'
    choice = message.text.lower()
    credentials = config.get("login_credentials", [])
    if '0' <= choice <= 'z' and choice.isalpha() and ord(choice) - ord('a') < len(credentials):
        cred_index = ord(choice) - ord('a')


def run_bot():
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.exception(f"Bot polling failed: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_bot()
