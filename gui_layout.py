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
import weakref


class GUILayout:
    def __init__(self, container=None):
        self.set_container(container)


    def get_container(self):
        return self.container() if self.container is not None else None


    def set_container(self, container):
        self.container = weakref.ref(container) if container else None 


class ColumnLayout(GUILayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update(self):
        container = self.get_container()
        if not container:
            return
        
        children = container.get_children()
        is_first = True
        y = 0
        for child in children:
            child.set_position(0, y)
            y += child.bounding_rect.h


class RowLayout(GUILayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update(self):
        container = self.get_container()
        if not container:
            return
        
        children = container.get_children()
        is_first = True
        x = 0
        for child in children:
            child.set_position(x, 0)
            x += child.bounding_rect.w


def rect_union(rect1, rect2):
    x = min(rect1.x, rect2.x)
    y = min(rect1.y, rect2.y)
    w = max(rect1.x + rect1.w, rect2.x + rect2.w) - x
    h = max(rect1.y + rect1.h, rect2.y + rect2.h) - y
    return sdl2.SDL_Rect(x, y, w, h)

