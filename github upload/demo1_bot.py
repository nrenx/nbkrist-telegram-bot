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
from selenium.webdriver.support.ui import Select
from collections import defaultdict
from datetime import datetime

# Earn Money Feature Constants
WORKING_CREDENTIALS_FILE = "working_credentials.json"
MAX_REQUESTS_PER_USER = 3  # Maximum requests per user in the time window
REQUEST_WINDOW = 30  # Time window in seconds
MAX_CONCURRENT_VERIFICATIONS = 5  # Maximum number of concurrent verifications

# Thread-safe structures for earn money feature
verification_semaphore = threading.Semaphore(MAX_CONCURRENT_VERIFICATIONS)
user_requests = defaultdict(list)  # Track user requests
user_requests_lock = threading.Lock()  # Lock for thread-safe access to user_requests
credentials_lock = threading.Lock()  # Lock for thread-safe access to credentials file
user_states = {}  # Store temporary user states
user_states_lock = threading.Lock()  # Lock for thread-safe access to user states

def load_credentials():
    """Load credentials from the working_credentials.json file."""
    try:
        if os.path.exists(WORKING_CREDENTIALS_FILE):
            with open(WORKING_CREDENTIALS_FILE, 'r') as f:
                return json.load(f)  # Return the list directly
        return []
    except Exception as e:
        logging.error(f"Error loading credentials: {e}")
        return []

def save_credentials(credentials):
    """Save credentials to the working_credentials.json file."""
    try:
        with open(WORKING_CREDENTIALS_FILE, 'w') as f:
            json.dump(credentials, f, indent=4)  # Save the list directly
    except Exception as e:
        logging.error(f"Error saving credentials: {e}")

def check_rate_limit(user_id):
    """Check if user has exceeded rate limit."""
    current_time = time.time()
    with user_requests_lock:
        # Remove old requests
        user_requests[user_id] = [t for t in user_requests[user_id] 
                                if current_time - t < REQUEST_WINDOW]
        
        # Check if user has exceeded limit
        if len(user_requests[user_id]) >= MAX_REQUESTS_PER_USER:
            return False
        
        # Add new request
        user_requests[user_id].append(current_time)
        return True

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
    """Loads configuration from config.json."""
    with open(path) as f:
        config = json.load(f)
        return config

config = load_config()
logging.info(f"Loaded config: {config}") # Added logging
API_KEY = config['api_key']
CHROME_PATH = config['chrome_path']
CHROMEDRIVER_PATH = config['chromedriver_path']
LOGIN_CREDENTIALS = config.get('login_credentials', [])

# Constants for mid-marks URL
MID_MARKS_URL = "http://103.203.175.90:94/mid_marks/classSelectionForMarksDisplay.php"

# Branch codes mapping based on the dropdown values
BRANCH_CODES = {
    "MECH": "7",
    "CSE": "5",
    "ECE": "4",
    "EEE": "2",
    "MTech_PS": "12",
    "CIVIL": "11",
    "MTech_CSE": "17",
    "MTech_ECE": "18",
    "MTech_AMS": "19",
    "IT": "22",
    "AI_DS": "23",
    "CSE_DS": "32",
    "CSE_AIML": "33"
}

