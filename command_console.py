# Copyright 2023-2024 Jabavu W. Adams

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from blinker import signal
import sdl2

from config import GUI_INSET_X, GUI_INSET_Y
from gui import GUI, GUIContainer
from gui_layout import ColumnLayout
from label import Label
from textarea import TextArea


class CommandConsole(GUIContainer):

    def __init__(self, **kwargs):
        PANEL_WIDTH = 1200
        
        super().__init__(layout=ColumnLayout(), **kwargs)
        self.draw_bounds = True
        # self._inset = (GUI_INSET_X, GUI_INSET_Y)

        self.console_label = Label(text="Command Console",
                                   draggable=False,
                                   w=150, 
                                   gui=self.gui)
        self.add_child(self.console_label)

        self.console_area = TextArea(w=PANEL_WIDTH, draggable=False, h=40, gui=self.gui)
        self.console_area.add_pre_event_snoop(self)
        self.add_child(self.console_area)
        
        self._can_focus = False


    def handle_event(self, event):
        # @note: I don't like that each derived class has to remember to do this
        if self._pre_handle_event(event):
            return True
        
        # Specific event handling for the CommandConsole
        if event.type == sdl2.SDL_KEYDOWN:
            keysym = event.key.keysym.sym
            if keysym in (sdl2.SDLK_RETURN, sdl2.SDLK_KP_ENTER):
                # Enter/Return key was pressed, process the command
                command = self.console_area.get_text()
                self.hide()
                self.process_command(command)
                return True
        
        return super().handle_event(event)

    def hide(self):
        self.gui.set_focus(self.console_area, False)
        self._visible = False

    def process_command(self, command):
        # Placeholder for the command processing logic
        print(f'User entered command: """{command}"""')
        signal('channel_raw_user_command').send(command)

        # Clear the TextArea for new input
        self.console_area.set_text('')


GUI.register_control_type("CommandConsole", Label)
