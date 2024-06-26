import asyncio
from embeddings import cos_similarity, embed
import json
from llm import LLMRequest
import numpy as np
from prompt import PromptTemplate
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
        self._summary_embedding = summary_embedding
        self._keywords = keywords

        self._summary_task_done = False
        self.summary_prompt_template = PromptTemplate(
"""
You are a conversational AI agent. You are being asked to memorize some TEXT and store it as a memory.
Considering the content of the TEXT, generate a sentence that paraphrases and summarizes it. This summary
will be used to generate an embedding for this summary sentence that can later be used with vector similarity
search to retrieve the TEXT memory. If there is a key point to the TEXT, make sure the summary includes that 
key point. Respond with a single sentence. Do not emit any other text or punctuation. Do not include text like "Summary:"

TEXT:

{{ Content }}
""")

        if summary_sentence:
            self._summary_sentence = summary_sentence
        else:
            # Get summary sentence for embedding
            data = {"Content": text}
            self.summary_prompt_template.fill(**data)
            rq_summary = LLMRequest(prompt=self.summary_prompt_template,
                                    handlers=[("stop", self._on_summary_ready)],
                                    custom_data={"mem_uid": self._uid})
            
            print('** SEND SUMMARY REQUEST')
            rq_summary.send_nowait()


    def _on_summary_ready(self, llm_request: LLMRequest) -> str:
        print(f'** RECEIVED MEMORY SUMMARY: {llm_request.response_text}')
        print(f'** UPDATING SUMMARY for Memory {self._uid}')
        
        self._summary_sentence = llm_request.response_text
        self._summary_embedding = embed(self._summary_sentence)[0]


    @property
    def uid(self) -> uuid.UUID:
        return self._uid


    @property
    def text(self) -> str:
        return self._text


    @property
    def keywords(self) -> List[str]:
        return self._keywords
    

    @keywords.setter
    def keywords(self, new_keywords: List[str]):
        self._keywords = new_keywords
    

    @property
    def summary_sentence(self) -> str | None:
        if not hasattr(self, '_summary_sentence'):
            return None
        return self._summary_sentence
    
    @summary_sentence.setter
    def summary_sentence(self, new_summary_sentence: str):
        self._summary_sentence = new_summary_sentence


    @property
    def summary_embedding(self) -> np.ndarray | None:
        if not hasattr(self, '_summary_embedding'):
            return None
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


    def retrieve_by_similarity(self, text: str) -> List[Tuple[float, Memory]]:
        results = []
        query_embedding = embed(text)[0]
        for uid, memory in self._memories.items():
            if memory.summary_embedding is None:
                continue
            similarity = cos_similarity(query_embedding, memory.summary_embedding)
            print(similarity)
            if similarity >= 0.1:
                results.append((similarity, memory))
        try:
            sorted_results = sorted(results, key=lambda x: x[0], reverse=True)
        except:
            seen = set()
            for tup in results:
                if tup[0] in seen:
                    # found duplicate
                    print(tup)
                seen.add(tup[0])
            sorted_results = []
        return sorted_results
    

    def retrieve_by_context(self, context) -> [str]:
        results = []
        return results
    

    def save(self, filename: str):
        json_data = {"version": 0.1, "memories": []}
        for uid, memory in self._memories.items():

            summary_embedding = memory.summary_embedding
            if summary_embedding is not None:
                summary_embedding = summary_embedding.tolist()

            json_data["memories"].append({"uid": str(uid), 
                                          "text": memory.text, 
                                          "keywords": memory.keywords,
                                          "summary": memory.summary_sentence,
                                          "summary_embedding": summary_embedding})
        with open(filename, "w") as f:
            json.dump(json_data, f, indent=2)


    def load(self, filename: str):
        with open(filename, "r") as f:
            json_data = json.load(f)
        for memory_data in json_data["memories"]:
            loaded_uid = uuid.UUID(memory_data["uid"])

            summary_embedding = memory_data["summary_embedding"]
            if summary_embedding is not None:
                summary_embedding = np.array(summary_embedding)

            memory = Memory(memory_data["text"], 
                            uid=loaded_uid, 
                            summary_sentence=memory_data["summary"],
                            summary_embedding=summary_embedding,
                            keywords=memory_data["keywords"])
            
            self._memories[memory.uid] = memory