# Available sections
SECTIONS = ["-", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]

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
            verify_button = InlineKeyboardButton("✅ Verify Membership", callback_data="verify_membership")
            markup.add(join_button)
            markup.add(verify_button)
            safe_reply_to(message, "You must join our channel (@nbkrist_helpline) to use this bot! After joining, click the Verify button below.", reply_markup=markup)
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
            WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

            try:
                username_field = WebDriverWait(browser, 30).until(EC.visibility_of_element_located((By.ID, 'username')))
                password_field = WebDriverWait(browser, 30).until(EC.visibility_of_element_located((By.ID, 'password')))
                submit_button = WebDriverWait(browser, 30).until(EC.element_to_be_clickable((By.XPATH, "//form[@name='frmAttLogin']//input[@type='submit']")))
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
            for i in range(2):  # Changed from 10 to 2 attempts
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
                WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.LINK_TEXT, "Attendance")))
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
    """Select form details for mid marks."""
    try:
        # Wait for the form elements to be present
        acadYear = WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.NAME, "acadYear")))
        yearSem = WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.NAME, "yearSem")))
        branch_select = WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.NAME, "branch")))
        section_select = WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.NAME, "section")))

        # Select Academic Year (format is already "2024-25")
        Select(acadYear).select_by_value(academic_year)
        
        # Select Year/Semester (format: "31" for 3rd year 1st sem)
        Select(yearSem).select_by_value(year_of_study)
        
        # Select Branch (format: "5" for CSE)
        Select(branch_select).select_by_value(branch)
        
        # Select Section (format: "A", "B", "C")
        Select(section_select).select_by_value(section)

        logging.info(f"Form details selected - Year: {academic_year}, Study: {year_of_study}, Branch: {branch}, Section: {section}")
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
        # Send initial message
        safe_reply_to(message, "Fetching attendance details...\n\nPlease wait it takes 1min to load")
        
        # Navigate to attendance page
        if not navigate_to_attendance_page(browser):
            safe_reply_to(message, "Failed to navigate to attendance page.")
            return

        # Login to the system
        if not login_to_system(browser):
            safe_reply_to(message, "Failed to login.")
            return

        # Convert branch name to code
        branch_code = BRANCH_CODES.get(branch, branch)  # Use the code if branch is a name, otherwise use as is
        
        # Select form details
        if not select_form_details(browser, academic_year, year_of_study, branch_code, section):
            safe_reply_to(message, "Failed to select form details.")
            return
        
        # Click show button
        if not click_show_button(browser):
            safe_reply_to(message, "Failed to click the show button.")
            return
        
        # Wait for page load
        if not wait_for_page_load(browser, rollno):
            safe_reply_to(message, f"Failed to load attendance details for roll number {rollno}.")
            return

        # Extract attendance data
        data = extract_attendance_data(browser, rollno)
        if data is None:
            safe_reply_to(message, f"❌ Roll number {rollno} not found in the attendance records.")
            return

        if data:
            # Create a formatted message with sections and emojis
            attendance_msg = [
                "📊 *ATTENDANCE DETAILS*\n",
                f"🆔 *Roll Number:* {data.get('roll_number', 'N/A')}",
                f"📈 *Overall Attendance:* {data.get('attendance_percentage', 'N/A')}%",
                f"📅 *Total Classes:* {data.get('total_classes', 'N/A')}\n",
                "📚 *Total Presented= Classes&Labs:*"
            ]
            
            # Add subject-wise attendance
            subject_items = []
            for key, value in data.items():
                if key not in ['roll_number', 'attendance_percentage', 'total_classes']:
                    if '(' in key:  # This identifies the labs entry
                        subject_items.append(f"• *{key}:* {value} =labs")
                    else:
                        subject_items.append(f"• *{key}:* {value}")
            
            # Sort items to ensure labs entry is at the end
            attendance_msg.extend(sorted(subject_items, key=lambda x: '=' in x))
            
            attendance_info = "\n".join(attendance_msg)
        else:
            attendance_info = "❌ No attendance data found for this roll number."

        safe_reply_to(message, attendance_info, parse_mode='Markdown')

    except Exception as e:
        logging.exception(f"Error while processing attendance details: {e}")
        safe_reply_to(message, f"Failed to retrieve attendance details. A detailed error has been logged. Please try again later.")

def navigate_to_mid_marks_page(browser):
    """Navigate to the mid marks page."""
    try:
        browser.get(MID_MARKS_URL)
        return True
    except Exception as e:
        logging.exception(f"Error navigating to mid marks page: {e}")
        return False

