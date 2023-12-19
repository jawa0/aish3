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


import logging
import weakref


class FocusRing():
    def __init__(self, controls=[], **kwargs):
        self.gui = kwargs.get("gui")
        assert(self.gui is not None)

        self._controls = list(controls)  # @note Copy it so our mods won't be propagaged outside this object
        if len(self._controls) > 0:
            # self.set_focus(self._controls[0])
            self.gui.set_focus(self._controls[0], True)


    def get_focus(self):
        return self.gui.get_focus()


    # Add a control to the FocusRing
    def add(self, control, set_focus=False):
        if control in self._controls:
            raise Exception("Control already in focus ring")
        
        self._controls.append(control)
        control.containing_focus_ring = weakref.ref(self)
        if self.get_focus() is None or set_focus:
            # self.set_focus(control)
            self.gui.set_focus(control, True)


    # Remove a control from the FocusRing
    def remove(self, control: "GUIControl") -> None:
        if control not in self._controls:
            logging.warn("Control not in focus ring")
            return
        
        self._controls.remove(control)
        control.containing_focus_ring = None
        if self.get_focus() == control:
            self.gui.set_focus(control, True)


    def focus_first(self):
        if len(self._controls) > 0:
            # return self.set_focus(self._controls[0])
            return self.gui.set_focus(self._controls[0], True)
        

    def focus_next(self, direction=1):
        # If there are no controls, return.
        if len(self._controls) == 0:
            return False

        control = None

        # If there is no focused control, focus the first control.
        if self.gui.get_focus() is None:
            control = self._controls[0]
        else:
            # Otherwise, focus the next control.
            control = self._next_control(self.gui.get_focus(), offset=direction)

        # assert(control is not None)
            
        first_control_tried = None
        while control != first_control_tried:   # Only go once around loop
            if first_control_tried is None:
                first_control_tried = control

            result = self.gui.set_focus(control, True)
            if result:
                return True
            else:  # Try focusing the next one
                control = self._next_control(control, offset=direction)

        # Rand out of controls to try        
        return False


    def focus_previous(self):
        return self.focus_next(direction=-1)


    def _next_control(self, control, offset=1):
        if control in self._controls:
            i = self._controls.index(control)
            return self._controls[(i + offset) % len(self._controls)]
