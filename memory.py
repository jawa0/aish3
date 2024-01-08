import uuid


class MemoryStore:
    def __init__(self):
        self._memories = {}


    def store(self, memory, context):
        uid = uuid.uuid4()
        self._memories[uid] = memory


    def retrieve_by_uid(self, uid):
        results = []
        return results


    def retrieve_by_context(self, context):
        results = []
        return results