def get_student_mid_marks(browser, rollno):
    """Extract mid marks for a specific student."""
    try:
        # Wait for the table to be present
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        
        # Get the page source and create BeautifulSoup object
        html_content = browser.page_source
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all tables
        tables = soup.find_all('table')
        if not tables:
            logging.error("No tables found in the page")
            return None
            
        # Get the main marks table (usually the last one)
        marks_table = tables[-1]
        
        # Find the row with the matching roll number
        student_row = marks_table.find('tr', attrs={'name': rollno}) or marks_table.find('tr', attrs={'id': rollno})
        if not student_row:
            logging.error(f"No row found for roll number: {rollno}")
            return None
            
        # Initialize student data
        student_data = {
            'roll_number': rollno,
            'subjects': {},
            'labs': {}
        }
        
        # Get all cells in the row
        cells = student_row.find_all('td')
        
        # Process each cell that has a name attribute (these are subject cells)
        for cell in cells:
            subject_name = cell.get('name', '').strip()
            if not subject_name:
                continue
                
            cell_text = cell.text.strip()
            if not cell_text:
                continue
                
            # Initialize marks dictionary
            marks_dict = {'mid1': '', 'mid2': '', 'total': ''}
            
            # Check if it's a lab subject
            if 'LAB' in subject_name.upper() or 'SKILLS' in subject_name.upper():
                student_data['labs'][subject_name] = cell_text
            else:
                # Extract marks - handle different formats
                if '/' in cell_text:
                    # Format: "34/25(33)" or "34/25"
                    parts = cell_text.split('/')
                    marks_dict['mid1'] = parts[0].strip()
                    
                    second_part = parts[1]
                    if '(' in second_part:
                        mid2, total = second_part.split('(')
                        marks_dict['mid2'] = mid2.strip()
                        marks_dict['total'] = total.rstrip(')').strip()
                    else:
                        marks_dict['mid2'] = second_part.strip()
                else:
                    # Single mark format: "16"
                    marks_dict['mid1'] = cell_text
                    
                student_data['subjects'][subject_name] = marks_dict
        
        # Get lab marks from the unnamed cells (last few cells)
        lab_cells = [cell for cell in cells if not cell.get('name') and cell.text.strip()]
        if len(lab_cells) >= 3:  # Usually last 3 cells contain lab marks
            student_data['labs'].update({
                'DW and M LAB': lab_cells[-3].text.strip(),
                'AI LAB': lab_cells[-2].text.strip(),
                'COMMUNICATION and SOFT SKILLS': lab_cells[-1].text.strip()
            })
        
        if not student_data['subjects'] and not student_data['labs']:
            logging.error("No marks found in the row")
            return None
            
        return student_data
        
    except Exception as e:
        logging.exception(f"Error extracting student mid marks: {e}")
        return None

def format_mid_marks_message(student_data):
    """Format student mid marks data into a readable message."""
    if not student_data:
        return "❌ No marks data found for the given roll number."

    # Start building the message
    message = "📊 *Mid Marks Report*\n\n"
    
    # Add student details
    message += "👤 *Student Details:*\n"
    message += f"Roll Number: `{student_data['roll_number']}`\n\n"
    
    # Add subject marks
    if student_data['subjects']:
        message += "📝 *Subject-wise Marks:*\n```\n"
        # Header
        message += f"{'Subject':<8} {'Mid-1':<8} {'Mid-2':<8} {'Total':<8}\n"
        message += "-" * 32 + "\n"
        
        # Add each subject's marks
        for subject, marks in student_data['subjects'].items():
            mid1 = marks['mid1'] or '-'
            mid2 = marks['mid2'] or '-'
            total = marks['total'] or '-'
            message += f"{subject:<8} {mid1:<8} {mid2:<8} {total:<8}\n"
        message += "```\n"
    
    # Add lab marks
    if student_data['labs']:
        message += "\n🔬 *Lab Internal Marks:*\n```\n"
        for lab, marks in student_data['labs'].items():
            lab_name = lab.ljust(30)  # Adjust lab name width
            message += f"{lab_name}{marks}\n"
        message += "```"
    
    return message

