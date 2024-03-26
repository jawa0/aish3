import asyncio
from openai import OpenAI, chat
import os
from prompt import LiteralPrompt, Prompt
from typing import Callable, Dict, List, Literal, Optional, Tuple


class LLMRequest:
    def __init__(self,
                 prompt: Prompt = LiteralPrompt(""), 
                 previous_messages: List[Dict[str, str]] = [],
                 tools: Optional[List[Dict]] = [],
                 tool_choice: Optional[str] = None,
                 handlers: [Tuple[Literal["start", "next", "stop"], Callable]] = [], 
                 respond_with_json: bool = False,
                 custom_data: Dict = {}):
        
        self._openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._completion: chat.completion = None
        self._task = None
        self._s_response = ""
        self._previous_messages = previous_messages
        self._respond_with_json = respond_with_json
        self._custom_data = custom_data
        self._tools = tools
        self._tool_choice = tool_choice

        self.set_prompt(prompt)

        self._handlers = {"start": [], "next": [], "stop": []}
        for kind, callback in handlers:
            self._handlers[kind].append(callback)
    

    @property
    def response_text(self):
        return self._s_response


    @property
    def task(self):
        return self._task
    

    @property
    def custom_data(self):
        return self._custom_data
    

    def set_prompt(self, prompt: Prompt):
        self._prompt = prompt


    def send_nowait(self):
        # print('**** ENTER LLMRequest.send()')
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._go())
        # print('**** LEAVE LLMRequest.send()')
        return self._task

    
    def is_done(self):
        return self._task is None or self._task.done()
    

    async def _go(self):
        # print('**** LLMRequest.go()')

        self._s_response = ""
        for cb in self._handlers["start"]:
            cb(self)

        model = 'gpt-4-1106-preview'

        if self._previous_messages:
            chat_messages = [{'role': 'system', 'content': ''},
                         {'role': 'user', 'content': self._prompt.get_prompt_text()}]
        else:
            chat_messages = self._previous_messages + \
                [{'role': 'user', 'content': self._prompt.get_prompt_text()}]

        args = {"model": model, "messages": chat_messages, "stream": True}  
        if self._respond_with_json:
            args["response_format"] = { "type": "json_object" }

        if self._tools is not None and len(self._tools) > 0:
            args["tools"] = self._tools
            # if self._tool_choice is not None:
            #     args["tool_choice"] = self._tool_choice

        self._completion = self._openai_client.chat.completions.create(**args)
        try:
            while True:
                # print('**** LLMRequest.go() calling next()')
                chunk = next(self._completion)    # Could raise StopIteration
                # print('**** LLMRequest.go() got chunk')
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content'):
                    chunk_text = chunk.choices[0].delta.content
                    if chunk_text is not None:
                        self._s_response += chunk_text
                    for cb in self._handlers["next"]:
                        cb(self, chunk_text)
                
                await asyncio.sleep(0.001)

        except StopIteration:
            # This means the completion we tried to call next() on is done.
            # Call all done handlers for that completion

            for cb in self._handlers["stop"]:
                cb(self)

        # print('**** LLMRequest.go() done')
