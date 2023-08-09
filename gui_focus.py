# (C) 2023 by Jabavu Adams. All Rights Reserved.

import weakref


class FocusRing():
    def __init__(self, controls=[], **kwargs):
        self.gui = kwargs.get("gui")
        assert(self.gui is not None)

        self._controls = list(controls)  # @note Copy it so our mods won't be propagaged outside this object
        self._focused_control = None
        if len(self._controls) > 0:
            self.focus(self._controls[0])


    def get_focus(self):
        return self._focused_control


    # Add a control to the FocusRing
    def add(self, control, set_focus=False):
        if control in self._controls:
            raise Exception("Control already in focus loop")
        
        self._controls.append(control)
        control.containing_focus_ring = weakref.ref(self)
        if self._focused_control is None or set_focus:
            self.focus(control)


    def focus(self, control):
        if control not in self._controls:
            raise Exception("Control not in focus loop")
        
        success = self.gui.set_focus(control, True)
        if success:
            self._focused_control = control
        return success


    def focus_first(self):
        if len(self._controls) > 0:
            return self.focus(self._controls[0])
        

    def focus_next(self, direction=1):
        # If there are no controls, return.
        if len(self._controls) == 0:
            return False

        control = None

        # If there is no focused control, focus the first control.
        if self._focused_control is None:
            control = self._controls[0]
        else:
            # Otherwise, focus the next control.
            control = self._next_control(self._focused_control, offset=direction)

        assert(control is not None)
            
        first_control_tried = None
        while control != first_control_tried:   # Only go once around loop
            if first_control_tried is None:
                first_control_tried = control

            result = self.focus(control)
            if result:
                return True
            else:  # Try focusing the next one
                control = self._next_control(control, offset=direction)

        # Rand out of controls to try        
        return False


    def focus_previous(self):
        return self.focus_next(direction=-1)


    def _next_control(self, control, offset=1):
        i = self._controls.index(control)
        return self._controls[(i + offset) % len(self._controls)]