def process_mid_marks(message, academic_year, year_of_study, branch, section, rollno):
    """Process and fetch mid marks for a student."""
    try:
        # Send initial message
        safe_reply_to(message, "Fetching mid marks details...\n\nPlease wait it takes 1min to load")
        
        # Navigate to mid marks page
        with open_browser() as browser:
            if not navigate_to_mid_marks_page(browser):
                safe_reply_to(message, "Failed to access the mid marks page.")
                return
                
            # Login to the system
            if not login_to_system(browser):
                safe_reply_to(message, "Failed to login.")
                return
            
            # Convert branch name to code if needed
            branch_code = BRANCH_CODES.get(branch, branch)  # Use the code if branch is a name, otherwise use as is
            
            # Select form details
            if not select_form_details(browser, academic_year, year_of_study, branch_code, section):
                safe_reply_to(message, "Failed to select form details.")
                return
            
            # Click show button
            if not click_show_button(browser):
                safe_reply_to(message, "Failed to submit the form.")
                return
            
            # Get student marks
            student_data = get_student_mid_marks(browser, rollno)
            if student_data:
                formatted_message = format_mid_marks_message(student_data)
                safe_reply_to(message, formatted_message, parse_mode='Markdown')
            else:
                safe_reply_to(message, f"❌ No marks found for roll number {rollno}.")
    
    except Exception as e:
        logging.exception(f"Error processing mid marks: {e}")
        safe_reply_to(message, "An error occurred while fetching mid marks. Please try again.")

def handle_mid_marks_request(message, academic_year, year_of_study, branch, section, rollno):
    """Handle mid marks request in a separate thread."""
    try:
        with open_browser() as browser:
            process_mid_marks(message, academic_year, year_of_study, branch, section, rollno)
    except Exception as e:
        logging.exception(f"Error in mid marks request: {e}")
        safe_reply_to(message, "An error occurred while fetching mid marks. Please try again later.")

def process_mid_marks_roll_number(message, academic_year, year_of_study, branch, section):
    """Process roll number input for mid marks."""
    try:
        rollno = message.text.strip().upper()
        if not re.match(r'^[A-Z0-9]+$', rollno):
            safe_reply_to(message, "Invalid roll number format. Please enter a valid roll number (uppercase alphanumeric characters only).")
            return
        
        logging.info(f"User entered roll number: {rollno}")
        thread = threading.Thread(target=handle_mid_marks_request, 
                                args=(message, academic_year, year_of_study, branch, section, rollno))
        thread.start()
    except Exception as e:
        logging.exception(f"Error processing roll number: {e}")
        safe_reply_to(message, "An error occurred. Please try again.")

