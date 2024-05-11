from enum import Enum, auto
from typing import List
import uuid


class ChangeType(Enum):
    INSERTION = auto()
    SUBSTITUTION = auto()
    DELETION = auto()

class TargetType(Enum):
    FILE = auto()
    TEXT_EDIT_BUFFER = auto()

class CodeChangeTarget:
    def __init__(self, target_type: TargetType):
        self.target_type = target_type

class FileTarget(CodeChangeTarget):
    def __init__(self):
        super().__init__(TargetType.FILE)

class BufferTarget(CodeChangeTarget):
    def __init__(self):
        super().__init__(TargetType.TEXT_EDIT_BUFFER)

class CodeChange:
    def __init__(self, change_type: ChangeType, target: CodeChangeTarget, content: str = None, position: int = None):
        self.change_type = change_type
        self.target = target
        self.content = content
        self.position = position

    def apply_change(self):
        # Implement logic to apply change to the target.
        pass

class CodeChanges:
    def __init__(self):
        self.code_changes: List[CodeChange] = []

    def add_change(self, change: CodeChange):
        self.code_changes.append(change)

    def apply_changes(self):
        for change in self.code_changes:
            change.apply_change()

class HypotheticalScenario:
    def __init__(self):
        self._uuid = uuid.uuid4()
        self.code_changes = CodeChanges()
        self.project = None
        

    def add_code_change(self, code_change: CodeChange):
        self.code_changes.add_change(code_change)

    def apply_code_changes(self):
        self.code_changes.apply_changes()
