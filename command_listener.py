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

from blinker import signal
import logging
import queue
from typing import Callable
from llm import LLMRequest
from prompt import LiteralPrompt

class CommandListener:
    def __init__(self, session: "Session", on_command: Callable[[str], None]):
        self.session = session
        self.on_command = on_command
        self.detected_command = None
        self._completion_text = None
        
        # Connect to the "channel_user_command" signal
        signal("channel_user_command").connect(self.handle_user_command)

    def handle_user_command(self, command_text: str):
        system = """
You are monitoring user input TEXT that has been transcribed from voice audio by a speech to text system.
You also know a set of COMMANDS that you can execute. Carefully examine the TEXT below, and determine
whether the user is asking you to perform a command from your set of COMMANDS. If so, then respond with
the command only. No other characters. If the user is not asking you to perform a command, then respond with
the empty string. You must also respond with the empty string if you are not sure whether the user is asking
you to perform a command.
--------

COMMANDS:
stop_listening
create_new_chat_with_llm
create_new_text_area
create_new_label(label_text)
pan_screen_left(number_of_pixels)
pan_screen_right(number_of_pixels)
pan_screen_down(number_of_pixels)
pan_screen_up(number_of_pixels)

EXAMPLES:
"stop_listening" -> stop_listening
"don't stop listening" -> ""
"create a new LLM chat" -> create_new_chat_with_llm
"create a new chat" -> create_new_chat_with_llm
"create a new label" -> create_new_label("New Label")
"create a new label with text Hello World" -> create_new_label("Hello World")
"pan screen left 650 pixels" -> pan_screen_left(650)
"pan screen right 40 pixels" -> pan_screen_right(40)
"pan screen down 300 pixels" -> pan_screen_down(300)
"pan screen up 120" -> pan_screen_up(120)
"""

        user = f"TEXT:\n{command_text}"
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        model = "gpt-3.5-turbo"
        logging.debug(f"**** COMMAND DETECTION: Sending chat request to {model}: {messages}")

        def on_completion_start(llm_request: LLMRequest):
            self._completion_text = ""

        def on_completion_next(llm_request: LLMRequest, chunk_text: str):
            if chunk_text is not None:
                self._completion_text += chunk_text

        def on_completion_done(llm_request: LLMRequest):
            logging.debug(f"**** COMMAND DETECTION: Chat completion done. Result: '{self._completion_text}'")
            self.detected_command = self._completion_text.strip()
            self._completion_text = None
            if len(self.detected_command) > 0:
                self.on_command(self.detected_command)

        llm_request = LLMRequest(session=self.session,
                                 prompt=LiteralPrompt(system + "\n" + user),  # @todo make template
                                 handlers=[("start", on_completion_start),
                                           ("next", on_completion_next),
                                           ("stop", on_completion_done)])
        llm_request.send_nowait()