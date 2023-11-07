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


class GUIControl:
    def __init__(self, can_focus=True, x=0, y=0, w=20, h=20, saveable=True, **kwargs):
        """
        Initializer method (constructor0 for the class.
        
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
        """
        self.gui = kwargs.get('gui')
        self.renderer = kwargs.get('renderer', self.gui.renderer if self.gui else None)
        self.font_descriptor = kwargs.get('font_descriptor', self.gui.font_descriptor if self.gui else "default")
        self.draw_bounds = kwargs.get('draw_bounds', False)
        self._draggable = kwargs.get('draggable', False)
        self._visible = kwargs.get('visible', True)
        self._screen_relative = kwargs.get('screen_relative', False)
        self._saveable = saveable

        # print(f'GUIControl.__init__(): self.font_descriptor={self.font_descriptor}')

        assert(self.gui)

        # Makes unit testing harder, if you aren't actually drawing stuff.
        # assert(self.renderer)
        # assert(self.font_descriptor)

        self.can_focus = can_focus
        self.parent = None
        self.set_bounds(x, y, w, h)
        self.containing_focus_ring = None


    def has_focus(self):
        return self.gui.get_focus() == self
    

    def set_bounds(self, x, y, w, h):
        if hasattr(self, "bounding_rect"):
            self.bounding_rect.x = x
            self.bounding_rect.y = y
            self.bounding_rect.w = w
            self.bounding_rect.h = h
        else:
            self.bounding_rect = sdl2.SDL_Rect(x, y, w, h)


    @classmethod
    def from_json(cls, json, **kwargs):
        assert(json["class"] == cls.__name__)
        saveable = True if "saveable" not in json else json["saveable"]
        kwargs["saveable"] = saveable

        if "bounding_rect" in json:
            x, y, w, h = json["bounding_rect"]
            kwargs["x"] = x
            kwargs["y"] = y
            kwargs["w"] = w
            kwargs["h"] = h

        if "draggable" in json and json["draggable"]:
            kwargs["draggable"] = True
            
        instance = cls(**kwargs)
        return instance


    def __json__(self):
        if not self._saveable:
            return None
            
        json = {}
        json["class"] = self.__class__.__name__
        json["bounding_rect"] = (self.bounding_rect.x, self.bounding_rect.y, self.bounding_rect.w, self.bounding_rect.h)
        return json


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

    
    def get_world_rect(self):
        """Get our bounding rect in 'world' coordinates. I.e. relative to the overall workspace."""
        if self.parent:
            # Our rect is relative to parent, so add parent's offset.
            parent_rect = self.parent.get_world_rect()
            wr = sdl2.SDL_Rect(parent_rect.x + self.bounding_rect.x,
                                 parent_rect.y + self.bounding_rect.y,
                                 self.bounding_rect.w,
                                 self.bounding_rect.h)
        else:
            # Our rect is relative to scene, so it should just be unmodified.
            wr = self.bounding_rect

        return wr
    
    
    def get_view_rect(self):
        """Get our bounding rect in 'view' coordinates. I.e. relative to the viewport position.
        These are what need to be passed to our drawing routines."""

        wr = self.get_world_rect()
        vr = sdl2.SDL_Rect(wr.x - self.gui._viewport_pos[0],
                        wr.y - self.gui._viewport_pos[1],
                        wr.w,
                        wr.h)
        return vr
        

    def _set_focus(self, has_focus):
        if self.can_focus:
            if self.has_focus() and self.parent and has_focus == False:
                self.parent.focused_child = None  # @todo still need this? GUI should handle this @todo
            return True
        else:
            return False


    def handle_event(self, event):
        return self.parent_handle_event(event)
    

    def parent_handle_event(self, event):
        # Pass unhandled events up the runtime child/parent hierarchy.
        if self.parent:
            return self.parent.handle_event(event)
        else:
            return False            

