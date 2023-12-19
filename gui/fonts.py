import json
import os
from typing import Dict, Union, Tuple, Optional

from sdl2.ext import Color, FontManager


# Either a name, or a tuple of (filename, size, color)
FontColorRGB = Tuple[int, int, int]
FontFilename = str
FontSizePixels = int
FontDescriptor = Union[str, Tuple[FontFilename, FontSizePixels, FontColorRGB]]


# Function to convert a FontDescriptor to a string for saving to JSON.
def json_str_from_font_descriptor(font_descriptor: FontDescriptor) -> str:
    if isinstance(font_descriptor, str):
        font_desc_json_str = f'{{"font_descriptor": "{font_descriptor}"}}'
    else:
        filename, size, color = font_descriptor
        font_desc_json_str = f'{{"font_descriptor": {{"filename": "{filename}", "size": "{size}", "color": [{color[0]}, {color[1]}, {color[2]}]}}}}'
    return font_desc_json_str
    

# Function to convert a JSON stringto a FontDescriptor
def font_descriptor_from_json_str(json_string: str) -> FontDescriptor:
    # print(f'font_descriptor_from_json_str(): json_string={json_string}')
    try:
        data = json.loads(json_string)
        # print('Got valid JSON')
        # print(data)
        if "font_descriptor" in data:
            fdesc_maybe_dict = data["font_descriptor"]
            # print(fdesc_maybe_dict)
            if isinstance(fdesc_maybe_dict, str):
                return fdesc_maybe_dict
            else:
                filename = fdesc_maybe_dict["filename"]
                size = fdesc_maybe_dict["size"]
                color = fdesc_maybe_dict["color"]
                return filename, size, color
    except:
        return "default"


class FontRegistry:
    _instance = None
    _registry: Dict[FontDescriptor, FontManager]
    _default_path = './res/fonts'


    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(FontRegistry, cls).__new__(cls)
            cls._instance._registry = {}
        return cls._instance


    def create_fontmanager(self, filename: str, size: int, color: Tuple[int, int, int] = (255, 255, 255), string_key: Optional[str] = None) -> FontManager:
        key: FontDescriptor = string_key if string_key else (filename, size, color)
        
        print(f'FontRegistry.create_fontmanager(): key={key}')
        print(f'fontdescriptor_to_json_string(key)={json_str_from_font_descriptor(key)}')

        if key not in self._instance._registry:
            font_path = os.path.join(self._default_path, filename)
            self._instance._registry[key] = FontManager(font_path, size=size, color=Color(*color))
        return key


    def get_fontmanager(self, font_descriptor: FontDescriptor) -> Optional[FontManager]:
        return self._instance._registry.get(font_descriptor)
