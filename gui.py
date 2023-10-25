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
import datetime
import json
import logging
import pytz
from rect_utils import rect_union
import sdl2
from tzlocal import get_localzone
from gui_layout import ColumnLayout
from gui_focus import FocusRing
import weakref
import os
from voice_out import VoiceOut
from voice_wakeup import PhraseListener
from transcribe_audio import VoiceTranscriber


#===============================================================================
class GUI:
    VOICE_IN_STATE_NOT_LISTENING = 0
    VOICE_IN_STATE_LISTENING_FOR_WAKEWORD = 1
    VOICE_IN_STATE_LISTENING_FOR_SPEECH = 2


    _factories = {}

    @classmethod
    def register_control_type(cls, class_name, control_class):
        cls._factories[class_name] = control_class


    @classmethod
    def control_class(cls, class_name):
        return cls._factories.get(class_name, None)
    

    def create_control(self, class_name, **kwargs):
        cls = self.__class__
        control_class = cls.control_class(class_name)
        if control_class:
            if not "gui" in kwargs:
                kwargs["gui"] = self
            gui = kwargs["gui"]

            if not "renderer" in kwargs:
                kwargs["renderer"] = gui.renderer
            if not "font_manager" in kwargs:
                kwargs["font_manager"] = gui.font_manager

            return control_class(**kwargs)
        else:
            return None


    def __init__(self, renderer, font_manager, workspace_filename="aish_workspace.json", client_session=None):        
        assert(client_session is not None)
        self.session = client_session
        self.session.gui = weakref.ref(self)

        self.renderer = renderer
        self.font_manager = font_manager

        assert(self.renderer)
        assert(self.font_manager)

        self._content = GUIContainer(gui=self, renderer=self.renderer, font_manager=self.font_manager)
        assert(self._content.focusRing is not None)
        self.focus_stack = []
        self.push_focus_ring(self._content.focusRing)
        
        # May be self.content or any depth of descendant of self.content
        self._focused_control = None

        self._strokes = {}
        self._content_pan = (0, 0)
        self._drag_control = None

        self.workspace_filename = workspace_filename
        
        self.load()

        self._voice_out = VoiceOut(on_speech_done=[self._on_speech_done])
        self._saying_text = None
        self._next_texts_to_say = []

        self._voice_in = VoiceTranscriber(session=self.session)
        self._voice_wakeup = None

        self._voice_in_state = GUI.VOICE_IN_STATE_LISTENING_FOR_WAKEWORD  # trigger start in update()


    class JSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if hasattr(obj, '__json__'):
                return obj.__json__()
            return json.JSONEncoder.default(self, obj)


    def __json__(self):
        return {"class": self.__class__.__name__, 
                "content": self._content.__json__()}
    

    def _start_listening_wakeword(self):
        assert(self._voice_wakeup is None)

        self._voice_wakeup = PhraseListener(detected_callback=self._on_voice_wakeup)
        self._voice_in_state = GUI.VOICE_IN_STATE_LISTENING_FOR_WAKEWORD
        self._voice_wakeup.start()
        logging.info('Listening for wakeup phrase.')

        if self.listening_indicator is not None:
            self.listening_indicator.set_text("Listening for WAKEUP")


    def _stop_listening_wakeword(self):
        assert(self._voice_wakeup is not None)
        self._voice_wakeup.stop()
        self._voice_wakeup = None

        if self.listening_indicator is not None:
            self.listening_indicator.set_text("")


    def content(self):
        return self._content
    
    
    def session(self):
        return self.session
    

    def on_quit(self):
        # Do depth-first traversal
        q = [self.content()]
        while len(q) > 0:
            control = q.pop()
            if hasattr(control, "children"):
                q.extend(control.children)
            if hasattr(control, "_on_quit"):
                control._on_quit()


    def say(self, text):
        logging.debug(f'GUI.say({text})')
        return

        if self._saying_text is None:
            self._saying_text = text

            if self._voice_in_state == GUI.VOICE_IN_STATE_LISTENING_FOR_SPEECH:
                self._voice_in.stop_recording()
            elif self._voice_in_state == GUI.VOICE_IN_STATE_LISTENING_FOR_WAKEWORD and self._voice_wakeup is not None:
                self._voice_wakeup.stop()
                self._voice_wakeup = None

            self._voice_out.say(text)
        else:
            self._next_texts_to_say.append(text)


    def _on_speech_done(self):
        self._saying_text = None

        # If we were actively listening before text_buffer_set_textsaying speech, then return to active listening...
        if len(self._next_texts_to_say) == 0 and \
            self._voice_in_state == GUI.VOICE_IN_STATE_LISTENING_FOR_SPEECH and \
            not self._voice_in.is_recording():

            self._voice_in.start_recording()

        # If we were waiting for the wakeup phrase, then go back to doing that
        elif len(self._next_texts_to_say) == 0 and \
            self._voice_in_state == GUI.VOICE_IN_STATE_LISTENING_FOR_WAKEWORD and \
            self._voice_wakeup is None:

            self._start_listening_wakeword()


    def _on_voice_wakeup(self):
        logging.info(f'WAKEUP. Stopping voice wakeup. Starting active listening.')
        self._stop_listening_wakeword()

        # self.say("Yes?")

        self._voice_in_state = GUI.VOICE_IN_STATE_LISTENING_FOR_SPEECH
        self._voice_in.start_recording()


    def handle_event(self, event):
        handled = False
        if self._focused_control:
            handled = self._focused_control.handle_event(event)

        if not handled:    
            if event.type == sdl2.SDL_KEYDOWN:
                return self.handle_keydown(event)
            
            elif event.type == sdl2.SDL_MOUSEBUTTONDOWN:
                # Do we have a stroke for this button?
                if event.button.button not in self._strokes:
                    # We do not.  Add this event to the stroke.
                    stroke = [(event.button.x, event.button.y)]                    
                    self._strokes[event.button.button] = stroke
                    # print(f"STROKE (button {event.button.button}) start at {stroke[0]}")

                    # If it's the left mouse button, then check for a hit on a control.
                    if event.button.button == sdl2.SDL_BUTTON_LEFT:
                        hit_control = self.check_hit(event.button.x, event.button.y)
                        if hit_control:
                            self._drag_control = hit_control
                    return True

            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                # Do we have a stroke for this button?
                if event.button.button in self._strokes:
                    # We do.  Remove this stroke.
                    del self._strokes[event.button.button]
                    # print(f"STROKE (button {event.button.button}) end")

                    # If it's the let mouse button, then check if we're dragging and release drag.
                    if self._drag_control and event.button.button == sdl2.SDL_BUTTON_LEFT:
                        self._drag_control = None
                    return True

            elif event.type == sdl2.SDL_MOUSEMOTION:
                # Do we have a stroke for this button?
                # @bug @todo only seems to work for L button
                # Maybe macOS two finger swipe is showing up as a trackpad gesture that gets handled first?
                if event.button.button in self._strokes:
                    # print(f"STROKE (button {event.button.button}) motion to {(event.motion.x, event.motion.y)}")

                    xy0 = self._strokes[event.button.button][-1]
                    self._strokes[event.button.button].append((event.motion.x, event.motion.y))
                    xy1 = self._strokes[event.button.button][-1]

                    dx = xy1[0] - xy0[0]
                    dy = xy1[1] - xy0[1]

                    if self._drag_control:
                        new_r = sdl2.SDL_Rect(self._drag_control.bounding_rect.x + dx,
                                               self._drag_control.bounding_rect.y + dy,
                                               self._drag_control.bounding_rect.w,
                                               self._drag_control.bounding_rect.h)
                        self._drag_control.bounding_rect = new_r
                    else:
                        self._content_pan = (self._content_pan[0] + dx, self._content_pan[1] + dy)

                    return True
                
        return handled
    

    def handle_keydown(self, event):
        wr = self.content().get_world_rect()

        keySym = event.key.keysym.sym
        cmdPressed = event.key.keysym.mod & (sdl2.KMOD_LGUI | sdl2.KMOD_RGUI)

        if cmdPressed:
            # Cmd+S saves GUI
            if keySym == sdl2.SDLK_s:
                self.save()
                return True  # event was handled
            # Cmd+L loads GUI
            if keySym == sdl2.SDLK_l:
                self.load()
                return True  # event was handled
            
            # Cmd+N add new LLM chat
            if keySym == sdl2.SDLK_n:
                x = ctypes.c_int()
                y = ctypes.c_int()                
                sdl2.mouse.SDL_GetMouseState(ctypes.byref(x), ctypes.byref(y))

                self.content().sizeToChildren()
                chat = self.create_control("LLMChatContainer", x=x.value-wr.x, y=y.value-wr.y)
                self.content().add_child(chat)
                # self.set_focus(chat)
                return True  # event was handled

            # Cmd+R say something
            if keySym == sdl2.SDLK_r:
                self.say("One, one-thousand. Two one-thousand. Three one-thousand. Do not call logging or print from this function! It's time-critical! You've touched upon a fascinating aspect of language models and artificial intelligence in general. While language models like mine lack true understanding and consciousness, they can indeed produce remarkably coherent and contextually relevant text, often to the point of surprising users.")
                # self.say("Listening")
                

                return True  # event was handled
            
            # Cmd+T creaes a new TextArea
            if keySym == sdl2.SDLK_t:
                x = ctypes.c_int()
                y = ctypes.c_int()                
                sdl2.mouse.SDL_GetMouseState(ctypes.byref(x), ctypes.byref(y))

                self.content().sizeToChildren()
                textArea = self.create_control("TextArea", w=160, h=80, x=x.value-wr.x, y=y.value-wr.y)
                self.content().add_child(textArea)
                self.set_focus(textArea)
                return True

            if keySym == sdl2.SDLK_RETURN:
                logging.info('Command: toggle recording')

                # Toggle active listening...

                if self._voice_in_state != GUI.VOICE_IN_STATE_LISTENING_FOR_SPEECH:
                    logging.debug('GUI is idle or listening for wakeword.')

                    if self._voice_in_state == GUI.VOICE_IN_STATE_LISTENING_FOR_WAKEWORD:
                        logging.debug('GUI is listening for wakeword. Stopping voice wakeup.')
                        self._stop_listening_wakeword()

                    logging.info(f'Starting active listening.')
                    self._voice_in.start_recording()
                    self._voice_in_state = GUI.VOICE_IN_STATE_LISTENING_FOR_SPEECH

                elif self._voice_in_state == GUI.VOICE_IN_STATE_LISTENING_FOR_SPEECH:
                    logging.info(f'GUI is listening for speech. Stopping active listening.')
                    self._voice_in.stop_recording()
                    self._voice_in_state = GUI.VOICE_IN_STATE_NOT_LISTENING

                    self._start_listening_wakeword()
                    return True
                
        if keySym == sdl2.SDLK_RETURN:
            # Focus down into FocusRing of currently focused control...
            focused = self._focused_control
            if focused:
                if hasattr(focused, "focusRing"):
                    self.push_focus_ring(focused.focusRing)
                    focused.focusRing.focus_first()
                    return True

        elif keySym == sdl2.SDLK_ESCAPE:
            # Focus up into previous FocusRing on stack
            self.pop_focus_ring()

            oldFocusRing = self.get_focus_ring()
            assert(oldFocusRing is not None)
            oldFocusRing.focus(oldFocusRing.get_focus())
            return True

        elif keySym == sdl2.SDLK_TAB:
            # TAB focuses next control in focus ring
            # Shift+TAB focuses previous control

            focusRing = self.get_focus_ring()
            assert(focusRing is not None)

            if event.key.keysym.mod & sdl2.KMOD_LCTRL:
                # Ctrl+TAB inserts a tab character - we handle this in the TextArea class
                pass
            else:
                if event.key.keysym.mod & sdl2.KMOD_SHIFT:  # if shift was also held
                    if focusRing.focus_previous():
                        return True  # event was handled
                else:
                    if focusRing.focus_next():
                        return True  # event was handled


    def update(self, dt):
        #
        # Should we enable or disable wake word listening?
        #
        
        if self._voice_in_state != GUI.VOICE_IN_STATE_LISTENING_FOR_WAKEWORD and self._voice_wakeup is not None:
            self._stop_listening_wakeword()

        if self._voice_in_state == GUI.VOICE_IN_STATE_LISTENING_FOR_WAKEWORD and self._voice_wakeup is None:
            self._start_listening_wakeword()

        # Update voice wakeup, if it's active
        if self._voice_in_state == GUI.VOICE_IN_STATE_LISTENING_FOR_WAKEWORD and self._voice_wakeup is not None:
            self._voice_wakeup.update()

        # 
        # Voice transcription
        #
        
        # Update visibility of voice transcript window...
        if self._voice_in_state == GUI.VOICE_IN_STATE_LISTENING_FOR_SPEECH:
            if self.voice_transcript is not None and \
                not self.voice_transcript._visible:

                self.voice_transcript.text_buffer.set_text("")  # @hack
                self.voice_transcript._visible = True
        
        elif self._voice_in_state != GUI.VOICE_IN_STATE_LISTENING_FOR_SPEECH and \
            self.voice_transcript is not None and \
            self.voice_transcript._visible:

            self.voice_transcript._visible = False


        # Do we have queued text to say?
        if self._saying_text is None and len(self._next_texts_to_say) > 0:
            self._saying_text = self._next_texts_to_say.pop(0)
            self._voice_out.say(self._saying_text)

        # Voice In
        if self._voice_in_state == GUI.VOICE_IN_STATE_LISTENING_FOR_SPEECH and self._voice_in is not None:
            
            self._voice_in.update()

            if self.listening_indicator is not None:
                voice_indicator_text = "LISTENING..."
                if self.listening_indicator.get_text() != voice_indicator_text:
                    self.listening_indicator.set_text(voice_indicator_text)

            # Stop voice in?
            if self._voice_in._should_stop and self._voice_in.is_recording():
                self._voice_in.stop_recording()
                logging.debug(f'Just called self._voice_in.stop_recording() and self._voice_in is {self._voice_in}')
                self._voice_in._should_stop = False

                self._voice_in_state = GUI.VOICE_IN_STATE_LISTENING_FOR_WAKEWORD
                # self.say("Okay")

        # Update components
        for c in self.content():
            if hasattr(c, 'on_update'):
                c.on_update(dt)


    def draw(self):
        if self._content:
            self._content.draw()

        # # @debug Draw strokes
        # for stroke in self._strokes:
        #     points = self._strokes[stroke]
            
        #     # Convert the list of points to a ctypes array of SDL_Point structures
        #     point_array = (sdl2.SDL_Point * len(points))(*points)

        #     if len(points) > 1:
        #         sdl2.SDL_SetRenderDrawColor(self.renderer.sdlrenderer, 255, 0, 0, 255)
        #         sdl2.SDL_RenderDrawLines(self.renderer.sdlrenderer, point_array, len(points))
        #         sdl2.SDL_SetRenderDrawColor(self.renderer.sdlrenderer, 0, 0, 0, 255)


    def push_focus_ring(self, focusRing):
        assert(focusRing is not None)
        self.focus_stack.append(focusRing)


    def pop_focus_ring(self):
        if len(self.focus_stack) > 1:
            return self.focus_stack.pop()
        return None


    def get_focus_ring(self):
        return self.focus_stack[-1] if len(self.focus_stack) > 0 else None


    def get_focus(self):
        return self._focused_control
    
    
    def set_focus(self, control, focus_it=True):
        assert(control is not None and isinstance(control, GUIControl))

        if focus_it:
            # Can't focus on a control that can't be focused.
            # @note @todo shouldn't this happen automatically?

            if not control.can_focus:
                return False
        
            # If another control has focus, then remove focus from it.
            if focus_it and \
                self._focused_control is not None and \
                self._focused_control != control:

                    self._focused_control._set_focus(False)
                    self._focused_control = None

            self._focused_control = control
            
            # containing_ring = control.containing_focus_ring()
            # if containing_ring is not None:
            #     currentFocusRing = self.focus_stack[-1] if len(self.focus_stack) > 0 else None

            #     if currentFocusRing != containing_ring:
            #         self.focus_stack.append(containing_ring)
                    
            return self._focused_control._set_focus(True)
        else:
            # Make sure it's not focused.
            if self._focused_control == control:
                self._focused_control = None
            return control._set_focus(False)
        

    def check_hit(self, x, y):
        p = sdl2.SDL_Point(x, y)
        
        q = list(self.content())
        while len(q) > 0:
            child = q.pop()
            if sdl2.SDL_PointInRect(p, child.get_world_rect()):
                return child
            else:
                if hasattr(child, "children"):
                    q.extend(child.children)
            # print(len(q))
        return None
    

    def get_ancestor_chain(self, control):
        chain = []
        while control is not None:
            chain.append(control)
            control = control.parent
        chain.reverse()
        chain.pop()  # Don't want the control, itself
        return chain
    

    def save(self):        
        utc_now = datetime.datetime.now(pytz.utc)
        local_timezone = get_localzone()
        local_now = utc_now.astimezone(local_timezone)

        logging.info("Saving GUI...")
        with open(self.workspace_filename, "w") as f:
            gui_json = {
                "saved_at_utc": utc_now.isoformat(),
                "saved_at_local": local_now.isoformat(),
                "gui": self.__json__()
            }
            json.dump(gui_json, f, indent=2, cls=GUI.JSONEncoder)
        logging.info("GUI saved.")


    def load(self):
        bak_content = self._content
        bak_focused_control = self._focused_control
        self.focus_stack = []

        logging.info("Loading GUI...")
        try:
            with open(self.workspace_filename, "r") as f:
                gui_json = json.load(f)
                content_json = gui_json["gui"]["content"]
                gui_class = GUI.control_class(content_json["class"])
                self._content = gui_class.from_json(content_json, gui=self, renderer=self.renderer, font_manager=self.font_manager)
                self.push_focus_ring(self._content.focusRing)

                focusRing = self.get_focus_ring()
                assert(focusRing is not None)
                focusRing.focus_first()

        except Exception as e:
            logging.error("Error loading GUI. Exception: ", str(e))
            self._content = bak_content
            self._focused_control = bak_focused_control
            return False
        
        logging.info("GUI loaded.")
        return True


    def voice_input_available(self):
        """Is speech input available?"""
        return os.getenv("ASSEMBLYAI_API_KEY") is not None
    

