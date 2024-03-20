# Copyright 2023-2024 Jabavu W. Adams

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import datetime
from dotenv import load_dotenv
import logging
import openai
import os
import os.path
from pathlib import Path

print('BEFORE load_dotenv()')
load_dotenv()   # Load the .env file
print('AFTER load_dotenv()')

# Set the application path to the current working directory when config is loaded
app_path = os.getcwd()
print(f'app_path: {app_path}')

# Ensure app user config dir exists
app_name = "aish3"

# Create the app config dir if it doesn't exist
app_config_path = Path().home() / f".{app_name}"
app_config_path.mkdir(exist_ok=True, mode=0o700)  # rwx------ permissions

GUI_INSET_X = 2
GUI_INSET_Y = 2

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

