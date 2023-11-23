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
from rect_utils import rect_union
import sdl2
from gui_layout import ColumnLayout
from gui_focus import FocusRing
from .gui_control import GUIControl
import gui
import math


class GUIContainer(GUIControl):
    @classmethod
    def from_json(cls, json, **kwargs):
        assert(json["class"] == cls.__name__)

        # kwargs["inset"] = json

        instance = super().from_json(json, **kwargs)
        for child_json in json["children"]:
            # print(f'child_json: {child_json}')
            if child_json is None:
                logging.warning('child_json is None')
                continue

            child_class = gui.GUI.control_class(child_json["class"])
            if child_class is None:
                logging.warning(f'Could not find class {child_json["class"]}')
                continue

            # print(f'child_class: {child_class}')
            child = child_class.from_json(child_json, **kwargs)
            # print(f'child: {child}')
            if child is not None:
                instance.add_child(child)

        if "layout" in json:
            layout_class_name = json["layout"]
            if layout_class_name == "ColumnLayout":
                instance.set_layout(ColumnLayout())
        return instance
    

    def __init__(self, children=None, layout=None, **kwargs):
        super().__init__(**kwargs)
        self.draw_bounds = False  #kwargs.get('draw_bounds', True)
        
        self.children = children if children is not None else []

        self.set_layout(layout)
        self.focusRing = FocusRing(gui=self.gui)


    def __iter__(self):
        self._iter_index = 0
        return self


    def __next__(self):
        if self._iter_index < len(self.children):
            result = self.children[self._iter_index]
            self._iter_index += 1
            return result
        else:
            raise StopIteration


    def __json__(self):
        json = super().__json__()
        if json == None:
            return None

        json["class"] = self.__class__.__name__
        json["layout"] =  self.layout.__class__.__name__ if self.layout else None
        json["name"] = self._name
        json["inset"] = self._inset

        json["children"] = []
        for child in self.children:
            child_json = child.__json__()
            if child_json is not None:
                json["children"].append(child_json)
        
        return json


    def set_layout(self, layout):
        self.layout = layout
        if layout is not None:
            self.layout.set_container(self)
            if self.children:
                self.updateLayout()


    def on_update(self, dt):
        for c in self:
            if hasattr(c, 'on_update'):
                c.on_update(dt)


    def draw(self):
        if not self._visible:
            return
        
        vr = self.get_view_rect()

        # Draw own bounding rect
        if self.draw_bounds and self.bounding_rect is not None:
            # Save the current color
            r, g, b, a = sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8()
            sdl2.SDL_GetRenderDrawColor(self.renderer.sdlrenderer, r, g, b, a)
            old_color = (r.value, g.value, b.value, a.value)

            # Set the new color
            r, g, b = (0, 127, 255) if self.has_focus() else (100, 100, 100)
            # r, g, b = (0, 255, 0)
            sdl2.SDL_SetRenderDrawColor(self.renderer.sdlrenderer, r, g, b, 255)

            # Draw the bounding rectangle
            sdl2.SDL_RenderDrawRect(self.renderer.sdlrenderer, vr)

            # # Draw insets
            # r, g, b = (255, 0, 0)
            # sdl2.SDL_SetRenderDrawColor(self.renderer.sdlrenderer, r, g, b, 255)
            # inset_rect = sdl2.SDL_Rect(vr.x + self._inset[0], vr.y + self._inset[1], vr.w - 2 * self._inset[0], vr.h - 2 * self._inset[1])
            # sdl2.SDL_RenderDrawRect(self.renderer.sdlrenderer, inset_rect)

            # Reset to the old color
            sdl2.SDL_SetRenderDrawColor(self.renderer.sdlrenderer, old_color[0], old_color[1], old_color[2], old_color[3])

        # Draw children
        for child in self:
            if child._visible:
                child.draw()


    def get_children(self):
        return self.children if self.children else []


    def add_child(self, child, add_to_focus_ring=True):
        # print(f'GUIContainer.add_child(): child={child}')

        child.parent = self
        self.children.append(child)

        self.updateLayout()

        if add_to_focus_ring:
            self.focusRing.add(child)
            self.focusRing.focus(child)


    def remove_child(self, child):
        self.focusRing.remove(child)
        self.children.remove(child)
        if self.gui._focused_control == child:
            self.gui._focused_control = None

        child.parent = None
        self.updateLayout()


    def updateLayout(self):
        # print(f'GUIContainer.updateLayout(): self={self}')
        if self.layout is not None:
            self.layout.update()

        self.sizeToChildren()

        if self.parent is not None:
            self.parent.updateLayout()


    def sizeToChildren(self):
        # print(f"************* GUIContainer.sizeToChildren() name='{self._name}' *************")
        # print(f"  self.bounding_rect={self.bounding_rect}, self._inset={self._inset}")
        # # print(f'GUIContainer.sizeToChildren(): self={self}')
        if not self.children:
            return
        else:
            my_content_x_wrt_parent_content, my_content_y_wrt_parent_content = self.gui.local_to_local(self, self.parent, 0, 0)

            # print(f'GUIContainer.sizeToChildren(): my_content_x_wrt_parent_content={my_content_x_wrt_parent_content}, my_content_y_wrt_parent_content={my_content_y_wrt_parent_content}')

            # Child coordinates are always relative to us. Make sure to handle the case where some of
            # them are negative. Also, maybe we deleted our leftmost or topmost. So in these cases,
            # our position will also change.

            children_x_min_wrt_my_content_area = math.inf
            children_x_max_wrt_my_content_area = -math.inf
            children_y_min_wrt_my_content_area = math.inf
            children_y_max_wrt_my_content_area = -math.inf

            count_non_screen_locked_children = 0
            for c in self.children:
                # If the child is screen-relative, it should not contribute to our size.
                if c.is_screen_relative():
                    continue
                count_non_screen_locked_children += 1

                children_x_min_wrt_my_content_area = min(children_x_min_wrt_my_content_area, c.bounding_rect.x)
                children_x_max_wrt_my_content_area = max(children_x_max_wrt_my_content_area, c.bounding_rect.x + c.bounding_rect.w)
                children_y_min_wrt_my_content_area = min(children_y_min_wrt_my_content_area, c.bounding_rect.y)
                children_y_max_wrt_my_content_area = max(children_y_max_wrt_my_content_area, c.bounding_rect.y + c.bounding_rect.h)

            if count_non_screen_locked_children == 0:
                children_x_min_wrt_my_content_area = 0
                children_x_max_wrt_my_content_area = 0
                children_y_min_wrt_my_content_area = 0
                children_y_max_wrt_my_content_area = 0

            # children_x_min_wrt_my_content_area -= self._inset[0]
            # children_x_max_wrt_my_content_area += self._inset[0]
            # children_y_min_wrt_me -= self._inset[1]
            # children_y_max_wrt_me += self._inset[1]
            
            # We want to move ourselves so that AFTER, (0, 0) relative to our content area corresponsds to
            # the world coordinates of (children_x_min_wrt_my_content_area, children_y_min_wrt_my_content_area) BEFORE.

            my_content_area_wx_before, my_content_area_wy_before = self.local_to_world(0, 0)
            my_content_area_wx_after, my_content_area_wy_after = self.local_to_world(children_x_min_wrt_my_content_area, children_y_min_wrt_my_content_area)

            my_x_shift = my_content_area_wx_after - my_content_area_wx_before
            my_y_shift = my_content_area_wy_after - my_content_area_wy_before

            # print(f'GUIContainer.sizeToChildren(): my_x_shift={my_x_shift}, my_y_shift={my_y_shift}')
        
            child_x_shift = -my_x_shift
            child_y_shift = -my_y_shift

            # print(f'GUIContainer.sizeToChildren(): child_x_shift={child_x_shift}, child_y_shift={child_y_shift}')

            for c in self.children:
                # If the child is screen-relative, don't move it.
                if c.is_screen_relative():
                    continue

                c.set_position(c.bounding_rect.x + child_x_shift, c.bounding_rect.y + child_y_shift)

            # self.set_position(my_content_x_wrt_parent_content + my_x_shift, my_content_y_wrt_parent_content + my_y_shift)
            self.set_position(self.bounding_rect.x + my_x_shift, self.bounding_rect.y + my_y_shift)

            new_width_local = children_x_max_wrt_my_content_area - children_x_min_wrt_my_content_area + 2 * self._inset[0]
            new_height_local = children_y_max_wrt_my_content_area - children_y_min_wrt_my_content_area + 2 * self._inset[1]

            # print(f'GUIContainer.sizeToChildren(): new_width_local={new_width_local}, new_height_local={new_height_local}')

            self.set_size(new_width_local, new_height_local, updateLayout=False)
    
