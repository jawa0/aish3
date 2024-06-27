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


import ctypes
import sdl2
from sdl2.ext.ttf import FontTTF
from sdl2.sdlttf import TTF_FontHeight
from draw import draw_cursor, draw_text, set_color
from gui import GUI, GUIControl
from gui.fonts import FontRegistry
import os
from text_edit_buffer import TextEditBuffer
import queue
from platform_utils import is_cmd_pressed


class TextArea(GUIControl):
    @classmethod
    def from_json(cls, json, **kwargs):
        assert(json["class"] == cls.__name__)
        kwargs = super(TextArea, cls)._enrich_kwargs(json, **kwargs)

        gui = kwargs.get('gui')

        instance = gui.create_control(json["class"], **kwargs)
        instance.set_bounds(*json["bounding_rect"])
        instance.set_text(json["text"])
        return instance


    def __init__(self, row_spacing=18, text_buffer=None, **kwargs):
        """
        Initializes a TextArea instance, which is a GUI control for displaying and editing text.

        Inherits from GUIControl and accepts all its keyword arguments, along with some additional specific to TextArea.

        Args:
            row_spacing (int): The vertical spacing between rows of text. Default is 18.
            text_buffer (TextEditBuffer, optional): The text buffer to be used by the TextArea. 
                If None, a new TextEditBuffer is created. Default is None.

        Keyword Args:
            text (str): Initial text for the TextArea. Default is an empty string.
            can_focus (bool): Indicates if the control can gain focus. Inherited from GUIControl. Default is True.
            x (int): Inherited from GUIControl (see GUIControl.__init__()). Default is 0.
            y (int):  Inherited from GUIControl (see GUIControl.__init__()). Default is 0.
            w (int): The width of the control. Inherited from GUIControl. Default is 20.
            h (int): The height of the control. Inherited from GUIControl. Default is 20.
            saveable (bool): Indicates if the control's state is saveable. Inherited from GUIControl. Default is True.
            gui (Object): Reference to the GUI object. Inherited from GUIControl. Default is None.
            renderer (Object): Reference to the renderer object. Inherited from GUIControl. 
                Default is gui.renderer if gui is not None, else None.
            font_manager (Object): Reference to the font manager object. Inherited from GUIControl. 
                Default is gui.font_manager if gui is not None, else None.
            draw_bounds (bool): Indicates if bounds should be drawn. Inherited from GUIControl. Default is False.
            draggable (bool): Indicates if the control is draggable. Inherited from GUIControl. Default is False.
            visible (bool): Indicates if the control is visible. Inherited from GUIControl. Default is True.
            screen_relative (bool): Indicates if the control's position is relative to the screen. 
                Inherited from GUIControl. Default is False.

        Calls the superclass initializer and sets up the TextArea specific attributes.
        """
        # print(f'TextArea.__init__() called')
        super().__init__(**kwargs)
        text = kwargs.get('text', '')
        self.text_buffer = text_buffer or TextEditBuffer(text=text)
        self.is_editable = True
        self.row_spacing = row_spacing
        self.y_scroll = 0
        self.x_scroll = 0
        self.combined_text_texture = None
        self._was_last_event_mousewheel = False
        self.input_q = None
        self._resizing = False
        self._resize_start_pos = None
        self._resize_start_size = None
        self._resize_edge = None

        # @hack @todo FontManager is deprecated. Should use sdl2.ext.ttf.FontTTF
        fm = FontRegistry().get_fontmanager(self.font_descriptor)
        assert(fm is not None)
        font_size_px = fm.size

        # print('__file__:', __file__)
        app_path = os.path.dirname(os.path.abspath(__file__))  # @todo DRY if this file location changes, then we'll need to update computation of app_path
        # print(f'app_path: {app_path}')

        font_filepath = os.path.abspath(os.path.join(app_path, "res/fonts/FiraCode-Regular.ttf"))
        # print(f'font_filepath: {font_filepath}')

        font = FontTTF(font_filepath, font_size_px, (255, 255, 255))
        ttf_font = font.get_ttf_font()
        line_height_px = TTF_FontHeight(ttf_font)
        self.row_spacing = line_height_px
        del ttf_font
        font.close()


    def __json__(self):
        json = super().__json__()
        if json is not None:  # Could be None for a non-saveable control, on save. @todo DRY every derived class will have to do this. Boo.
            json["class"] = self.__class__.__name__
            json["text"] = self.text_buffer.get_text()
        return json
    
    
    def _change_focus(self, am_getting_focus: bool) -> bool:
        # @hack @todo make this optional
        if am_getting_focus:
            self.input_q = self.gui.session.subscribe("transcribed_text")
        else:
            self.input_q = None

        return super()._change_focus(am_getting_focus)
    

    def get_text(self) -> str:
        return self.text_buffer.get_text()
    
    
    def set_text(self, text: str) -> None:
        self.text_buffer.set_text(text)


    def on_update(self, dt):
        if self.input_q is not None:
            try:
                while True:
                    (text, is_final) = self.input_q.get_nowait()
                    if len(text) == 0:
                        continue

                    # self.set_text(text)

                    # Don't just overwrite text, but insert it at the current cursor position
                    # However, delete any current selection. We'll use this as a way to 
                    # update partial text results.
                    if self.text_buffer.get_selection() is not None:
                        self.text_buffer.delete_selection()
                    
                    # Cause the new text we insert to be selected, so if we get new partial 
                    # text, then it will overwrite the old partial text by overwriting the
                    # selection.

                    if not is_final:
                        self.text_buffer.set_mark()
                    else:
                        text += '\n'
                        self.text_buffer.clear_mark()
                    self.text_buffer.insert(text)
                    
            except queue.Empty:
                pass
            finally:
                self.set_needs_redraw()
        


    def handle_event(self, event):
        # @note: I don't like that each derived class has to remember to do this
        if self._pre_handle_event(event):
            return True

        current_was_last_event_mousewheel = self._was_last_event_mousewheel
        self._was_last_event_mousewheel = False

        if event.type == sdl2.SDL_MOUSEBUTTONDOWN:
            if event.button.button == sdl2.SDL_BUTTON_LEFT:
                mx, my = event.button.x, event.button.y
                wx, wy = self.gui.view_to_world(mx, my)
                if self._is_on_edge(wx, wy):
                    self._resizing = True
                    self._resize_start_pos = (wx, wy)
                    self._resize_start_size = self.get_size()
                    self._resize_edge = self._get_edge(wx, wy)
                    return True

        elif event.type == sdl2.SDL_MOUSEBUTTONUP:
            if event.button.button == sdl2.SDL_BUTTON_LEFT and self._resizing:
                self._resizing = False
                self._resize_start_pos = None
                self._resize_start_size = None
                self._resize_edge = None
                return True

        elif event.type == sdl2.SDL_MOUSEMOTION:
            if self._resizing:
                mx, my = event.motion.x, event.motion.y
                wx, wy = self.gui.view_to_world(mx, my)
                self._resize(wx, wy)
                return True

        elif event.type == sdl2.SDL_MOUSEWHEEL:
            # Scroll this TextArea, but only if it has focus.

            GAIN = 8
            dy = -event.wheel.y * GAIN

            if self.has_focus():
                self.scroll_by(dy=dy)
                return True
        
        elif event.type == sdl2.SDL_KEYDOWN:
            cmdPressed: bool = is_cmd_pressed(event)
            keySymbol = event.key.keysym.sym

            # Esc: If if there is a text selection, then clear selection.
            if keySymbol == sdl2.SDLK_ESCAPE:
                if self.text_buffer.get_selection() is not None:
                    self.text_buffer.clear_mark()
                    self.set_needs_redraw()
                    return True
                
            # Cmd+A selects all text
            elif keySymbol == sdl2.SDLK_a and (cmdPressed):
                self.text_buffer.set_mark(mark_position=0)
                self.text_buffer.move_point_to_end()
                self.set_needs_redraw()
                return True
            
            elif keySymbol == sdl2.SDLK_RETURN and not cmdPressed:
                # @todo: add an option to not capture RETURN, so that
                # we can make specialized text-based controls that do
                # stuff when you press RETURN.
                
                if self.text_buffer.get_selection() is not None:
                    self.text_buffer.delete_selection()
                self.text_buffer.insert()
                self.set_needs_redraw()
                return True
            
            # Cmd+Backspace/Delete delete the focused control, but only if
            # it is at the top-level of the GUI, not part of some other
            # container.

            elif cmdPressed and keySymbol == sdl2.SDLK_BACKSPACE:
                focused_control = self.gui.get_focus()
                if focused_control is self and focused_control.parent == self.gui.content():
                    self.parent.remove_child(self)
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
                    self.text_buffer.move_point_down()

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
                        self.set_text('')

                # Set the clipboard text
                sdl2.SDL_SetClipboardText(text.encode('utf-8'))
                self.set_needs_redraw()
                return True
                    
        elif event.type == sdl2.SDL_TEXTINPUT:
            # event.text.text is a bytes object representing a string in UTF-8 encoding
            text = event.text.text.decode('utf-8')
            
            # @hack to get command console to stop inserting its wakeup key ~ into
            # the textbuffer
            if text == '~' or text == "`":
                return True
            
            if self.text_buffer.get_selection() is not None:
                self.text_buffer.delete_selection()
            self.text_buffer.insert(text)
            self.set_needs_redraw()
            return True
    
        # We reached the end of our events, so don't clear _was_last_event_mousewheel
        self._was_last_event_mousewheel = current_was_last_event_mousewheel

        return self.parent_handle_event(event)
    

    def _is_on_edge(self, wx, wy):
        rect = self.get_world_rect()
        leeway = 1
        if (rect.x - leeway <= wx <= rect.x + rect.w + leeway and
            rect.y - leeway <= wy <= rect.y + rect.h + leeway):
            return True
        return False

    def _get_edge(self, wx, wy):
        rect = self.get_world_rect()
        edges = []
        if abs(wx - rect.x) <= 1:
            edges.append('left')
        if abs(wx - (rect.x + rect.w)) <= 1:
            edges.append('right')
        if abs(wy - rect.y) <= 1:
            edges.append('top')
        if abs(wy - (rect.y + rect.h)) <= 1:
            edges.append('bottom')
        return edges

    def _resize(self, wx, wy):
        start_w, start_h = self._resize_start_size
        start_x, start_y = self._resize_start_pos
        dx = wx - start_x
        dy = wy - start_y

        new_w = start_w
        new_h = start_h

        if 'right' in self._resize_edge:
            new_w = max(20, start_w + dx)
        if 'bottom' in self._resize_edge:
            new_h = max(20, start_h + dy)
        if 'left' in self._resize_edge:
            new_w = max(20, start_w - dx)
            self.set_position(self.bounding_rect.x + dx, self.bounding_rect.y)
        if 'top' in self._resize_edge:
            new_h = max(20, start_h - dy)
            self.set_position(self.bounding_rect.x, self.bounding_rect.y + dy)

        self.set_size(new_w, new_h)
        leeway = 1
        if (rect.x - leeway <= wx <= rect.x + rect.w + leeway and
            rect.y - leeway <= wy <= rect.y + rect.h + leeway):
            return True
        return False

    def _get_edge(self, wx, wy):
        rect = self.get_world_rect()
        edges = []
        if abs(wx - rect.x) <= 1:
            edges.append('left')
        if abs(wx - (rect.x + rect.w)) <= 1:
            edges.append('right')
        if abs(wy - rect.y) <= 1:
            edges.append('top')
        if abs(wy - (rect.y + rect.h)) <= 1:
            edges.append('bottom')
        return edges

    def _resize(self, wx, wy):
        start_w, start_h = self._resize_start_size
        start_x, start_y = self._resize_start_pos
        dx = wx - start_x
        dy = wy - start_y

        new_w = start_w
        new_h = start_h

        if 'right' in self._resize_edge:
            new_w = max(20, start_w + dx)
        if 'bottom' in self._resize_edge:
            new_h = max(20, start_h + dy)
        if 'left' in self._resize_edge:
            new_w = max(20, start_w - dx)
            self.set_position(self.bounding_rect.x + dx, self.bounding_rect.y)
        if 'top' in self._resize_edge:
            new_h = max(20, start_h - dy)
            self.set_position(self.bounding_rect.x, self.bounding_rect.y + dy)

        self.set_size(new_w, new_h)


    def set_needs_redraw(self):
        if self.combined_text_texture is not None:
            sdl2.SDL_DestroyTexture(self.combined_text_texture)
            self.combined_text_texture = None
            if not self._was_last_event_mousewheel:
                self.scroll_cursor_into_view()


    def set_size(self, w, h):
        super().set_size(w, h)

        # Mark dirty or else the cached text texture will be stretched
        # to the new size.
        self.set_needs_redraw()


    def _draw_bounds(self, vr):
        # Draw the bounding rectangle after all text has been drawn
        # Save the current color
        r, g, b, a = sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8()
        sdl2.SDL_GetRenderDrawColor(self.renderer.sdlrenderer, r, g, b, a)
        old_color = (r.value, g.value, b.value, a.value)

        # Set the new color
        if self.pulse_busy:
            r, g, b = (255, 0, 0)
        elif self.has_focus():
            r, g, b = (0, 127, 255)
        else:
            r, g, b = (100, 100, 100)
        sdl2.SDL_SetRenderDrawColor(self.renderer.sdlrenderer, r, g, b, 255)

        # Draw the bounding rectangle
        sdl2.SDL_RenderDrawRect(self.renderer.sdlrenderer, vr)

        # Reset to the old color
        sdl2.SDL_SetRenderDrawColor(self.renderer.sdlrenderer, old_color[0], old_color[1], old_color[2], old_color[3])


    def draw(self):
        lines = self.text_buffer.get_lines()
        
        vr = self.get_view_rect()

        vx = vr.x - self.x_scroll
        vy = vr.y - self.y_scroll

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

                        draw_text(self.renderer, self.font_descriptor, 
                                line, 
                                vx, vy, bounding_rect=vr,
                                dst_surface=surf, 
                                selection_start=c_start, selection_end=c_end)
                    else:
                        draw_text(self.renderer, self.font_descriptor, line, vx, vy, bounding_rect=vr, dst_surface=surf)

                vy += self.row_spacing

            self.combined_text_texture = sdl2.SDL_CreateTextureFromSurface(self.renderer.sdlrenderer, surf)
            sdl2.SDL_FreeSurface(surf)

        assert(self.combined_text_texture is not None)
        sdl2.SDL_RenderCopy(self.renderer.sdlrenderer, self.combined_text_texture, None, vr)

        self._draw_bounds(vr)

        # Draw cursor
        if self.has_focus():
            row, col = self.text_buffer.get_row_col(self.text_buffer.get_point())
            line = lines[row]
            if line is not None and col is not None:
                old_color = set_color(self.renderer, (255, 255, 255, 255))
                draw_cursor(self.renderer, self.font_descriptor, self.text_buffer, self.row_spacing, vr.x, vr.y, vr, self.x_scroll, self.y_scroll)
                set_color(self.renderer, old_color)


    def scroll_by(self, dx=0, dy=0):
        self.y_scroll = max(0, self.y_scroll + dy)  # adjust y_scroll by dy
        self.x_scroll = max(0, self.x_scroll + dx)  # adjust x_scroll by dx
        self.set_needs_redraw()


    def scroll_cursor_into_view(self):
        # Where is the cursor?
        wr = self.get_world_rect()
        x_cursor, y_cursor = draw_cursor(self.renderer, self.font_descriptor, 
                                         self.text_buffer, 
                                         self.row_spacing, 
                                         wr.x, wr.y, wr, 
                                         self.x_scroll, self.y_scroll,
                                         dont_draw_just_calculate=True)  # !!! @todo wtf? @hack
        
        
        cursor_bottom_y = y_cursor + self.row_spacing
        rect_bottom_y = wr.y + wr.h
        # print(f'cursor_bottom_y: {cursor_bottom_y}, rect_bottom_y: {rect_bottom_y}')

        if cursor_bottom_y >= rect_bottom_y:
            y_correction = cursor_bottom_y - rect_bottom_y
            # print(f'y_correction: {y_correction}')
            self.scroll_by(dy=y_correction)
        elif y_cursor < wr.y:
            y_correction = y_cursor - wr.y
            # print(f'y_correction: {y_correction}')
            self.scroll_by(dy=y_correction)

        x_pad = 20  # Arbitrary @note this is really an input sensitivy setting
        if x_cursor > wr.x + wr.w - x_pad:
            x_correction = x_cursor - (wr.x + wr.w - x_pad)
            self.scroll_by(dx=x_correction)
        elif x_cursor < wr.x + x_pad:
            x_correction = x_cursor - (wr.x + x_pad)
            self.scroll_by(dx=x_correction)


GUI.register_control_type("TextArea", TextArea)
