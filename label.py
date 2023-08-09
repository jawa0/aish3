# (C) 2023 by Jabavu Adams. All Rights Reserved.

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