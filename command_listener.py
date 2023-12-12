# Copyright 2023 Jabavu W. Adams

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import logging
import queue
from session import ChatCompletionHandler, Session
from typing import Callable


class VoiceCommandListener:
    def __init__(self, session: Session, on_command: Callable[[str], None]):
        self.session = session

        self.completion_handler = ChatCompletionHandler(start_handler=self._chat_completion_start,
                                                        chunk_handler=self._chat_completion_chunk,
                                                        done_handler=self._chat_completion_done)
        self.text_in_q = self.session.subscribe("transcribed_text")
        self.on_command = on_command
        self.transcribed_texts = []
        self.detected_command = None
        self._completion_text = None


    def update(self):
        try:
            while True:
                (text, is_final) = self.text_in_q.get_nowait()
                if len(text) == 0:
                    continue

                self.transcribed_texts.append(text)

                if is_final:
                    system = \
"""You are monitoring user input TEXT that has been transcribed from voice audio by a speech to text system.
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
                    # Get last K transcribed texts, for context. Includes partials.
                    K = 3
                    context = "\n".join(self.transcribed_texts[-K:])
                    user = f"TEXT:\n{context}"

                    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]

                    # model = "gpt-4"
                    model = "gpt-3.5-turbo"  # @todo: fails on "don't stop listening" etc.
                    logging.debug(f"**** COMMAND DETECTION: Sending chat request to {model}: {messages}")
                    self.session.llm_send_streaming_chat_request(model, messages, handlers=[self.completion_handler])



        except queue.Empty:
            pass


    def _chat_completion_start(self):
        self._completion_text = ""


    def _chat_completion_chunk(self, chunk_text):
        if chunk_text is not None:
            self._completion_text += chunk_text


    def _chat_completion_done(self):
        logging.debug(f"**** COMMAND DETECTION: Chat completion done. Result: '{self._completion_text}'")
        self.detected_command = self._completion_text.strip()
        self._completion_text = None
        if len(self.detected_command) > 0:
            self.on_command(self.detected_command)
