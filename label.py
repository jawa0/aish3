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


from json import JSONDecodeError, loads
import logging
from typing import Optional

import sdl2
from gui.fonts import json_str_from_font_descriptor
from draw import draw_text, get_char_width
from gui import GUI, GUIControl
from gui.fonts import FontDescriptor, font_descriptor_from_json_str
from platform_utils import is_cmd_pressed
from textarea import TextArea


class Label(GUIControl):
    @classmethod
    def from_json(cls, json, **kwargs):
        assert(json["class"] == cls.__name__)
        kwargs = super(Label, cls)._enrich_kwargs(json, **kwargs)
        
        gui = kwargs.get('gui')

        # print('\n\n******\n\n\n\n')

        # The font descriptor may be just a string, or it may be a dict.
        
        font_desc_maybe_json_str = json.get('font_descriptor', 'default')
        # print(f'font_desc_json_str: {font_desc_maybe_json_str}')
        
        font_desc = font_descriptor_from_json_str(font_desc_maybe_json_str)
        # print(f'font_desc: {font_desc}')

        # print('\n\n******\n\n\n\n')

        kwargs["font_descriptor"] = font_desc

        instance = gui.create_control(json["class"], **kwargs)
        instance.set_bounds(*json["bounding_rect"])
        instance._text = json["text"]

        return instance


    def __init__(self, **kwargs):
        super().__init__(can_focus=False, **kwargs)
        self._text = kwargs.get('text', '')
        
        self.font_descriptor = kwargs.get('font_descriptor', "default")

        self.combined_text_texture = None


    def __json__(self):
        json = super().__json__()
        if json is not None:    # Could be None on save, if control is not saveable. @todo DRY every derived class will have to do this. Boo.
            json["class"] = self.__class__.__name__
            json["text"] = self._text
            json["font_descriptor"] = json_str_from_font_descriptor(self.font_descriptor)
        return json


    def __str__(self):
        default_str = super(Label, self).__str__()
        text_summary = self.get_text()[:12]
        return f"{default_str}, text: {text_summary}"
    

    def get_text(self):
        return self._text
    

    def set_text(self, text):
        self._text = text
        self.set_needs_redraw()


    def set_needs_redraw(self):
        if self.combined_text_texture is not None:
            sdl2.SDL_DestroyTexture(self.combined_text_texture)
            self.combined_text_texture = None


    def draw(self):
        r = self.get_view_rect()

        if self.combined_text_texture is None:
            surf = sdl2.SDL_CreateRGBSurface(0, self.bounding_rect.w, self.bounding_rect.h, 32, 0, 0, 0, 0)

            draw_text(self.renderer, self.font_descriptor, self._text, r.x, r.y, bounding_rect=r, dst_surface=surf)

            self.combined_text_texture = sdl2.SDL_CreateTextureFromSurface(self.renderer.sdlrenderer, surf)
            sdl2.SDL_FreeSurface(surf)

        assert(self.combined_text_texture is not None)
        sdl2.SDL_RenderCopy(self.renderer.sdlrenderer, self.combined_text_texture, None, r)


    def on_double_click(self, vx, vy):
        logging.debug("Label.on_double_click")
        if self._editable and not self.editor:
            self._start_editing()


    def _start_editing(self):
        assert(not self.editor)
        self.editor = self.gui.create_control("LabelEditor", 
                                        label=self, 
                                        saveable=False,
                                        draggable=False,
                                        font_descriptor=self.font_descriptor, 
                                        x=self.bounding_rect.x, 
                                        y=self.bounding_rect.y, 
                                        w=self.bounding_rect.w, 
                                        h=self.bounding_rect.h)
        self.parent.add_child(self.editor)
        

class LabelEditor(TextArea):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.edit_target: Label = kwargs['label']
        self._was_target_draggable = self.edit_target._draggable
        self.edit_target._draggable = False
        self.text_buffer.set_text(self.edit_target.get_text())
        self.text_buffer.move_point_to_end()


    def _stop_editing(self):
        assert(self.edit_target)
        self.edit_target.set_text(self.text_buffer.get_text())
        text_width_px = get_char_width(self.edit_target.font_descriptor, "W") * len(self.text_buffer.get_text())

        r = self.edit_target.bounding_rect
        self.edit_target.set_bounds(r.x, r.y, text_width_px, r.h)

        self.edit_target._draggable = self._was_target_draggable
        self.parent.remove_child(self)
        self.edit_target.editor = None
        self.edit_target = None


    def _change_focus(self, am_getting_focus: bool) -> bool:
        # Losing focus cancels editing
        if self.has_focus() and not am_getting_focus:
            self._stop_editing()
            return True

        return super()._change_focus(am_getting_focus)


    def handle_event(self, event):
        # @note: I don't like that each derived class has to remember to do this
        if self._pre_handle_event(event):
            return True

        if event.type == sdl2.SDL_KEYDOWN:
            cmdPressed: bool = is_cmd_pressed(event)
            keySymbol = event.key.keysym.sym

            if cmdPressed:
                # Cmd+Delete to delete Label we're editing
                if keySymbol == sdl2.SDLK_BACKSPACE:
                    self.edit_target.parent.remove_child(self.edit_target)
                    self._stop_editing()
                    return True
            else:
                if keySymbol == sdl2.SDLK_ESCAPE or keySymbol == sdl2.SDLK_RETURN:
                    self._stop_editing()
                    return True

        return super().handle_event(event)


GUI.register_control_type("Label", Label)
GUI.register_control_type("LabelEditor", LabelEditor)