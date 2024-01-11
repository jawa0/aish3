import uuid


class MemoryStore:
    def __init__(self):
        self._memories = {}


    def store(self, memory: str, context=None):
        uid = uuid.uuid4()
        self._memories[uid] = memory

        print(f'Storing memory: {memory} with uid: {uid}')


    def retrieve_by_uid(self, uid):
        results = []
        return results


    def retrieve_by_context(self, context):
        results = []
        return results
