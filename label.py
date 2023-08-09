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
from gui import GUI, GUIControl
from draw import draw_text


class Label(GUIControl):
    @classmethod
    def from_json(cls, json, **kwargs):
        assert(json["class"] == cls.__name__)
        gui = kwargs.get('gui')

        instance = gui.create_control(json["class"], **kwargs)
        instance.set_bounds(*json["bounding_rect"])
        instance.text = json["text"]
        return instance

    def __init__(self, text="", **kwargs):
        super().__init__(can_focus=False, **kwargs)
        self.text = text


    def __json__(self):
        json = super().__json__()
        json["class"] = self.__class__.__name__
        json["text"] = self.text
        return json


    def draw(self):
        r = self.get_world_rect()
        draw_text(self.renderer, self.font_manager, self.text, r.x, r.y, r)


GUI.register_control_type("Label", Label)