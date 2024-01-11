import uuid


class MemoryStore:
    def __init__(self):
        self._memories = {}


    def store(self, memory: str, context=None) -> str:
        uid = uuid.uuid4()
        self._memories[uid] = memory
        print(f'STORE memory (uid {uid}):\n"""\n{memory}\n"""')
        return uid


    def retrieve_by_uid(self, uid: str) -> str:
        return self._memories.get(uid, None)


    def retrieve_by_context(self, context) -> [str]:
        results = []
        return results