@bot.message_handler(commands=['start'])
@require_channel_membership
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    join_button = InlineKeyboardButton("Join Channel (@nbkrist_helpline)", url="https://t.me/nbkrist_helpline")
    verify_button = InlineKeyboardButton("✅ Verify Membership", callback_data="verify_membership")
    markup.add(join_button)
    markup.add(verify_button)
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
    markup.add(types.KeyboardButton("📊 Check Attendance"))
    markup.add(types.KeyboardButton("📝 Check Mid Marks"))
    markup.add(types.KeyboardButton("💰 EARN MONEY"))
    markup.add(types.KeyboardButton("‼️ REPORT ERROR"))

    bot.send_message(message.chat.id, "Please select an option from below\n\nIf not visible click on four dots to open them:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ["📊 Check Attendance", "📝 Check Mid Marks"])
@require_channel_membership
def handle_main_menu(message):
    if message.text == "📊 Check Attendance":
        academic_year_selection_attendance(message)
    else:
        academic_year_selection_midmarks(message)

def academic_year_selection_attendance(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("2021-22", callback_data="year_2021-22"))
    markup.add(types.InlineKeyboardButton("2022-23", callback_data="year_2022-23"))
    markup.add(types.InlineKeyboardButton("2023-24", callback_data="year_2023-24"))
    markup.add(types.InlineKeyboardButton("2024-25(present-year)", callback_data="year_2024-25"))
    safe_reply_to(message, "Please select the Academic Year:", reply_markup=markup)

def academic_year_selection_midmarks(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("2021-22", callback_data="mid_year_2021-22"))
    markup.add(types.InlineKeyboardButton("2022-23", callback_data="mid_year_2022-23"))
    markup.add(types.InlineKeyboardButton("2023-24", callback_data="mid_year_2023-24"))
    markup.add(types.InlineKeyboardButton("2024-25(present-year)", callback_data="mid_year_2024-25"))
    safe_reply_to(message, "Please select the Academic Year:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
@require_channel_in_callback
def callback_query(call):
    try:
        if call.data == "verify_membership":
            user_id = call.from_user.id
            if is_user_in_channel(user_id):
                bot.delete_message(call.message.chat.id, call.message.message_id)
                new_message = types.Message(
                    message_id=None,
                    from_user=call.from_user,
                    date=None,
                    chat=call.message.chat,
                    content_type='text',
                    options={},
                    json_string=None
                )
                new_message.text = '/start'
                send_welcome(new_message)
            else:
                bot.answer_callback_query(call.id, "Please join the channel first!", show_alert=True)
            return

        # Handle attendance flow
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
            markup.add(types.InlineKeyboardButton("MECH", callback_data=f"branch_{academic_year}_{year_of_study}_7"))
            markup.add(types.InlineKeyboardButton("CSE", callback_data=f"branch_{academic_year}_{year_of_study}_5"))
            markup.add(types.InlineKeyboardButton("ECE", callback_data=f"branch_{academic_year}_{year_of_study}_4"))
            markup.add(types.InlineKeyboardButton("EEE", callback_data=f"branch_{academic_year}_{year_of_study}_2"))
            markup.add(types.InlineKeyboardButton("CIVIL", callback_data=f"branch_{academic_year}_{year_of_study}_11"))
            markup.add(types.InlineKeyboardButton("IT", callback_data=f"branch_{academic_year}_{year_of_study}_22"))
            markup.add(types.InlineKeyboardButton("AI&DS", callback_data=f"branch_{academic_year}_{year_of_study}_23"))
            safe_edit_message_text(call, f"Selected Year of Study\nPlease select the Branch:", reply_markup=markup)

        elif call.data.startswith("branch_"):
            data = call.data.split("_")
            academic_year = data[1]
            year_of_study = data[2]
            branch = data[3]
            markup = types.InlineKeyboardMarkup()
            for section in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
                markup.add(types.InlineKeyboardButton(section, callback_data=f"section_{academic_year}_{year_of_study}_{branch}_{section}"))
            safe_edit_message_text(call, f"Selected Branch\nPlease select the Section:", reply_markup=markup)

        elif call.data.startswith("section_"):
            data = call.data.split("_")
            academic_year = data[1]
            year_of_study = data[2]
            branch = data[3]
            section = data[4]
            safe_edit_message_text(call, f"Selected Section: {section}\nPlease enter your roll number (in uppercase):")
            bot.register_next_step_handler(call.message, process_roll_number, academic_year, year_of_study, branch, section)

        # Handle mid-marks flow
        elif call.data.startswith("mid_year_"):
            academic_year = call.data.split("_")[2]
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("First", callback_data=f"mid_study_{academic_year}_01"))
            markup.add(types.InlineKeyboardButton("First Yr - First Sem", callback_data=f"mid_study_{academic_year}_11"))
            markup.add(types.InlineKeyboardButton("First Yr - Second Sem", callback_data=f"mid_study_{academic_year}_12"))
            markup.add(types.InlineKeyboardButton("Second Yr - First Sem", callback_data=f"mid_study_{academic_year}_21"))
            markup.add(types.InlineKeyboardButton("Second Yr - Second Sem", callback_data=f"mid_study_{academic_year}_22"))
            markup.add(types.InlineKeyboardButton("Third Yr - First Sem", callback_data=f"mid_study_{academic_year}_31"))
            markup.add(types.InlineKeyboardButton("Third Yr - Second Sem", callback_data=f"mid_study_{academic_year}_32"))
            markup.add(types.InlineKeyboardButton("Final Yr - First Sem", callback_data=f"mid_study_{academic_year}_41"))
            markup.add(types.InlineKeyboardButton("Final Yr - Second Sem", callback_data=f"mid_study_{academic_year}_42"))
            safe_edit_message_text(call, f"Selected Academic Year: {academic_year}\nPlease select the Year of Study:", reply_markup=markup)

        elif call.data.startswith("mid_study_"):
            data = call.data.split("_")
            academic_year = data[2]
            year_of_study = data[3]
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("MECH", callback_data=f"mid_branch_{academic_year}_{year_of_study}_7"))
            markup.add(types.InlineKeyboardButton("CSE", callback_data=f"mid_branch_{academic_year}_{year_of_study}_5"))
            markup.add(types.InlineKeyboardButton("ECE", callback_data=f"mid_branch_{academic_year}_{year_of_study}_4"))
            markup.add(types.InlineKeyboardButton("EEE", callback_data=f"mid_branch_{academic_year}_{year_of_study}_2"))
            markup.add(types.InlineKeyboardButton("CIVIL", callback_data=f"mid_branch_{academic_year}_{year_of_study}_11"))
            markup.add(types.InlineKeyboardButton("IT", callback_data=f"mid_branch_{academic_year}_{year_of_study}_22"))
            markup.add(types.InlineKeyboardButton("AI&DS", callback_data=f"mid_branch_{academic_year}_{year_of_study}_23"))
            safe_edit_message_text(call, f"Selected Year of Study\nPlease select the Branch:", reply_markup=markup)

        elif call.data.startswith("mid_branch_"):
            data = call.data.split("_")
            academic_year = data[2]
            year_of_study = data[3]
            branch = data[4]
            markup = types.InlineKeyboardMarkup()
            for section in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
                markup.add(types.InlineKeyboardButton(section, callback_data=f"mid_section_{academic_year}_{year_of_study}_{branch}_{section}"))
            safe_edit_message_text(call, f"Selected Branch\nPlease select the Section:", reply_markup=markup)

        elif call.data.startswith("mid_section_"):
            data = call.data.split("_")
            academic_year = data[2]
            year_of_study = data[3]
            branch = data[4]
            section = data[5]
            safe_edit_message_text(call, f"Selected Section: {section}\nPlease enter your roll number (in uppercase):")
            bot.register_next_step_handler(call.message, process_mid_marks_roll_number, academic_year, year_of_study, branch, section)

        # Handle enter_credentials callback
        elif call.data == "enter_credentials":
            credential_entry(call)

        elif call.data == "restart_bot":
            send_welcome(call.message)

    except Exception as e:
        logging.exception(f"Error handling callback query: {e}")
        safe_reply_to(call.message, f"An error occurred. Please try again.")

