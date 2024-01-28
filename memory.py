from embeddings import cos_similarity, embed
import json
import numpy as np
from typing import List, Optional, Tuple
import uuid


class Memory:
    def __init__(self, 
                 text: str, 
                 uid: Optional[uuid.UUID] = None, 
                 summary_sentence: Optional[str] = None,
                 summary_embedding: Optional[np.ndarray] = None,
                 keywords: Optional[List[str]]=[]):
        
        if uid is not None:
            self._uid = uid
        else:
            self._uid = uuid.uuid4()
            
        self._text = text
        self._summary_sentence = summary_sentence
        self._summary_embedding = summary_embedding
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


    @property
    def summary_embedding(self) -> np.ndarray | None:
        return self._summary_embedding
    

    @summary_embedding.setter
    def summary_embedding(self, new_summary_embedding: np.ndarray):
        self._summary_embedding = new_summary_embedding


class MemoryStore:
    def __init__(self):
        self._memories = {}


    def store(self, memory: Memory, context=None) -> None:
        self._memories[memory.uid] = memory
        print(f'STORE memory (uid {memory.uid}):\n"""\n{memory.text}\n"""')
        return memory.uid


    def retrieve_by_uid(self, uid: str) -> str:
        return self._memories.get(uid, None)


    def retrieve_by_similarity(self, text: str) -> [Tuple[float, Memory]]:
        results = []
        query_embedding = embed(text)[0]
        for uid, memory in self._memories.items():
            if memory.summary_embedding is None:
                continue

            similarity = cos_similarity(query_embedding, memory.summary_embedding)
            print(similarity)
            if similarity >= 0.01:
                results.append((similarity, memory))

        return sorted(results, reverse=True)
    

    def retrieve_by_context(self, context) -> [str]:
        results = []
        return results
    

    def save(self, filename: str):
        json_data = {"version": 0.1, "memories": []}
        for uid, memory in self._memories.items():
            json_data["memories"].append({"uid": str(uid), 
                                          "text": memory.text, 
                                          "keywords": memory.keywords,
                                          "summary": memory.summary_sentence,
                                          "summary_embedding": memory.summary_embedding.tolist()})
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
                            summary_embedding=np.array(memory_data["summary_embedding"]),
                            keywords=memory_data["keywords"])
            
            self._memories[memory.uid] = memory
