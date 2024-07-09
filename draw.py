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


from typing import Dict, Optional, Tuple

import sdl2
import sdl2.ext
import sdl2.sdlttf as ttf

from gui.fonts import FontDescriptor, FontRegistry
from text_edit_buffer import TextEditBuffer

# Key: (font_name, font_size, char)
_char_width_cache: Dict[Tuple[str, int, str], int] = {}


def get_char_width(font_descriptor: FontDescriptor, char: str) -> int:
    global _char_width_cache

    font_manager = FontRegistry().get_fontmanager(font_descriptor)
    assert(font_manager is not None)
    font_name = font_manager.default_font
    font_size = font_manager.size
    key = (font_name, font_size, char)

    if key in _char_width_cache:
        return _char_width_cache[key]

    text_surface = font_manager.render(char)
    char_width = text_surface.w
    sdl2.SDL_FreeSurface(text_surface)

    _char_width_cache[key] = char_width
    return char_width


def draw_rectangle(renderer: 'sdl2.ext.Renderer', rect: sdl2.SDL_Rect) -> None:
    sdl2.SDL_RenderDrawRect(renderer, rect)


def draw_text(renderer, font_descriptor, text, x, y, bounding_rect=None, dst_surface=None, selection_start=None, selection_end=None, color=(255, 255, 255, 255)):
    if len(text.strip()) == 0:
        return
    
    # print(f'draw_text: font_descriptor={font_descriptor}')
    font_manager = FontRegistry().get_fontmanager(font_descriptor)
    assert(font_manager is not None)
    # print(f'draw_text: font_manager={font_manager}')

    # Keep track of initial x, and y since we will be updating x, y for each character.
    # We need to know where each character is relative to the starting point in order
    # to blit our various surfaces correctly.

    if bounding_rect is not None:
        x0 = bounding_rect.x
        y0 = bounding_rect.y
    else:
        x0 = x
        y0 = y

    # Draw the text character by character, for now. While this is inefficient, it does
    # allow for the selection background colour to be drawn with simpler logic.

    # Propagate renderer color to text color
    font_manager.color = sdl2.SDL_Color(color[0], color[1], color[2], color[3])

    for i, char in enumerate(text):

        # In SDL, when you render text, you get a new surface containing only that text.
        # To copy it to the renderer, you need to create a texture from the surface, and
        # then copy the texture to the renderer. The surface and texture can then be freed.

        old_color = set_color(renderer, (255, 0, 0, 255))
        text_surface = font_manager.render(char)
        if dst_surface is None:
            text_texture = sdl2.SDL_CreateTextureFromSurface(renderer.sdlrenderer, text_surface)
        set_color(renderer, old_color)

        text_rect = sdl2.SDL_Rect(x, y, text_surface.w, text_surface.h)

        # If a bounding rectangle is specified, then only draw the text if it intersects with the bounding rectangle.
        # I.e. the text will not be drawn outside the bounding rectangle.
        
        src_rect = None
        dst_rect = None
        do_draw_text = True

        if bounding_rect is not None:
            overlap_rect = sdl2.SDL_Rect()
            theyDoIntersect = sdl2.SDL_IntersectRect(text_rect, bounding_rect, overlap_rect)

            if theyDoIntersect:

                # The text and bounding rectangle intersect, so draw the text. But, if they only partially overlap,
                # then we need to adjust the text rectangle so that it only draws the part of the text that intersects.
                # Maybe we could use a scissor test instead, and copy the whole rect?

                src_rect = sdl2.SDL_Rect(overlap_rect.x - text_rect.x, overlap_rect.y - text_rect.y, overlap_rect.w, overlap_rect.h)
                dst_rect = overlap_rect
            else:
                # The text and bounding rectangle do not intersect, so don't draw the text.
                do_draw_text = False
        else:
            # No bounding rectangle specified, so draw the text as normal.
            src_rect = None
            dst_rect = text_rect
            
        if do_draw_text:
            dst_rect2 = sdl2.SDL_Rect(dst_rect.x - x0, dst_rect.y - y0, dst_rect.w, dst_rect.h)

            # If this character is part of a selection, then we want to draw it with a different background colour.
            # We'll draw a coloured rectangle behind the character, and then draw the character on top of it.

            if selection_start is not None and selection_end is not None and \
                selection_start <= i < selection_end:
                
                old_color = set_color(renderer, (0, 100, 200, 200))     # @todo @perf every char!
                # sdl2.SDL_RenderFillRect(renderer.sdlrenderer, dst_rect2)
                # sdl2.SDL_RenderFillRect(dst_surface, dst_rect2)
                sdl2.SDL_FillRect(dst_surface, dst_rect2, sdl2.SDL_MapRGBA(dst_surface.contents.format, 0, 100, 200, 200))
                set_color(renderer, old_color)

            # Finally, draw the text char by copying the texture with the char to our
            # destination surface.

            if dst_surface is None:
                sdl2.SDL_RenderCopy(renderer.sdlrenderer, text_texture, src_rect, dst_rect)
            else:
                sdl2.SDL_BlitSurface(text_surface, src_rect, dst_surface, dst_rect2)

        if char == '\n':
            x = 0
            y += text_rect.h
        else:
            x += text_rect.w

        if dst_surface is None:
            sdl2.SDL_DestroyTexture(text_texture)
        sdl2.SDL_FreeSurface(text_surface)


