from typing import List, Optional
import uuid


class Memory:
    def __init__(self, text: str, summary_sentence: Optional[str] = None, keywords: Optional[List[str]]=[]):
        self._uid = uuid.uuid4()
        self._text = text
        self._summary_sentence = summary_sentence
        self._keywords = keywords


    @property
    def uid(self):
        return self._uid


    @property
    def text(self):
        return self._text


    @property
    def keywords(self):
        return self._keywords
    

    @keywords.setter
    def keywords(self, new_keywords: List[str]):
        self._keywords = new_keywords
    

    @property
    def summary_sentence(self):
        return self._summary_sentence
    
    @summary_sentence.setter
    def summary_sentence(self, new_summary_sentence: str):
        self._summary_sentence = new_summary_sentence


class MemoryStore:
    def __init__(self):
        self._memories = {}


    def store(self, memory: Memory, context=None) -> None:
        self._memories[memory.uid] = memory
        print(f'STORE memory (uid {memory.uid}):\n"""\n{memory.text}\n"""')
        return memory.uid


    def retrieve_by_uid(self, uid: str) -> str:
        return self._memories.get(uid, None)


    def retrieve_by_context(self, context) -> [str]:
        results = []
        return results
