# Copyright 2023 Jabavu W. Adams

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import sdl2

from gui import GUI, GUIContainer
from gui_layout import ColumnLayout

from config import GUI_INSET_X, GUI_INSET_Y
from label import Label
from textarea import TextArea


class CommandConsole(GUIContainer):
    def __init__(self, **kwargs):
        super().__init__(layout=ColumnLayout(), **kwargs)
        self.console_label = Label(text="Command Console", 
                                   x=0, y=0, w=self.bounding_rect.w, h=20,  # Adjust dimensions as needed
                                   gui=self.gui)
        self.add_child(self.console_label, add_to_focus_ring=False)

        self.console_area = TextArea(w=self.bounding_rect.w - GUI_INSET_X, h=60, gui=self.gui)
        self.add_child(self.console_area)


    def handle_event(self, event):
        # Specific event handling for the CommandConsole
        if event.type == sdl2.SDL_KEYDOWN:
            keysym = event.key.keysym.sym
            if keysym in (sdl2.SDLK_RETURN, sdl2.SDLK_KP_ENTER):
                # Enter/Return key was pressed, process the command
                command = self.console_area.get_text()
                self.process_command(command)
                return True
        
        return super().handle_event(event)


    def process_command(self, command):
        # Placeholder for the command processing logic
        print(f'Command Entered: {command}')
        # Clear the TextArea for new input
        self.console_area.set_text('')


GUI.register_control_type("CommandConsole", Label)
