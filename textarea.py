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


import ctypes
import sdl2
from draw import draw_cursor, draw_text
from gui import GUI, GUIControl
from text_edit_buffer import TextEditBuffer


class TextArea(GUIControl):
    @classmethod
    def from_json(cls, json, **kwargs):
        assert(json["class"] == cls.__name__)
        gui = kwargs.get('gui')

        instance = gui.create_control(json["class"], **kwargs)
        instance.set_bounds(*json["bounding_rect"])
        instance.text_buffer.set_text(json["text"])
        return instance


    def __init__(self, row_spacing=18, text_buffer=None, **kwargs):
        # print(f'TextArea.__init__() called')
        super().__init__(**kwargs)
        text = kwargs.get('text', '')
        self.text_buffer = text_buffer or TextEditBuffer(text=text)
        self.is_editable = True
        self.row_spacing = row_spacing
        self.y_scroll = 0
        self.combined_text_texture = None


    def __json__(self):
        json = super().__json__()
        json["class"] = self.__class__.__name__
        json["text"] = self.text_buffer.get_text()
        return json
    

    def handle_event(self, event):

        if event.type == sdl2.SDL_MOUSEWHEEL:
            # Here, we handle the vertical scrolling (event.wheel.y) 
            # We will assume that each "tick" of the mouse wheel corresponds to 3 lines of text
            self.scroll_by(event.wheel.y * -8)
            return True
        
            # for control in self.children:
            #     if isinstance(control, TextArea):
            #         control.scroll_by(scroll_y)
            #         return True

        elif event.type == sdl2.SDL_KEYDOWN:
            cmdPressed = (event.key.keysym.mod & (sdl2.KMOD_LGUI | sdl2.KMOD_RGUI))
            keySymbol = event.key.keysym.sym

            # Cmd+A selects all text
            if keySymbol == sdl2.SDLK_a and (cmdPressed):
                self.text_buffer.set_mark(mark_position=0)
                self.text_buffer.move_point_to_end()
                self.set_needs_redraw()
                return True
            
            if keySymbol == sdl2.SDLK_RETURN:
                if self.text_buffer.get_selection() is not None:
                    self.text_buffer.delete_selection()
                self.text_buffer.insert()
                self.set_needs_redraw()
                return True
            
            # left arrow key
            elif keySymbol == sdl2.SDLK_LEFT:  
                # Is Shift held? Start selection if None
                if event.key.keysym.mod & sdl2.KMOD_SHIFT:  
                    if self.text_buffer.get_selection() is None:
                        self.text_buffer.set_mark()
                else:
                    self.text_buffer.clear_mark()

                # Option/Alt - start of current or previous word
                if event.key.keysym.mod & sdl2.KMOD_ALT:
                    # move to start of word
                    self.text_buffer.move_point_word_left()
                # Cmd - beginning of line
                elif cmdPressed:
                    self.text_buffer.move_point_start_of_line()
                else:
                    self.text_buffer.move_point_left()

                self.set_needs_redraw()    
                return True
            
            # right arrow key
            elif keySymbol == sdl2.SDLK_RIGHT:
                if event.key.keysym.mod & sdl2.KMOD_SHIFT:
                    if self.text_buffer.get_selection() is None:
                        self.text_buffer.set_mark()
                else:
                    self.text_buffer.clear_mark()

                # Option/Alt - start of next word
                if event.key.keysym.mod & sdl2.KMOD_ALT:
                    self.text_buffer.move_point_word_right()
                # Cmd - end of line
                elif cmdPressed:
                    self.text_buffer.move_point_end_of_line()
                else:
                    self.text_buffer.move_point_right()

                self.set_needs_redraw()    
                return True
            
            elif keySymbol == sdl2.SDLK_UP:  # up arrow key
                if cmdPressed:
                    # move to start of buffer
                    self.text_buffer.move_point_to_start()
                else:
                    if event.key.keysym.mod & sdl2.KMOD_SHIFT:
                        if self.text_buffer.get_selection() is None:
                            self.text_buffer.set_mark()
                    else:
                        self.text_buffer.clear_mark()
                    self.text_buffer.move_point_up()

                self.set_needs_redraw()    
                return True
            
            elif keySymbol == sdl2.SDLK_DOWN:  # down arrow key
                if cmdPressed:
                    # move to end of buffer
                    self.text_buffer.move_point_to_end()
                else:
                    if event.key.keysym.mod & sdl2.KMOD_SHIFT:
                        if self.text_buffer.get_selection() is None:
                            self.text_buffer.set_mark()
                    else:
                        self.text_buffer.clear_mark()
                    if self.text_buffer.move_point_down():  
                        # @todo encapsulate in a controller
                        self.scroll_cursor_into_view()

                self.set_needs_redraw()        
                return True
                
            # delete key -- delete char, but send Cmd+Delete to parent
            elif keySymbol == sdl2.SDLK_BACKSPACE and not cmdPressed:
                if self.text_buffer.get_selection() is not None:
                    self.text_buffer.delete_selection()
                else:
                    self.text_buffer.delete_char()

                self.set_needs_redraw()    
                return True
            
            elif keySymbol == sdl2.SDLK_TAB:  # tab key
                # TAB focuses next control
                # Shift+TAB focuses previous control
                # Ctrl+TAB inserts a tab character
                if event.key.keysym.mod & sdl2.KMOD_LCTRL:  # if left Ctrl was held
                    if self.text_buffer.get_selection() is not None:
                        self.text_buffer.delete_selection()
                    self.text_buffer.insert('\t')  # @todo how to access self.text_buffer through current control?

                    self.set_needs_redraw()
                    return True
                
            elif (keySymbol == sdl2.SDLK_SPACE and
                (event.key.keysym.mod & (sdl2.KMOD_LCTRL | sdl2.KMOD_RCTRL))):
                self.text_buffer.set_mark()

                self.set_needs_redraw()
                return True

            # Check for Cmd+V (paste) on macOS
            elif cmdPressed and keySymbol == sdl2.SDLK_v:
                # Get the clipboard text
                clipboard_text = sdl2.SDL_GetClipboardText()
                if clipboard_text:
                    # Convert the clipboard text from bytes to a string
                    text = ctypes.cast(clipboard_text, ctypes.c_char_p).value.decode('utf-8')
                    # Insert the text into the text buffer
                    if self.text_buffer.get_selection() is not None:
                        self.text_buffer.delete_selection()
                    self.text_buffer.insert(text)
                    # Free the clipboard text
                    # sdl2.SDL_free(clipboard_text)

                    self.set_needs_redraw()
                    return True

            # Copy & Cut
            elif cmdPressed and keySymbol == (sdl2.SDLK_c or keySymbol == sdl2.SDLK_x):
                # Is there a selection?
                if self.text_buffer.get_selection() is not None:
                    # Get the selected text
                    start, end = self.text_buffer.get_selection()
                    text = self.text_buffer.get_text()[start:end]
                    
                    # If we're cutting, then delete selection
                    if keySymbol == sdl2.SDLK_x:
                        self.text_buffer.delete_selection()
                else:
                    # Get all the text
                    text = self.text_buffer.get_text()

                    # If we're cutting, then delete all the text
                    if keySymbol == sdl2.SDLK_x:
                        self.text_buffer.set_text('')

                # Set the clipboard text
                sdl2.SDL_SetClipboardText(text.encode('utf-8'))
                self.set_needs_redraw()
                return True
                    
        elif event.type == sdl2.SDL_TEXTINPUT:
            # event.text.text is a bytes object representing a string in UTF-8 encoding
            text = event.text.text.decode('utf-8')
            if self.text_buffer.get_selection() is not None:
                self.text_buffer.delete_selection()
            self.text_buffer.insert(text)
            self.set_needs_redraw()
            return True
    
        return self.parent_handle_event(event)
    

    def set_needs_redraw(self):
        if self.combined_text_texture is not None:
            sdl2.SDL_DestroyTexture(self.combined_text_texture)
            self.combined_text_texture = None


    def draw(self):
        lines = self.text_buffer.get_lines()
        wr = self.get_world_rect()
        x = wr.x
        y = wr.y - self.y_scroll

        # Determine start and end of selection
        selected = self.text_buffer.get_selection()
        if selected is not None:
            i_start, i_end = selected
            sel_rc0 = self.text_buffer.get_row_col(i_start)
            sel_rc1 = self.text_buffer.get_row_col(i_end)

        if self.combined_text_texture is None:
            surf = sdl2.SDL_CreateRGBSurface(0, self.bounding_rect.w, self.bounding_rect.h, 32, 0, 0, 0, 0)

            # Draw the text
            for i, line in enumerate(lines):
                if len(line.strip()) != 0:
                    if selected is not None:
                        # Figure out where the selection starts and ends, line by line since
                        # we can have multiline selections, and we are drawing the text a line
                        # at a time.

                        c_start = None
                        if i < sel_rc0[0]:          # current line is before (not in) selection
                            pass
                        elif i == sel_rc0[0]:       # current line is first line of selection
                            c_start = sel_rc0[1]
                        elif i <= sel_rc1[0]:       # current line is internal to selection or last
                            c_start = 0


                        c_end = None
                        if i > sel_rc1[0]:
                            pass
                        elif i < sel_rc1[0]:
                            c_end = len(line)
                        elif i == sel_rc1[0]:
                            c_end = sel_rc1[1]

                        draw_text(self.renderer, self.font_manager, 
                                line, 
                                wr.x, y, bounding_rect=wr,
                                dst_surface=surf, 
                                selection_start=c_start, selection_end=c_end)
                    else:
                        draw_text(self.renderer, self.font_manager, line, wr.x, y, bounding_rect=wr, dst_surface=surf)

                y += self.row_spacing

            self.combined_text_texture = sdl2.SDL_CreateTextureFromSurface(self.renderer.sdlrenderer, surf)
            sdl2.SDL_FreeSurface(surf)

        assert(self.combined_text_texture is not None)
        sdl2.SDL_RenderCopy(self.renderer.sdlrenderer, self.combined_text_texture, None, wr)

        # Draw the bounding rectangle after all text has been drawn
        # Save the current color
        r, g, b, a = sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8()
        sdl2.SDL_GetRenderDrawColor(self.renderer.sdlrenderer, r, g, b, a)
        old_color = (r.value, g.value, b.value, a.value)

        # Set the new color
        r, g, b = (0, 127, 255) if self.has_focus() else (100, 100, 100)
        sdl2.SDL_SetRenderDrawColor(self.renderer.sdlrenderer, r, g, b, 255)

        # Draw the bounding rectangle
        sdl2.SDL_RenderDrawRect(self.renderer.sdlrenderer, wr)

        # Reset to the old color
        sdl2.SDL_SetRenderDrawColor(self.renderer.sdlrenderer, old_color[0], old_color[1], old_color[2], old_color[3])

        # Draw cursor
        if self.has_focus():
            row, col = self.text_buffer.get_row_col(self.text_buffer.get_point())
            line = lines[row]
            if line is not None and col is not None:
                draw_cursor(self.renderer, self.font_manager, self.text_buffer, self.row_spacing, wr.x, wr.y, wr, self.y_scroll)


    def scroll_by(self, dy):
        self.y_scroll = max(0, self.y_scroll + dy)  # adjust y_scroll by dy
        self.set_needs_redraw()


    def is_cursor_on_last_line(self, text_buffer):
        row, _ = text_buffer.get_row_col(text_buffer.get_point())
        return row >= (self.bounding_rect.h / self.row_spacing + self.y_scroll)


    def scroll_cursor_into_view(self):
        if self.is_cursor_on_last_line(self.text_buffer):
            self.scroll_by(self.row_spacing)


GUI.register_control_type("TextArea", TextArea)