#===============================================================================
class GUIControl:
    def __init__(self, can_focus=True, x=0, y=0, w=20, h=20, **kwargs):
        self.gui = kwargs.get('gui')
        self.renderer = kwargs.get('renderer')
        self.font_manager = kwargs.get('font_manager')
        self.draw_bounds = kwargs.get('draw_bounds', False)
        self._draggable = kwargs.get('draggable', False)
        self._visible = kwargs.get('visible', True)
        self._screen_relative = kwargs.get('screen_relative', False)

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
            wr = sdl2.SDL_Rect(wr.x + self.gui._content_pan[0],
                           wr.y + self.gui._content_pan[1],
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


#===============================================================================
class GUIContainer(GUIControl):
    @classmethod
    def from_json(cls, json, **kwargs):
        assert(json["class"] == cls.__name__)
        gui = kwargs.get('gui')

        instance = gui.create_control(json["class"], **kwargs)
        instance.set_bounds(*json["bounding_rect"])

        for child_json in json["children"]:
            child_class = GUI.control_class(child_json["class"])
            instance.add_child(child_class.from_json(child_json, **kwargs))

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
        json["class"] = self.__class__.__name__
        json["layout"] =  self.layout.__class__.__name__ if self.layout else None


        json["children"] = []
        for child in self.children:
            child_json = child.__json__()
            assert(child_json is not None)
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
        
        # Draw own bounding rect
        if self.draw_bounds and self.bounding_rect is not None:
            # Save the current color
            r, g, b, a = sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8()
            sdl2.SDL_GetRenderDrawColor(self.renderer.sdlrenderer, r, g, b, a)
            old_color = (r.value, g.value, b.value, a.value)

            # Set the new color
            r, g, b = (0, 127, 255) if self.has_focus() else (100, 100, 100)
            sdl2.SDL_SetRenderDrawColor(self.renderer.sdlrenderer, r, g, b, 255)

            # Draw the bounding rectangle
            wr = self.get_world_rect()
            sdl2.SDL_RenderDrawRect(self.renderer.sdlrenderer, wr)

            # Reset to the old color
            sdl2.SDL_SetRenderDrawColor(self.renderer.sdlrenderer, old_color[0], old_color[1], old_color[2], old_color[3])

        # Draw children
        for child in self:
            if child._visible:
                child.draw()


    def get_children(self):
        return self.children if self.children else []


    def add_child(self, child, add_to_focus_ring=True):
        child.parent = self
        self.children.append(child)

        self.updateLayout()

        child_rect_wrt_my_parent = sdl2.SDL_Rect(child.bounding_rect.x + self.bounding_rect.x,
                                                 child.bounding_rect.y + self.bounding_rect.y,
                                                 child.bounding_rect.w,
                                                 child.bounding_rect.h)
        self.bounding_rect = rect_union(self.bounding_rect, child_rect_wrt_my_parent)
        
        if add_to_focus_ring:
            self.focusRing.add(child)
            self.focusRing.focus(child)


    def remove_child(self, child):
        child.parent = None
        self.children.remove(child)
        self.updateLayout()


    def updateLayout(self):
        if self.layout is not None:
            self.layout.update()

        self.sizeToChildren()

        if self.parent is not None:
            self.parent.updateLayout()


    def sizeToChildren(self):
        # @todo DRY
        INSET_X = 1
        INSET_Y = 1

        if self.children:
            w = max([child.bounding_rect.x + child.bounding_rect.w for child in self])
            h = max([child.bounding_rect.y + child.bounding_rect.h for child in self])
            self.set_size(w + INSET_X, h + INSET_Y, updateLayout=False)


    def handle_event(self, event):
        return self.parent_handle_event(event)
    

GUI.register_control_type("GUIContainer", GUIContainer)
GUI.register_control_type("GUIControl", GUIControl)
