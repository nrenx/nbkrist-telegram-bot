import json
from telebot import TeleBot
import time
import os  # Import os for file path validation
import re  # For improved URL validation
import logging

# Replace 'YOUR_API_KEY' with your bot's API key
API_KEY = '7874697193:AAHkMBjc-tdNx5KBhtMnJ-ZheI5EzIdp2a8'
bot = TeleBot(API_KEY)

# Define the JSON file name
DATA_FILE = "nbkrist_attendance_user_data.json"

# Set up logging to log to a file
logging.basicConfig(filename='send_message.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def log_message(message):
    """Log the message to the log file."""
    logging.info(message)

def load_user_data():
    """Load user data from the JSON file."""
    try:
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print("User data file not found.")
        return {}
    except json.JSONDecodeError:
        print("Error decoding JSON file.")
        return {}

def send_text_to_all_users(message, retries=3):
    """Send a text message to all users listed in the JSON file, with retries."""
    users = load_user_data()
    if not users:
        print("No users found in the data file.")
        return

    for user_id, user_info in users.items():
        attempt = 0
        while attempt < retries:
            try:
                bot.send_message(user_id, message)
                log_message(f"Message sent to user {user_id} ({user_info.get('username', 'Unknown')}): {message}")
                print(f"Message sent to user {user_id} ({user_info.get('username', 'Unknown')}): {message}")
                break
            except Exception as e:
                attempt += 1
                if attempt >= retries:
                    log_message(f"Failed to send message to user {user_id}: {e}")
                    print(f"Failed to send message to user {user_id}: {e}")
                time.sleep(1)  # Wait before retrying

def send_image_to_all_users(image_source, caption, is_url=False, retries=3):
    """Send an image (local or URL) to all users listed in the JSON file, with retries."""
    users = load_user_data()
    if not users:
        print("No users found in the data file.")
        return

    for user_id, user_info in users.items():
        attempt = 0
        while attempt < retries:
            try:
                if is_url:
                    bot.send_photo(user_id, image_source, caption=caption)
                else:
                    with open(image_source, "rb") as photo:
                        bot.send_photo(user_id, photo, caption=caption)
                log_message(f"Image sent to user {user_id} ({user_info.get('username', 'Unknown')}).")
                print(f"Image sent to user {user_id} ({user_info.get('username', 'Unknown')}).")
                break
            except Exception as e:
                attempt += 1
                if attempt >= retries:
                    log_message(f"Failed to send image to user {user_id}: {e}")
                    print(f"Failed to send image to user {user_id}: {e}")
                time.sleep(1)  # Wait before retrying

def is_valid_url(url):
    """Validate the URL format using a regex pattern."""
    url_pattern = re.compile(r"^(http|https)://[^\s/$.?#].[^\s]*$")
    return url_pattern.match(url)

def main():
    """Main function to execute the sending of messages."""
    log_message("Message sending process started.")
    
    # Ask user for each option
    send_text = input("Do you want to send a text message? (yes/no): ").strip().lower() == "yes"
    send_local_image = input("Do you want to send a local image? (yes/no): ").strip().lower() == "yes"
    send_url_image = input("Do you want to send an image from a URL? (yes/no): ").strip().lower() == "yes"

    # Display summary of choices and confirm before proceeding
    print("\nYou selected the following options:")
    if send_text:
        print("- Send a text message")
    if send_local_image:
        print("- Send a local image")
    if send_url_image:
        print("- Send an image from a URL")

    confirm = input("\nDo you want to proceed with sending these messages? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Process aborted.")
        log_message("Process aborted by the user.")
        return

    # Send Text Message
    if send_text:
        message = input("Enter the text message to send to all users: ").strip()
        if message:
            send_text_to_all_users(message)
        else:
            print("No message entered. Skipping text message.")

    # Send Local Image
    if send_local_image:
        image_path = input("Enter the path to the local image: ").strip()
        if not image_path or not os.path.isfile(image_path):
            print("Invalid image path. Skipping local image.")
        else:
            caption = input("Enter a caption for the local image (optional): ").strip()
            send_image_to_all_users(image_path, caption, is_url=False)

    # Send Image from URL
    if send_url_image:
        image_url = input("Enter the URL of the image: ").strip()
        if not is_valid_url(image_url):
            print("Invalid URL format. Skipping image from URL.")
        else:
            caption = input("Enter a caption for the URL image (optional): ").strip()
            send_image_to_all_users(image_url, caption, is_url=True)

    print("\nMessages have been sent.")
    log_message("Message sending process completed.")

if __name__ == "__main__":
    main()
