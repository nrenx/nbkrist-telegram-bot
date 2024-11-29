import json
import os

# Define the JSON file name
DATA_FILE = "nbkrist_attendance_user_data.json"

def load_user_data():
    """Load user data from the JSON file."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as file:
                data = json.load(file)
                return data if data else {} # Handle empty JSON
        except json.JSONDecodeError:
            # Handle invalid JSON by resetting the file
            with open(DATA_FILE, "w") as file:
                file.write("{}")
            return {}
    return {}

def save_user_data(data):
    """Save user data to the JSON file."""
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)

def update_user_data(user_id, key, value):
    """Update a user's data and save it."""
    data = load_user_data()
    if user_id not in data:
        data[user_id] = {}
    data[user_id][key] = value
    save_user_data(data)

def get_user_data(user_id, key, default=None):
    """Retrieve specific data for a user."""
    data = load_user_data()
    return data.get(user_id, {}).get(key, default)
