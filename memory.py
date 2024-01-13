import json
from typing import List, Optional
import uuid


class Memory:
    def __init__(self, text: str, uid: Optional[uuid.UUID] = None, summary_sentence: Optional[str] = None, keywords: Optional[List[str]]=[]):
        if uid is not None:
            self._uid = uid
        else:
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
    

    def save(self, filename: str):
        json_data = {"version": 0.1, "memories": []}
        for uid, memory in self._memories.items():
            json_data["memories"].append({"uid": str(uid), 
                                          "text": memory.text, 
                                          "keywords": memory.keywords,
                                          "summary": memory.summary_sentence})
        with open(filename, "w") as f:
            json.dump(json_data, f, indent=2)


    def load(self, filename: str):
        with open(filename, "r") as f:
            json_data = json.load(f)
        for memory_data in json_data["memories"]:
            loaded_uid = uuid.UUID(memory_data["uid"])
            memory = Memory(memory_data["text"], 
                            uid=loaded_uid, 
                            summary_sentence=memory_data["summary"], 
                            keywords=memory_data["keywords"])
            
            self._memories[memory.uid] = memory
