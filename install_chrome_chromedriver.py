import os
import platform
import subprocess
import shutil
import requests
from zipfile import ZipFile
import glob
import json

def download_and_extract(url, filename, extract_dir):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        with ZipFile(filename, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        print(f"Successfully downloaded and extracted {filename} to {extract_dir}")
        os.remove(filename)
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")
    except Exception as e:
        print(f"Error extracting {filename}: {e}")


def set_permissions(path):
    try:
        os.chmod(path, 0o755)
        print(f"Permissions set successfully for {path}")
    except OSError as e:
        print(f"Error setting permissions for {path}: {e}")
    except FileNotFoundError:
        print(f"Error: File not found at {path}")


def install_packages(urls):
    os_name = platform.system()
    machine = platform.machine()
    if os_name == "Linux":
        platform_key = "linux64"
    elif os_name == "Windows":
        platform_key = "win64" if machine == "AMD64" else "win32"
    elif os_name == "Darwin":
        platform_key = "mac-x64" if machine == "x86_64" else "mac-arm64"
    else:
        print(f"Unsupported operating system: {os_name}")
        return

    if platform_key in urls["chrome-headless-shell"] and platform_key in urls["chromedriver"]:
        chrome_url = urls["chrome-headless-shell"][platform_key]
        chromedriver_url = urls["chromedriver"][platform_key]
        download_and_extract(chrome_url, f"chrome_{platform_key}.zip", "./chrome")
        download_and_extract(chromedriver_url, f"chromedriver_{platform_key}.zip", "./chromedriver")

        chrome_dir = os.path.join("./chrome", f"chrome-headless-shell-{platform_key}")
        chromedriver_dir = os.path.join("./chromedriver", f"chromedriver-{platform_key}")

        chrome_executable = os.path.join(chrome_dir, "chrome-headless-shell")
        chromedriver_executable = os.path.join(chromedriver_dir, "chromedriver")

        if os.path.exists(chrome_executable):
            set_permissions(chrome_executable)
        else:
            print(f"Error: Chrome executable not found at {chrome_executable}")

        if os.path.exists(chromedriver_executable):
            set_permissions(chromedriver_executable)
        else:
            print(f"Error: ChromeDriver executable not found at {chromedriver_executable}")


    else:
        print(f"Missing Chrome or ChromeDriver URL for {os_name} and architecture {machine}")


def update_config(platform_key):
    config_path = "config.json"
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: config.json not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in config.json.")
        return

    chrome_dir = os.path.join("./chrome", f"chrome-headless-shell-{platform_key}")
    chromedriver_dir = os.path.join("./chromedriver", f"chromedriver-{platform_key}")

    chrome_executable = os.path.join(chrome_dir, "chrome-headless-shell")
    chromedriver_executable = os.path.join(chromedriver_dir, "chromedriver")

    config["chrome_path"] = chrome_executable
    config["chromedriver_path"] = chromedriver_executable

    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"config.json updated successfully.")
    except Exception as e:
        print(f"Error updating config.json: {e}")


if __name__ == "__main__":
    urls = {
        "chrome-headless-shell": {
            "linux64": "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/linux64/chrome-headless-shell-linux64.zip",
            "mac-arm64": "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/mac-arm64/chrome-headless-shell-mac-arm64.zip",
            "mac-x64": "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/mac-x64/chrome-headless-shell-mac-x64.zip",
            "win32": "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/win32/chrome-headless-shell-win32.zip",
            "win64": "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/win64/chrome-headless-shell-win64.zip"
        },
        "chromedriver": {
            "linux64": "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/linux64/chromedriver-linux64.zip",
            "mac-arm64": "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/mac-arm64/chromedriver-mac-arm64.zip",
            "mac-x64": "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/mac-x64/chromedriver-mac-x64.zip",
            "win32": "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/win32/chromedriver-win32.zip",
            "win64": "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.85/win64/chromedriver-win64.zip"
        }
    }
    os_name = platform.system()
    machine = platform.machine()
    if os_name == "Linux":
        platform_key = "linux64"
    elif os_name == "Windows":
        platform_key = "win64" if machine == "AMD64" else "win32"
    elif os_name == "Darwin":
        platform_key = "mac-x64" if machine == "x86_64" else "mac-arm64"
    else:
        print(f"Unsupported operating system: {os_name}")
        exit(1)

    install_packages(urls)
    update_config(platform_key)
