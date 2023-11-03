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
        self.gui = kwargs.get('gui')
        self.renderer = kwargs.get('renderer')
        self.font_manager = kwargs.get('font_manager')
        self.draw_bounds = kwargs.get('draw_bounds', False)
        self._draggable = kwargs.get('draggable', False)
        self._visible = kwargs.get('visible', True)
        self._screen_relative = kwargs.get('screen_relative', False)
        self.saveable = saveable

        assert(self.gui)
        assert(self.renderer)
        assert(self.font_manager)

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
        if not self.saveable:
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
        pass

    
    def get_world_rect(self):
        if self.parent:
            parent_rect = self.parent.get_world_rect()
            wr = sdl2.SDL_Rect(parent_rect.x + self.bounding_rect.x,
                                 parent_rect.y + self.bounding_rect.y,
                                 self.bounding_rect.w,
                                 self.bounding_rect.h)
        else:
            wr = self.bounding_rect
            wr = sdl2.SDL_Rect(wr.x - self.gui._viewport_pos[0],
                           wr.y - self.gui._viewport_pos[1],
                           wr.w,
                           wr.h)
        return wr
        

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

