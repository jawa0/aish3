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


import sdl2
from gui.fonts import font_descriptor_to_json_string
from draw import draw_text
from gui import GUI, GUIControl
from gui.fonts import json_to_font_descriptor


class Label(GUIControl):
    @classmethod
    def from_json(cls, json, **kwargs):
        assert(json["class"] == cls.__name__)
        gui = kwargs.get('gui')

        instance = gui.create_control(json["class"], **kwargs)
        instance.set_bounds(*json["bounding_rect"])
        instance._text = json["text"]
        instance.font_descriptor = json_to_font_descriptor(json['font_descriptor'])
        # print(f'Label.from_json(): instance.font_descriptor={instance.font_descriptor}')
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
            json["font_descriptor"] = font_descriptor_to_json_string(self.font_descriptor)
        return json


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
        # @todo should each specialized control need to implement this?
        if self._screen_relative:
            r = self.bounding_rect
        else:
            r = self.get_world_rect()

        if self.combined_text_texture is None:
            surf = sdl2.SDL_CreateRGBSurface(0, self.bounding_rect.w, self.bounding_rect.h, 32, 0, 0, 0, 0)

            draw_text(self.renderer, self.font_descriptor, self._text, r.x, r.y, bounding_rect=r, dst_surface=surf)

            self.combined_text_texture = sdl2.SDL_CreateTextureFromSurface(self.renderer.sdlrenderer, surf)
            sdl2.SDL_FreeSurface(surf)

        assert(self.combined_text_texture is not None)
        sdl2.SDL_RenderCopy(self.renderer.sdlrenderer, self.combined_text_texture, None, r)


GUI.register_control_type("Label", Label)