def process_roll_number(message, academic_year, year_of_study, branch, section):
    rollno = message.text.strip().upper()
    logging.info(f"User entered roll number: {rollno}")
    user_thread = threading.Thread(target=handle_user_request, args=(message, academic_year, year_of_study, branch, section, rollno))
    user_thread.start()

def handle_user_request(message, academic_year, year_of_study, branch, section, rollno):
    try:
        with open_browser() as browser:
            process_attendance_details(message, academic_year, year_of_study, branch, section, rollno, browser)
    except Exception as e:
        logging.exception(f"Error handling user request: {e}")
        safe_reply_to(message, f"An error occurred while processing your request. Please try again later.  A detailed error has been logged.")

def verify_login(username, password):
    """Verify login credentials using Selenium."""
    logging.info(f"Starting login verification for username: {username}")
    browser = None
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')  # Enable headless mode
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')  # Required for headless
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument('--silent')
        
        # Performance optimizations
        chrome_options.add_argument('--disable-dev-tools')
        chrome_options.add_argument('--no-default-browser-check')
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(executable_path=CHROMEDRIVER_PATH)
        service.log_path = os.devnull  # Disable service logging
        
        browser = webdriver.Chrome(service=service, options=chrome_options)
        browser.set_page_load_timeout(15)  # Reduced timeout
        
        url = "http://103.203.175.90:94/attendance/attendanceLogin.php"
        logging.info(f"Navigating to URL: {url}")
        browser.get(url)
        
        try:
            logging.info("Waiting for login form elements...")
            
            # Reduced wait times and more efficient selectors
            username_field = WebDriverWait(browser, 5).until(
                EC.presence_of_element_located((By.ID, 'username'))
            )
            logging.info("Found username field")
            
            password_field = browser.find_element(By.ID, 'password')
            logging.info("Found password field")
            
            submit_button = browser.find_element(By.XPATH, "//form[@name='frmAttLogin']//input[@type='submit']")
            logging.info("Found submit button")
            
            # Fast input without delays
            username_field.send_keys(username)
            password_field.send_keys(password)
            
            logging.info("Clicking submit button...")
            submit_button.click()
            
            # Quick check for logout link (success indicator)
            try:
                logout_link = WebDriverWait(browser, 3).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'Logout.php')]"))
                )
                if logout_link.is_displayed():
                    logging.info("Found logout link - login successful!")
                    return True
            except:
                # If logout link not found, check for errors
                if "attendanceLogin.php" in browser.current_url:
                    logging.error("Still on login page - login failed")
                    return False
                
                page_source = browser.page_source.lower()
                error_texts = ['invalid', 'incorrect', 'failed', 'error']
                if any(error in page_source for error in error_texts):
                    logging.error("Login error detected in page source")
                    return False
                
                # Final quick check for success elements
                try:
                    success = WebDriverWait(browser, 2).until(
                        EC.any_of(
                            EC.presence_of_element_located((By.XPATH, "//a[@class='clsWhiteA' and contains(@href, 'Logout.php')]")),
                            EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'dashboard')]"))
                        )
                    )
                    logging.info("Found post-login elements")
                    return True
                except:
                    logging.error("Could not find any post-login elements")
                    return False
                
        except Exception as e:
            logging.error(f"Error during login process: {e}")
            return False
            
    except Exception as e:
        logging.error(f"Browser initialization error: {e}")
        return False
        
    finally:
        if browser:
            try:
                browser.quit()
            except:
                pass

