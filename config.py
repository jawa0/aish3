import datetime
from dotenv import load_dotenv
import logging
import openai
import os.path
from pathlib import Path


load_dotenv()   # Load the .env file

# Ensure app user config dir exists
app_name = "aish3"

# Create the app config dir if it doesn't exist
app_config_path = Path().home() / f".{app_name}"
app_config_path.mkdir(exist_ok=True, mode=0o700)  # rwx------ permissions


def setup_logging():
    formatter = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s")

    #
    # Setup logging to STDOUT
    #
    
    handle_logs_to_stdout = logging.StreamHandler()
    handle_logs_to_stdout.setFormatter(formatter)
    handle_logs_to_stdout.setLevel(logging.DEBUG)

    #
    # Setup logging to file
    #

    # Create log dir if it doesn't exist
    logs_dir = "logs"
    logs_path = app_config_path / logs_dir
    logs_path.mkdir(exist_ok=True)

    # Name our log file using the current time
    start_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = logs_path / f'{app_name}-{start_timestamp}.log'
    handle_logs_to_file = logging.FileHandler(log_file_path)
    handle_logs_to_file.setFormatter(formatter)
    handle_logs_to_file.setLevel(logging.DEBUG)

    handlers = [handle_logs_to_stdout, handle_logs_to_file]

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    for handler in handlers:
        root_logger.addHandler(handler)


    # Increase OpenAI log level
    logging.getLogger("openai").setLevel(logging.DEBUG)


setup_logging()
