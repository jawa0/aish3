# (C) 2023 by Jabavu Adams. All Rights Reserved.

import sdl2

# @todo I think there is a native SDL function to do this
def rect_union(rect1, rect2):
    x = min(rect1.x, rect2.x)
    y = min(rect1.y, rect2.y)
    w = max(rect1.x + rect1.w, rect2.x + rect2.w) - x
    h = max(rect1.y + rect1.h, rect2.y + rect2.h) - y
    return sdl2.SDL_Rect(x, y, w, h)

