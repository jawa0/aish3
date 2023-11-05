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
import sdl2
from typing import Union
from tzlocal import get_localzone
import weakref
import os

from command_listener import VoiceCommandListener
from .fonts import FontRegistry
from .gui_container import GUIContainer
from rect_utils import rect_union
from transcribe_audio import VoiceTranscriber
import utils
from voice_out import VoiceOut
from voice_wakeup import PhraseListener


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
            if not "font_descriptor" in kwargs:
                kwargs["font_descriptor"] = gui.font_descriptor

            return control_class(**kwargs)
        else:
            return None


    def __init__(self, renderer, font_descriptor, workspace_filename=None, client_session=None, enable_voice_in=False, enable_voice_out=False):        
        assert(client_session is not None)
        self.session = client_session
        self.session.gui = weakref.ref(self)

        self.renderer = renderer
        self.font_descriptor = font_descriptor

        # Makes unit testing harder.
        # assert(self.renderer)
        # assert(self.font_descriptor)

        self._content = GUIContainer(gui=self)
        assert(self._content.focusRing is not None)
        self.focus_stack = []
        self.push_focus_ring(self._content.focusRing)
        
        # May be self.content or any depth of descendant of self.content
        self._focused_control = None

        self._strokes = {}
        self._drag_control = None

        self._viewport_pos = (0, 0)
        self._viewport_bookmarks = {}

        self.workspace_filename = workspace_filename
        if self.workspace_filename is not None:
            self.load()

        if enable_voice_out:
            self._voice_out = VoiceOut(on_speech_done=[self._on_speech_done])
        else:
            self._voice_out = None
        self._saying_text = None
        self._next_texts_to_say = []


        self._voice_in_state = GUI.VOICE_IN_STATE_LISTENING_FOR_WAKEWORD  # trigger start in update()
        self._voice_wakeup = None

        if enable_voice_in:
            self._voice_in = VoiceTranscriber(session=self.session)
        self._should_stop_voice_in = False

        self.command_listener = None


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


    def set_view_pos(self, x: int, y: int) -> None:
        logging.debug(f'GUI.set_view_pos({x}, {y})')
        self._viewport_pos = (x, y)


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
            self.command_listener = VoiceCommandListener(session=self.session, on_command=self._on_voice_command)

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
        self.command_listener = VoiceCommandListener(session=self.session, on_command=self._on_voice_command)


    def _on_voice_command(self, command: str) -> None:
        logging.info(f'GUI._on_voice_command({command})')

        # @todo make sanitization routines
        command = command.replace('"', "")
        command = command.replace("'", "")

        if command == "stop_listening":
            logging.info('Command: stop listening')
            self._should_stop_voice_in = True

        elif command == "create_new_chat_with_llm":
            self.cmd_new_llm_chat()

        elif command == "create_new_text_area":
            self.cmd_new_text_area()



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
                            self.set_focus(hit_control)
                    return True

            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                # Do we have a stroke for this button?
                if event.button.button in self._strokes:
                    # We do.  Remove this stroke.
                    del self._strokes[event.button.button]
                    # print(f"STROKE (button {event.button.button}) end")

                    # If it's the left mouse button, then check if we're dragging and release drag.
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
                        self.set_view_pos(self._viewport_pos[0] - dx, self._viewport_pos[1] - dy)

                    return True
                
        return handled
    

    def cmd_new_text_area(self, x: int, y: int) -> None:
        logging.info('Command: create new text area')
        wr = self.content().get_world_rect()

        # self.content().sizeToChildren()
        textArea = self.create_control("TextArea", w=240, h=100, x=x.value-wr.x, y=y.value-wr.y)
        self.content().add_child(textArea)
        self.set_focus(textArea)


    def cmd_new_llm_chat(self, x: int, y: int) -> None:
        logging.info('Command: create new LLM chat')
        wr = self.content().get_world_rect()

        # self.content().sizeToChildren()

        argx = x.value-wr.x
        argy = y.value-wr.y

        logging.debug(f"Creating new LLMChatContainer at {argx}, {argy}")
        chat = self.create_control("LLMChatContainer", x=argx, y=argy)
        self.content().add_child(chat)


    def cmd_new_label(self, x: int, y: int) -> None:
        logging.info('Command: create new Label')
        wr = self.content().get_world_rect()

        # self.content().sizeToChildren()
        label = self.create_control("Label", text="New Label", font_descriptor="large-label", w=200, h=30, x=x.value-wr.x, y=y.value-wr.y)
        self.content().add_child(label)
        self.set_focus(label)


    def cmd_set_viewport_bookmark(self, index: int) -> None:
        logging.info(f'Command: set viewport bookmark {index}')
        logging.debug(f'Bookmarks: {self._viewport_bookmarks}')

        s_index: str = str(index)
        self._viewport_bookmarks[s_index] = self._viewport_pos
        logging.debug(f'Bookmarks: {self._viewport_bookmarks}')


    def cmd_goto_viewport_bookmark(self, index: int) -> None:
        logging.info(f'Command: goto viewport bookmark {index}')
        logging.debug(f'Bookmarks: {self._viewport_bookmarks}')

        s_index: str = str(index)
        if s_index in self._viewport_bookmarks:
            vx, vy = self._viewport_bookmarks[s_index]
            self.set_view_pos(vx, vy)
        else:
            logging.warning(f'Viewport bookmark {index} does not exist.')


    def handle_keydown(self, event):
        vr = self.content().get_view_rect()

        keySym = event.key.keysym.sym
        cmdPressed: bool = 0 != event.key.keysym.mod & (sdl2.KMOD_LGUI | sdl2.KMOD_RGUI)
        shiftPressed: bool = 0 != event.key.keysym.mod & (sdl2.KMOD_LSHIFT | sdl2.KMOD_RSHIFT)
        altPressed: bool = 0 != event.key.keysym.mod & (sdl2.KMOD_LALT | sdl2.KMOD_RALT)
        ctrlPressed: bool = 0 != event.key.keysym.mod & (sdl2.KMOD_LCTRL | sdl2.KMOD_RCTRL)

        # print(f'keySym: {keySym}, cmdPressed: {cmdPressed}, shiftPressed: {shiftPressed}, altPressed: {altPressed}, ctrlPressed: {ctrlPressed}')

        if cmdPressed:
            x = ctypes.c_int()
            y = ctypes.c_int()                
            sdl2.mouse.SDL_GetMouseState(ctypes.byref(x), ctypes.byref(y))

            # Shift+Cmd+[1-9] sets viewport bookmark
            if shiftPressed and not altPressed and not ctrlPressed and \
                keySym >= sdl2.SDLK_0 and keySym <= sdl2.SDLK_9:

                i_bookmark: int = int(keySym - sdl2.SDLK_0)
                self.cmd_set_viewport_bookmark(i_bookmark)
                return True
            
            # Cmd+[0-9] goes to viewport bookmark
            if not shiftPressed and not altPressed and not ctrlPressed and \
                keySym >= sdl2.SDLK_0 and keySym <= sdl2.SDLK_9:

                i_bookmark: int = int(keySym - sdl2.SDLK_0)

                # Bookmark 0 is not settable, but will always go to the coordinates of
                # the currently focused control. Helpful if we're lost in space.

                if i_bookmark == 0:
                    if self.get_focus() is not None:
                        wr = self.get_focus().get_world_rect()
                        self.set_view_pos(wr.x, wr.y)
                    else:
                        self.set_view_pos(0, 0)
                    return True
                
                self.cmd_goto_viewport_bookmark(i_bookmark)
                return True
            
            # Cmd+B creates a new Label
            if keySym == sdl2.SDLK_b:
                self.cmd_new_label(x, y)
                return True
            
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
                self.cmd_new_llm_chat(x, y)
                return True  # event was handled

            # Cmd+R say something
            if keySym == sdl2.SDLK_r:
                self.say("One, one-thousand. Two one-thousand. Three one-thousand. Do not call logging or print from this function! It's time-critical! You've touched upon a fascinating aspect of language models and artificial intelligence in general. While language models like mine lack true understanding and consciousness, they can indeed produce remarkably coherent and contextually relevant text, often to the point of surprising users.")
                # self.say("Listening")
                

                return True  # event was handled
            
            # Cmd+T creaes a new TextArea
            if keySym == sdl2.SDLK_t:
                self.cmd_new_text_area(x, y)
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
                    self.command_listener = VoiceCommandListener(session=self.session, on_command=self._on_voice_command)
                    self._voice_in_state = GUI.VOICE_IN_STATE_LISTENING_FOR_SPEECH

                elif self._voice_in_state == GUI.VOICE_IN_STATE_LISTENING_FOR_SPEECH:
                    logging.info(f'GUI is listening for speech. Stopping active listening.')
                    self._voice_in.stop_recording()
                    self.command_listener = None
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

            if ctrlPressed:
                # Ctrl+TAB inserts a tab character - we handle this in the TextArea class
                pass
            else:
                if shiftPressed:  # if shift was also held
                    if focusRing.focus_previous():
                        return True  # event was handled
                else:
                    if focusRing.focus_next():
                        return True  # event was handled


    def update(self, dt):
        # print(f'****\nViewport pos: {self._viewport_pos}')
        # print(f'  gui.content().bounding_rect: {self.content().bounding_rect}')
        # print(f'  gui.content().get_world_rect(): {self.content().get_world_rect()}')
        # print(f'  gui.content().get_view_rect(): {self.content().get_view_rect()}')

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

            if self.command_listener is not None:
                self.command_listener.update()

            # Stop voice in?
            if self._should_stop_voice_in and self._voice_in.is_recording():
                self._voice_in.stop_recording()
                logging.debug(f'Just called self._voice_in.stop_recording() and self._voice_in is {self._voice_in}')
                self._should_stop_voice_in = False
                self.command_listener = None

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
    
    
    def set_focus(self, control: "GUIControl", focus_it=True):
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
        

    def check_hit(self, x: int, y: int) -> "Union[GUIControl, None]":
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

        unique_filename = utils.unique_filename(self.workspace_filename)
        if unique_filename != self.workspace_filename:
            logging.info(f"Backing up existing workspace file to \"{os.path.abspath(unique_filename)}\"")
            os.rename(self.workspace_filename, unique_filename)
        logging.info(f"Saving workspace file to \"{os.path.abspath(self.workspace_filename)}\"")

        with open(self.workspace_filename, "w") as f:
            print(self._viewport_bookmarks)
            print(f'Viewport pos: {self._viewport_pos}')

            gui_json = {
                "saved_at_utc": utc_now.isoformat(),
                "saved_at_local": local_now.isoformat(),
                "gui": self.__json__(),
                "viewport_bookmarks": self._viewport_bookmarks,
                "viewport_pos": self._viewport_pos
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
                self._content = gui_class.from_json(content_json, gui=self)
                self.push_focus_ring(self._content.focusRing)

                focusRing = self.get_focus_ring()
                assert(focusRing is not None)
                focusRing.focus_first()

                print(gui_json["viewport_bookmarks"])
                self._viewport_bookmarks = gui_json.get("viewport_bookmarks", {})
                
                vx, vy = gui_json.get("viewport_pos", (0, 0))
                self.set_view_pos(vx, vy)
                

        except Exception as e:
            logging.error("Error loading GUI. Exception: ", str(e))
            self._content = bak_content
            self._focused_control = bak_focused_control
            return False
        
        # self._content.sizeToChildren()
        
        # self._viewport_pos = self.content().bounding_rect.x, self.content().bounding_rect.y


        logging.info("GUI loaded.")
        return True


    def voice_input_available(self):
        """Is speech input available?"""
        return os.getenv("ASSEMBLYAI_API_KEY") is not None