def draw_cursor(renderer: 'sdl2.ext.Renderer', 
                font_descriptor: FontDescriptor, 
                text_buffer: TextEditBuffer, 
                row_spacing: int, 
                x: int, 
                y: int, 
                bounding_rect: 'Optional[sdl2.SDL_Rect]' = None, 
                x_scroll: int = 0, 
                y_scroll: int = 0,
                dont_draw_just_calculate: bool = False) -> Tuple[int, int]: 
    """
    Draws or calculates the position of the cursor within a text buffer.

    This function determines the cursor's x and y position within a given text
    buffer, optionally drawing it using the provided renderer. Calculation of
    the cursor's position accounts for tab expansion and scrolling offsets.

    Args:
        renderer: The rendering context onto which the cursor may be drawn.
        font_descriptor: Data describing the font, used to calculate character widths.
        text_buffer: The text buffer which contains the text and cursor position.
        row_spacing: The vertical distance from the start of one row of text, to the next, in pixels.
        x: The x coordinate of the top-left corner of the text area.
        y: The y coordinate of the top-left corner of the text area.
        bounding_rect (optional): A rectangle that defines the clipping area for drawing.
        x_scroll (optional): The horizontal scroll offset.
        y_scroll (optional): The vertical scroll offset.
        dont_draw_just_calculate (optional): If set to True, the function will not
                                              draw the cursor but only calculate
                                              its position.

    Returns:
        A tuple (x_cursor, y_cursor) representing the cursor's coordinates. If the
        cursor is drawn, these coordinates indicate where the cursor was drawn.
        If drawing is skipped, they indicate where the cursor would have been
        drawn.

    Note:
        If `bounding_rect` is provided, the cursor will be drawn clipped to this
        rectangle. The cursor will not be drawn outside this area.

        If `dont_draw_just_calculate` is True, no drawing operations will occur,
        and the function serves to return the cursor's computed position.
    """

    row, col_unexpanded = text_buffer.get_row_col(text_buffer.get_point())
    line_unexpanded = text_buffer.get_line(row, expand_tabs=False)

    cursor_height = row_spacing
    
    x_offset = 0
    for char in line_unexpanded[:col_unexpanded]:
        if char == '\t':
            width = text_buffer.get_tab_spaces() * get_char_width(font_descriptor, ' ')
        else:
            width = get_char_width(font_descriptor, char)

        x_offset += width

    x_cursor = x + x_offset - x_scroll
    y_cursor = y + row * row_spacing - y_scroll 

    if bounding_rect is None:
        if not dont_draw_just_calculate:
            sdl2.SDL_RenderDrawLine(renderer.sdlrenderer, x_cursor, y_cursor, x_cursor, y_cursor + cursor_height)

    elif bounding_rect.x <= x_cursor < bounding_rect.x + bounding_rect.w and (
        y_cursor + cursor_height >= bounding_rect.y  and
        y_cursor <= bounding_rect.y + bounding_rect.h
    ):        
        # Set the scissor rectangle to the bounding rectangle
        # This is so that the cursor doesn't draw outside the bounding rectangle.
        
        if not dont_draw_just_calculate:
            sdl2.SDL_RenderSetClipRect(renderer.sdlrenderer, bounding_rect)
            sdl2.SDL_RenderDrawLine(renderer.sdlrenderer, x_cursor, y_cursor, x_cursor, y_cursor + cursor_height)
            sdl2.SDL_RenderSetClipRect(renderer.sdlrenderer, None)

    return x_cursor, y_cursor


