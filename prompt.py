import pystache
from typing import Optional


class Prompt:
    def __init__(self):
        self._prompt_text = ""


    def get_prompt_text(self):
        return self._prompt_text


class LiteralPrompt(Prompt):
    def __init__(self, prompt_text: Optional[str]) -> None:
        self.set_prompt_text(prompt_text)


    def set_prompt_text(self, prompt_text: str) -> None:
        self._prompt_text = prompt_text
    
    
class PromptTemplate(Prompt):
    def __init__(self, template_text: Optional[str]):
        self.set_template(template_text)


    def set_template(self, template_text: str) -> None:
        self._template = template_text
        self._prompt_text = ""


    def fill(self, **kwargs) -> str:
        self._prompt_text = pystache.render(self._template, kwargs)
        return self.get_prompt_text()
    

