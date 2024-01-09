import asyncio
from openai import OpenAI, chat
import os
from prompt import LiteralPrompt, Prompt
from session import ChatCompletionHandler, Session
# from typing import Optional


class LLMRequest:
    def __init__(self, session: Session, prompt: Prompt = LiteralPrompt(""), handlers: list = []):
        self._openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) 
        self._session = session
        self._completion: chat.completion = None
        self._handlers = set(handlers)

        self.set_prompt(prompt)        
    

    def set_prompt(self, prompt: Prompt):
        self._prompt = prompt


    async def go(self):
        for handler in self._handlers:
            if hasattr(handler, '_on_start'):
                handler._on_start()

        model = 'gpt-4-1106-preview'
        chat_messages = [{'role': 'system', 'content': ''}, 
                         {'role': 'user', 'content': self._prompt.get_prompt_text()}]
        
        self._completion = self._openai_client.chat.completions.create(model=model, messages=chat_messages, stream=True)
        try:
            while True:
                chunk = next(self._completion)    # Could raise StopIteration
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content'):
                    chunk_text = chunk.choices[0].delta.content
                    for handler in self._handlers:
                        if hasattr(handler, '_on_next'):
                            handler._on_next(chunk_text)

        except StopIteration:
            # This means the completion we tried to call next() on is done.
            # Call all done handlers for that completion
            for handler in self._handlers:
                if hasattr(handler, '_on_finish'):
                    handler._on_finish()


    def _on_start(self):
        print('LLMRequest._on_start()')

    
    def _on_next(self, chunk: str):
        print('LLMRequest._on_next()')

    def _on_finish(self):
        print('LLMRequest._on_finish()')

