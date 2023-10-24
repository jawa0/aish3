import logging
import openai
import os
from typing import Callable, Dict, List, Optional

from audio_service import AudioService


class ChatCompletionHandler:
    def __init__(self, 
                 start_handler: Optional[Callable[[], None]]=None,
                 chunk_handler: Optional[Callable[[str], None]]=None, 
                 done_handler: Optional[Callable[[], None]]=None):
        
        self._start_handler = start_handler
        self._chunk_handler = chunk_handler
        self._done_handler = done_handler


    def on_start(self) -> None:
        if self._start_handler is not None:
            self._start_handler()

            
    def on_text_chunk(self, text: str) -> None:
        if self._chunk_handler is not None:
            self._chunk_handler(text)


    def on_done(self) -> None:
        if self._done_handler is not None:
            self._done_handler()


class Session:
    def __init__(self):
        logging.debug("Client Session.__init__")

        openai.api_key = os.getenv("OPENAI_API_KEY")
        openai.organization = os.getenv("OPENAI_ORGANIZATION")

        self._running_completions: Dict[openai.ChatCompletion, List[ChatCompletionHandler]] = {}
        
        self._audio = AudioService()


    def start(self):
        logging.debug("Client Session.start")
        self._audio.start()

    
    def stop(self):
        logging.debug("Client Session.stop")
        self._audio.stop()


    def update(self):
        # logging.debug("ENTER Client Session.update")
        done_completions = []

        # Pump chat completions...
        for completion in self._running_completions:
            try:
                chunk = next(completion)    # Could raise StopIteration
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content'):
                    chunk_text = chunk.choices[0].delta.content
                    for handler in self._running_completions[completion]:
                        if hasattr(handler, 'on_text_chunk'):
                            handler.on_text_chunk(chunk_text)

            except StopIteration:
                # This means the completion we tried to call next() on is done.
                # 1. Call all done handlers for that completion
                for handler in self._running_completions[completion]:
                    if hasattr(handler, 'on_done'):
                        handler.on_done()

                # 2. Mark that completion for removal, but since we're looping
                #    over the dict, we can't remove it yet.

                done_completions.append(completion)
                continue

        # Remove finished completion callbacks
        for done_completion in done_completions:
            del self._running_completions[done_completion]
        
        # logging.debug("EXIT Client Session.update")


    def llm_send_streaming_chat_request(self, chat_messages, handlers: List[ChatCompletionHandler]=[]):
        completion = openai.ChatCompletion.create(model="gpt-4", messages=chat_messages, stream=True)
        logging.debug(chat_messages)
        self._running_completions[completion] = handlers

        for handler in handlers:
            if hasattr(handler, 'on_start'):
                handler.on_start()