def get_color(renderer: 'sdl2.SDL_Renderer') -> Tuple[int, int, int, int]:
    """
    Get the renderer's current drawing color.

    Parameters:
    renderer : SDL_Renderer
        A pointer to the rendering context.

    Returns:
    tuple of 4 uint8
        A (red, green, blue, alpha) tuple representing the RGBA color that is currently set.

    Note:
    This function relies on PySDL2's SDL2 bindings for interacting with SDL_Renderer.
    """
    r, g, b, a = sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8()
    sdl2.SDL_GetRenderDrawColor(renderer.sdlrenderer, r, g, b, a)
    return (r.value, g.value, b.value, a.value)


def set_color(renderer: 'sdl2.SDL_Renderer', new_color: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    """
    Change the renderer's current drawing color to the new specified color.

    This function gets the current drawing color from the renderer, sets a new drawing color, 
    and then returns the old color.

    Parameters:
    renderer : SDL_Renderer
        A pointer to the rendering context.
    new_color : tuple of 4 uint8
        A (red, green, blue, alpha) tuple representing the RGBA color to set. Each color
        component should be an integer in the range 0-255.

    Returns:
    tuple of 4 uint8
        A (red, green, blue, alpha) tuple representing the old RGBA color that was set
        before this function changed it.

    Note:
    This function relies on PySDL2's SDL2 bindings for interacting with SDL_Renderer.
    """
    # Get the current color
    old_color = get_color(renderer)

    # Set the new color
    sdl2.SDL_SetRenderDrawColor(renderer.sdlrenderer, new_color[0], new_color[1], new_color[2], new_color[3])

    # Return the old color
    return old_color


def draw_marker_point(renderer: 'sdl2.ext.Renderer',
                vx: int, 
                vy: int,
                caption: Optional[str] = None,
                font_descriptor: Optional[FontDescriptor] = None,
                color: Tuple[int, int, int, int] = (255, 255, 255, 255),
                cross_radius: int = 20):
    """
    """
    # Get the current color so we can set it back when we're done
    # @perf optional? What if I want to draw a whole run of things of
    # the same color? Extra state changes.
    
    old_color = set_color(renderer, color)

    # Draw the horizontal line of the cross
    sdl2.SDL_RenderDrawLine(renderer.sdlrenderer,
                            vx - max(0, cross_radius-1), 
                            vy, 
                            vx + max(0, cross_radius-1), 
                            vy)
    
    # Draw the vertical line of the cross
    sdl2.SDL_RenderDrawLine(renderer.sdlrenderer,
                            vx, 
                            vy - max(0, cross_radius-1), 
                            vx, 
                            vy + max(0, cross_radius-1))
    
    # Optionally, draw text
    if caption is not None and font_descriptor is not None:
        draw_text(renderer, font_descriptor, caption, vx + 5, vy + 5, color=color)

    # Set the color back to what it was
    set_color(renderer, old_color)
