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


import sdl2
from config import GUI_INSET_X, GUI_INSET_Y
import uuid
import weakref


class GUIControl:
    @classmethod
    def from_json(cls, json, **kwargs):
        assert(json["class"] == cls.__name__)

        # @todo: Isn't there a built-in way to do this with dicts?
        # Just saw that recently...
        kwargs = cls._enrich_kwargs(json, **kwargs)            
        instance = cls(**kwargs)
        return instance


    @classmethod
    def _enrich_kwargs(cls, json, **kwargs):
        got_uid = json.get("uid", False)
        if got_uid:
            kwargs["uid"] = got_uid

        kwargs["saveable"] = json.get("saveable", True)
        kwargs["name"] = json.get("name", "")

        if "bounding_rect" in json:
            x, y, w, h = json["bounding_rect"]
            kwargs["x"] = x
            kwargs["y"] = y
            kwargs["w"] = w
            kwargs["h"] = h

        if "draggable" in json and json["draggable"]:
            kwargs["draggable"] = True

        return kwargs


    def __json__(self):
        if not self._saveable:
            return None
            
        json = {}
        json["class"] = self.__class__.__name__
        json["uid"] = self._uid
        json["bounding_rect"] = (self.bounding_rect.x, self.bounding_rect.y, self.bounding_rect.w, self.bounding_rect.h)
        json["z_order"] = self.z_order  # Add this line
        return json


    def __init__(self, can_focus=True, x=0, y=0, w=20, h=20, saveable=True, **kwargs):
        """
        Initializer method for the class.

        can_focus (bool): Indicates if the control can gain focus. Default is True.
        x (int): The x-coordinate of the control's position. Relative to parent 
            control's content area (offset by parent's _inset[0]). If no parent, then in world coordinates. Default is 0.
        y (int): The y-coordinate of the control's position. Relative to parent 
            control's content area (offset by parent's _inset[1]). If no parent, then in world coordinates.  Default is 0.
                
        Keyword arguments are used to fetch 'gui', 'renderer', 'font_manager', 'draw_bounds', 
        'draggable', 'visible', 'screen_relative', and 'saveable' values.

        When 'renderer' or 'font_manager' keyword arguments are missing,
        and 'gui' is not None, 'gui.renderer' and/or 'gui.font_manager' are used
        as the default value for missing ones.

        Keyword Args:
            gui (Object): GUI object, default is None
            renderer (Object): renderer object, default is gui.renderer if gui exists else None
            font_manager (Object): font_manager object, default is gui.font_manager if gui exists else None
            draw_bounds (bool): whether to draw bounds, default is False
            draggable (bool): whether it's draggable, default is False
            visible (bool): whether it's visible, default is True
            screen_relative (bool): whether it's screen relative, default is False
            saveable (bool): whether it's saveable, default is True
            name (str): name of the control, default is "".
        """
        self._uid = kwargs.get('uid', str(uuid.uuid4()))
        self.gui: "GUI" = kwargs.get('gui')
        self.renderer = kwargs.get('renderer', self.gui.renderer if self.gui else None)
        self.font_descriptor = kwargs.get('font_descriptor', self.gui.font_descriptor if self.gui else "default")
        self.draw_bounds = kwargs.get('draw_bounds', False)
        self._editable = kwargs.get('editable', True)
        self._draggable = kwargs.get('draggable', True)
        self._visible = kwargs.get('visible', True)
        self._screen_relative = kwargs.get('screen_relative', False)
        self._saveable = saveable
        self._inset = kwargs.get('inset', (GUI_INSET_X, GUI_INSET_Y))
        self._name = kwargs.get('name', "")

        # print(f'GUIControl.__init__(): self.font_descriptor={self.font_descriptor}')

        assert(self.gui)

        # Makes unit testing harder, if you aren't actually drawing stuff.
        # assert(self.renderer)
        # assert(self.font_descriptor)

        self._can_focus = can_focus
        self.parent = None
        self.set_bounds(x, y, w, h)
        self.pulse_busy = False
        self.editor = None
        self._pre_event_snoops = []


    @property
    def uid(self):
        return self._uid
    
    
    def has_focus(self):
        return self.gui.get_focus() == self
    

    def focus_in(self):
        pass


    def focus_out(self):
        pass


    def set_bounds(self, x, y, w, h):
        """Set the bounding rect for the control. This is relative to its parent, not necessarily
        in world coordinates."""

        if hasattr(self, "bounding_rect"):
            self.bounding_rect.x = x
            self.bounding_rect.y = y
            self.bounding_rect.w = w
            self.bounding_rect.h = h
        else:
            self.bounding_rect = sdl2.SDL_Rect(x, y, w, h)


    def _on_quit(self):
        pass


    # In local coordinates (relative to parent)
    def get_position(self):
        return (self.bounding_rect.x, self.bounding_rect.y)


    # In local coordinates (relative to parent)
    def set_position(self, x, y):
        # print(f'GUIControl.set_position(): x={x}, y={y}')
        self.bounding_rect = sdl2.SDL_Rect(x,
                                           y,
                                           self.bounding_rect.w,
                                           self.bounding_rect.h)


    def get_size(self):
        return (self.bounding_rect.w, self.bounding_rect.h)


    def set_size(self, w, h, updateLayout=True):
        self.bounding_rect = sdl2.SDL_Rect(self.bounding_rect.x,
                                           self.bounding_rect.y,
                                           w,
                                           h)
        if updateLayout:
            self.updateLayout()
            if self.parent is not None:
                self.parent.updateLayout()
        

    def updateLayout(self):
        # print(f'GUIControl.updateLayout(): self={self}')
        pass


    def local_to_world(self, lx: int, ly: int) -> "tuple[int, int]":
        """
        Convert local coordinates of this control to world coordinates.
        The local coordinates are relative to the control's content area, which is
        offset by self._inset from the control's bounding rect.
        
        Args:
            lx (int): The local x-coordinate.
            ly (int): The local y-coordinate.

        Returns:
            A tuple containing the x and y coordinates in world space.
        """
        wx = lx + self._inset[0] + self.bounding_rect.x
        wy = ly + self._inset[1] + self.bounding_rect.y

        for a in self.gui.get_ancestor_chain(self):
            wx += a.bounding_rect.x + a._inset[0]
            wy += a.bounding_rect.y + a._inset[1]
        return wx, wy


    def world_to_local(self, wx: int, wy: int) -> "tuple[int, int]":
        """
        Convert world coordinates to local coordinates of this control. The local coordinates
        are relative to the control's content area, which is offset by self._inset from the
        control's bounding rect.
        
        Args:
            wx (int): The world x-coordinate.
            wy (int): The world y-coordinate.

        Returns:
            A tuple containing the x and y coordinates in local space of this control.
        """
        lx, ly = wx, wy
        for a in self.gui.get_ancestor_chain(self):
            lx -= (a.bounding_rect.x + a._inset[0])
            ly -= (a.bounding_rect.y + a._inset[1])

        lx -= (self.bounding_rect.x + self._inset[0])
        ly -= (self.bounding_rect.y + self._inset[1])

        return lx, ly


    def get_world_rect(self):
        """Get our bounding rect in 'world' coordinates. I.e. relative to the overall workspace."""

        if self.is_screen_relative():
            wr = sdl2.SDL_Rect(self.bounding_rect.x + self.gui._viewport_pos[0], 
                               self.bounding_rect.y + self.gui._viewport_pos[1],
                               self.bounding_rect.w, 
                               self.bounding_rect.h)
        else:
            wx, wy = self.local_to_world(-self._inset[0], -self._inset[1])
            wr = sdl2.SDL_Rect(wx, wy, self.bounding_rect.w, self.bounding_rect.h)
        return wr
    
    
    def get_view_rect(self):
        """Get our bounding rect in 'view' coordinates. I.e. relative to the viewport position.
        These are what need to be passed to our drawing routines."""

        if self.is_screen_relative():
            return self.bounding_rect
        else:
            ancestors = self.gui.get_ancestor_chain(self)
            most_senior_screen_relative_ancestor = None
            for ancestor in ancestors:  # ordered from root on down to control's direct parent
                if ancestor.is_screen_relative():
                    most_senior_screen_relative_ancestor = ancestor
                    break
                
            if most_senior_screen_relative_ancestor is not None:
                x, y = self.gui.local_to_local(self.parent, 
                                               most_senior_screen_relative_ancestor, 
                                               self.bounding_rect.x, 
                                               self.bounding_rect.y)
                
                avr = most_senior_screen_relative_ancestor.get_view_rect()
                vr = sdl2.SDL_Rect(x + avr.x + most_senior_screen_relative_ancestor._inset[0], 
                                   y + avr.y + most_senior_screen_relative_ancestor._inset[1], 
                                   self.bounding_rect.w, 
                                   self.bounding_rect.h)
                return vr
            else:
                wr = self.get_world_rect()
                vx, vy = self.gui.world_to_view(wr.x, wr.y)
                vr = sdl2.SDL_Rect(vx, vy, wr.w, wr.h)
                return vr        
        

    def is_screen_relative(self):
        # Check self first
        if self._screen_relative:
            return True

        # # Now check ancestors
        # for ancestor in self.gui.get_ancestor_chain(self):
        #     if ancestor._screen_relative:
        #         return True

        return False


    def accept_focus(self) -> bool:
        return self._change_focus(True)


    def lose_focus(self) -> bool:
        return self._change_focus(False)


    def can_focus(self) -> bool:    # @todo @note should/can this be a property?
        return self._visible and self._can_focus
    

    def _change_focus(self, am_getting_focus: bool) -> bool:
        if self.can_focus():
            return True
        else:
            return False


    def add_pre_event_snoop(self, func):
        self._pre_event_snoops.append(weakref.ref(func))


    def handle_event(self, event) -> bool:
        # If a derived class of GUIControl does not implement its own event handling, 
        # then it should just pass the event up the runtime scene hierarchy.

        return self.parent_handle_event(event)
    

    def _pre_handle_event(self, event) -> bool:
        # if event.type == sdl2.SDL_KEYDOWN and event.key.keysym.sym == sdl2.SDLK_RETURN:
        #     debug_break = 1

        for weak_snoop in self._pre_event_snoops:
            snoop = weak_snoop()
            if snoop and hasattr(snoop, 'handle_event') and snoop.handle_event(event):
                return True
        return False
    

    def parent_handle_event(self, event) -> bool:
        # Pass unhandled events up the runtime child/parent hierarchy.
        if self.parent:
            return self.parent.handle_event(event)
        else:
            return False            

