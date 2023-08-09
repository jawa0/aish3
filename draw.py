# (C) 2023 by Jabavu Adams. All Rights Reserved.

import sdl2
import sdl2.ext
import sdl2.sdlttf as ttf


_char_width_cache = {}

def get_char_width(font_manager, char):
    global _char_width_cache

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


def draw_text(renderer, font_manager, text, x, y, bounding_rect=None, selection_start=None, selection_end=None):
    if len(text.strip()) == 0:
        return
    
    # Draw the text character by character, for now. While this is inefficient, it does
    # allow for the selection background colour to be drawn with simpler logic.

    for i, char in enumerate(text):

        # In SDL, when you render text, you get a new surface containing only that text.
        # To copy it to the renderer, you need to create a texture from the surface, and
        # then copy the texture to the renderer. The surface and texture can then be freed.

        text_surface = font_manager.render(char)
        text_texture = sdl2.SDL_CreateTextureFromSurface(renderer.sdlrenderer, text_surface)

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
            # If this character is part of a selection, then we want to draw it with a different background colour.
            # We'll draw a coloured rectangle behind the character, and then draw the character on top of it.

            if selection_start is not None and selection_end is not None and \
                selection_start <= i < selection_end:
                
                old_color = set_color(renderer, (0, 100, 200, 200))     # @todo @perf every char!
                sdl2.SDL_RenderFillRect(renderer.sdlrenderer, dst_rect)
                set_color(renderer, old_color)

            # Finally, draw the text char by copying the texture with the char to our
            # destination surface.
            sdl2.SDL_RenderCopy(renderer.sdlrenderer, text_texture, src_rect, dst_rect)

        if char == '\n':
            x = 0
            y += text_rect.h
        else:
            x += text_rect.w

        sdl2.SDL_FreeSurface(text_surface)
        sdl2.SDL_DestroyTexture(text_texture)


def draw_cursor(renderer, font_manager, text_buffer, row_spacing, x, y, bounding_rect=None, y_scroll=0): 
    row, col_unexpanded = text_buffer.get_row_col(text_buffer.get_point())
    line_unexpanded = text_buffer.get_line(row, expand_tabs=False)

    cursor_height = row_spacing
    
    x_offset = 0
    for char in line_unexpanded[:col_unexpanded]:
        if char == '\t':
            width = text_buffer.get_tab_spaces() * get_char_width(font_manager, ' ')
        else:
            width = get_char_width(font_manager, char)

        x_offset += width

    old_color = set_color(renderer, (255, 255, 255, 255))

    x_cursor = x + x_offset
    y_cursor = y + row * row_spacing - y_scroll 

    if bounding_rect is None:
        sdl2.SDL_RenderDrawLine(renderer.sdlrenderer, x_cursor, y_cursor, x_cursor, y_cursor + cursor_height)

    elif bounding_rect.x <= x_cursor < bounding_rect.x + bounding_rect.w and (
        y_cursor + cursor_height >= bounding_rect.y  and
        y_cursor <= bounding_rect.y + bounding_rect.h
    ):        
        # Set the scissor rectangle to the bounding rectangle
        # This is so that the cursor doesn't draw outside the bounding rectangle.
        
        sdl2.SDL_RenderSetClipRect(renderer.sdlrenderer, bounding_rect)
        sdl2.SDL_RenderDrawLine(renderer.sdlrenderer, x_cursor, y_cursor, x_cursor, y_cursor + cursor_height)
        sdl2.SDL_RenderSetClipRect(renderer.sdlrenderer, None)

    set_color(renderer, old_color)


def set_color(renderer, new_color):
    # Get the current color
    r, g, b, a = sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8()
    sdl2.SDL_GetRenderDrawColor(renderer.sdlrenderer, r, g, b, a)
    old_color = (r.value, g.value, b.value, a.value)

    # Set the new color
    sdl2.SDL_SetRenderDrawColor(renderer.sdlrenderer, new_color[0], new_color[1], new_color[2], new_color[3])

    # Return the old color
    return old_color

