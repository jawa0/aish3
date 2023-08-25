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


import csv
import sdl2
from draw import draw_cursor, draw_text, set_color
from gui import GUI, GUIControl


class CandlestickPlot(GUIControl):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        csv_filepath = kwargs.get('csv_filepath', None)
        if csv_filepath is None:
            raise ValueError('csv_filepath is required.')
        
        with open(csv_filepath, 'r') as file:
            target_line = '# Date, Time, Open, High, Low, Close, Volume'
            line = next(file).strip()
            while line != target_line:
                line = next(file).strip()

            reader = csv.reader(file)
            self.rows = tuple(reader)
            # print(rows)

        self.opens = [float(row[2]) for row in self.rows]
        self.closes = [float(row[5]) for row in self.rows]
        self.highs = [float(row[3]) for row in self.rows]
        self.lows = [float(row[4]) for row in self.rows]

        self.draw_bounds = True
        self.scroll = [0, 0]
        self.top_pad = 10
        self.bottom_pad = 10

            
    def draw(self):
        wr = self.get_world_rect()

        # Draw the candlesticks
        assert(len(self.opens) == len(self.closes) == len(self.highs) == len(self.lows))

        top_price = max(self.highs)
        bottom_price = min(self.lows)
        y_scale = (wr.h - self.top_pad - self.bottom_pad) / (top_price - bottom_price)

        old_color = set_color(self.renderer, (255, 255, 255, 255))

        candle_w = 4
        for i, row in enumerate(self.opens):
            # print(i)
            x0 = wr.x + i * candle_w
            y0 = wr.y + self.top_pad

            y_open = int(0.5 + y0 + (top_price - self.opens[i]) * y_scale)
            y_close = int(0.5 + y0 + (top_price - self.closes[i]) * y_scale)
            y_high = int(0.5 + y0 + (top_price - self.highs[i]) * y_scale)
            y_low = int(0.5 + y0 + (top_price - self.lows[i]) * y_scale)

            # Draw the candlestick "wicks"
            set_color(self.renderer, (255, 255, 255, 255))
            sdl2.SDL_RenderDrawLine(self.renderer.sdlrenderer, x0+1, y_high, x0+1, y_low)

            # Draw the candlestick "body"
            if self.opens[i] < self.closes[i]:
                set_color(self.renderer, (0, 255, 0, 255))
            elif self.opens[i] > self.closes[i]:
                set_color(self.renderer, (255, 0, 0, 255))
            else:
                set_color(self.renderer, (255, 255, 255, 255))

            sdl2.SDL_RenderFillRect(self.renderer.sdlrenderer, sdl2.SDL_Rect(x0, y_open, 3, y_close - y_open))
            
            if x0 >= wr.x + wr.w - candle_w:
                break
            
        set_color(self.renderer, old_color)



        # Draw own bounding rect @debug @test
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


# def find_line_number(file_path, target_line):
#     with open(file_path, 'r') as file:
#         for num, line in enumerate(file, 1):
#             if line.strip() == target_line:
#                 return num
#     return None

# line_number = find_line_number('filename.csv', '# Date, Time, Open, High, Low, Close, Volume')
# if line_number:
#     print(f'The line number is: {line_number}')
# else:
#     print('The line was not found.')


GUI.register_control_type("CandlestickPlot", CandlestickPlot)