def handle_verification(message, username, password, status_message):
    """Handle verification in a separate thread"""
    try:
        with verification_semaphore:
            if verify_login(username, password):
                # Load existing credentials
                credentials = load_credentials()  # Now returns a list
                logging.info(f"Loaded {len(credentials)} existing credentials from file")
                
                # Check if exact username and password combination exists
                exists = False
                for cred in credentials:  # Iterate directly over the list
                    logging.info(f"Checking against saved credential: username={cred.get('username')}")
                    if cred.get("username") == username and cred.get("password") == password:
                        exists = True
                        logging.info(f"Found duplicate: username={username}")
                        break
                
                if not exists:
                    # Add new credentials only if combination doesn't exist
                    new_entry = {
                        "username": username,
                        "password": password,
                        "telegram_username": message.from_user.username,
                        "telegram_name": message.from_user.first_name,
                        "date_added": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    credentials.append(new_entry)  # Append directly to list
                    save_credentials(credentials)  # Pass the list
                    logging.info(f"New unique credentials saved for user {message.from_user.id}")
                    bot.edit_message_text(
                        "✅ Login successful! Credentials saved! You are now participating in the contest! 🎉",
                        chat_id=status_message.chat.id,
                        message_id=status_message.message_id
                    )
                else:
                    logging.info(f"Skipping save - duplicate credentials found for username: {username}")
                    bot.edit_message_text(
                        "✅ Login successful! But these credentials are already saved in our system.",
                        chat_id=status_message.chat.id,
                        message_id=status_message.message_id
                    )
            else:
                bot.edit_message_text(
                    "❌ Invalid credentials. Please try again with correct username and password.",
                    chat_id=status_message.chat.id,
                    message_id=status_message.message_id
                )
    except Exception as e:
        logging.error(f"Error in verification thread: {e}")
        bot.edit_message_text(
            "❌ An error occurred. Please try again.",
            chat_id=status_message.chat.id,
            message_id=status_message.message_id
        )

@bot.message_handler(func=lambda message: message.text == "💰 EARN MONEY")
def earn_money_handler(message):
    # Remove the keyboard immediately
    remove_markup = types.ReplyKeyboardRemove()
    
    info_text = contest_details = """
🎉 Contest Announcement 🎉\n(not started yet,but you try)

🏆 Prize: One lucky winner will receive ₹200!

📑 How to Participate:
1️⃣ Click the Enter Credentials button below.
2️⃣ Provide collage website credentials (username and password).\nNOTE:These details are used for improving bot interaction only.
3️⃣ Your credentials will be verified in real-time:
    • ✅ If correct, you will be successfully registered for the contest.
    • ❌ If incorrect, you will not qualify.

🔔 Important Rules:
    • Credentials must be unique and not previously used for contest entry.
    • Duplicate entries with the same credentials will not be accepted.

📅 Contest Rounds:
    • One round will be conducted every month.

🏆 Winner Selection:
    • The winner will be selected randomly after the contest ends and announced on the same day!

📢 Previous Contest:
    • The first contest was posted in the group, and this is the second contest.
"""

    # Create inline keyboard for credential entry
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("Enter Credentials", callback_data="enter_credentials"))
    
    # Send message with inline keyboard and remove the previous keyboard
    bot.send_message(
        message.chat.id,
        info_text,
        reply_markup=markup,
        parse_mode='HTML'
    )

