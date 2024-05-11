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


import os
from config import app_path  # Import the app_path from config.py

# Function to get the allowed relative paths
def get_allowed_relative_paths():
    # List of relative paths
    relative_paths = [
        './README.md',
        './aish3.py',
        './audio_service.py',
        './command_listener.py',
        './config.py',
        './draw.py',
        './file_collection.py',
        './gui/__init__.py',
        './gui/fonts.py',
        './gui/gui.py',
        './gui/gui_container.py',
        './gui/gui_control.py',
        './gui_focus.py',
        './gui_layout.py',
        './label.py',
        './llm_chat_container.py',
        './record_audio.py',
        './rect_utils.py',
        './session.py',
        './test/__init__.py',
        './test/test_gui_coordinates.py',
        './test/test_text_edit_buffer.py',
        './textarea.py',
        './text_edit_buffer.py',
        './transcribe_audio.py',
        './utils.py',
        './voice_out.py',
        './voice_wakeup.py'
    ]

# Function to get allowed real paths based on a base path
def get_allowed_real_paths():
    relative_paths = get_allowed_relative_paths()
    return [os.path.realpath(os.path.join(app_path, rp)) for rp in relative_paths]

# Function to read content from a file given its path, after checking for permissions
def read_file_checked(path):
    # the app_path imported from config is now used directly
    allowed_paths = get_allowed_real_paths()

    # Convert the provided path to its real path (canonical absolute path)
    real_path = os.path.realpath(path)
    
    # Check if the real path is in the list of allowed paths
    if real_path not in allowed_paths:
        raise PermissionError("Access to the requested file is not allowed.")
    
    # Read and return the file content
    with open(real_path, 'r') as file:
        content = file.read()
    
    return content

# Rest of the get_allowed_relative_paths() function code...
