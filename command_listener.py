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
"stop_listening"
"""
                    # Get last K transcribed texts, for context. Includes partials.
                    K = 3
                    context = "\n".join(self.transcribed_texts[-K:])
                    user = f"TEXT:\n{context}"

                    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]

                    model = "gpt-4"
                    # model = "gpt-3.5-turbo"  # @todo: fails on "don't stop listening" etc.
                    logging.debug(f"**** COMMAND DETECTION: Sending chat request to {model}: {messages}")
                    self.session.llm_send_streaming_chat_request(model, messages, handlers=[self.completion_handler])



        except queue.Empty:
            pass


    def _chat_completion_start(self):
        self._completion_text = ""


    def _chat_completion_chunk(self, chunk_text):
        self._completion_text += chunk_text


    def _chat_completion_done(self):
        logging.debug(f"**** COMMAND DETECTION: Chat completion done. Result: '{self._completion_text}'")
        self.detected_command = self._completion_text.strip()
        self._completion_text = None
        if len(self.detected_command) > 0:
            self.on_command(self.detected_command)