@bot.callback_query_handler(func=lambda call: call.data == "enter_credentials")
@require_channel_in_callback
def credential_entry(call):
    try:
        # Store user state
        user_states[call.from_user.id] = {"state": "awaiting_username"}
        
        # Remove the inline keyboard
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None
        )
        
        # Ask for username
        bot.send_message(call.message.chat.id, "Please enter your username:")
        bot.answer_callback_query(call.id)
    except Exception as e:
        logging.exception(f"Error in credential entry: {e}")
        safe_reply_to(call.message, "An error occurred. Please try again.")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id].get("state") in ["awaiting_username", "awaiting_password"])
def handle_credentials(message):
    user_id = message.from_user.id
    state = user_states[user_id]["state"]
    
    if state == "awaiting_username":
        user_states[user_id]["username"] = message.text
        user_states[user_id]["state"] = "awaiting_password"
        bot.reply_to(message, "Please enter your password:")
        
    elif state == "awaiting_password":
        # Check rate limit
        if not check_rate_limit(user_id):
            bot.reply_to(message, "⚠️ Too many attempts. Please wait a minute before trying again.")
            del user_states[user_id]
            return
            
        username = user_states[user_id]["username"]
        password = message.text
        
        status_message = bot.reply_to(message, "🔄 Verifying your credentials... Please wait.")
        
        # Start verification in a separate thread
        thread = threading.Thread(
            target=handle_verification,
            args=(message, username, password, status_message)
        )
        thread.start()

@bot.message_handler(func=lambda message: message.text == "‼️ REPORT ERROR")
def report_error_handler(message):
    """
    Handler for the Report Error button
    Provides contact information for the CSE department
    """
    contact_message = """
    Click on below restart bot button for restarting bot 
    
if still not solved contact @inevitable_2035\nfor solving your problem

THANK YOU FOR USING THIS BOT
    """

    # Create an inline keyboard with a "Restart Bot" button
    markup = types.InlineKeyboardMarkup()
    restart_button = types.InlineKeyboardButton("🔄 Restart Bot", callback_data="restart_bot")
    markup.add(restart_button)
    
    bot.send_message(
        message.chat.id, 
        contact_message, 
        reply_markup=markup,
        parse_mode='HTML'
    )

def run_bot():
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.exception(f"Bot polling failed: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_bot()
