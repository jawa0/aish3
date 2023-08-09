# (C) 2023 by Jabavu Adams. All Rights Reserved.

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
        # @todo DRY
        INSET_X = 1
        INSET_Y = 1

        container = self.get_container()
        if not container:
            return
        
        children = container.get_children()
        is_first = True
        y = INSET_Y
        for child in children:
            child.set_position(INSET_X, y)
            y += child.bounding_rect.h


class RowLayout(GUILayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update(self):
        # @todo DRY
        INSET_X = 1
        INSET_Y = 1

        container = self.get_container()
        if not container:
            return
        
        children = container.get_children()
        is_first = True
        x = INSET_X
        for child in children:
            child.set_position(x, INSET_Y)
            x += child.bounding_rect.w


def rect_union(rect1, rect2):
    x = min(rect1.x, rect2.x)
    y = min(rect1.y, rect2.y)
    w = max(rect1.x + rect1.w, rect2.x + rect2.w) - x
    h = max(rect1.y + rect1.h, rect2.y + rect2.h) - y
    return sdl2.SDL_Rect(x, y, w, h)

