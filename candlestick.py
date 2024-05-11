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


import csv
import sdl2
from draw import draw_cursor, draw_text, set_color
from gui import GUI, GUIControl
from math import ceil, floor, isclose


class CandlestickPlot(GUIControl):
    @classmethod
    def from_json(cls, json, **kwargs):
        assert(json["class"] == cls.__name__)
        kwargs = super(CandlestickPlot, cls)._enrich_kwargs(json, **kwargs)

        gui = kwargs.get('gui')

        instance = gui.create_control(json["class"], **kwargs)
        instance.set_bounds(*json["bounding_rect"])
        instance.csv_filepath = json["csv_filepath"]
        instance.load_data(instance.csv_filepath)
        return instance


    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        csv_filepath = kwargs.get('csv_filepath', None)
        if csv_filepath is not None:
            self.csv_filepath = csv_filepath
            self.load_data(csv_filepath)
        else:
            self.rows = None
        
        self.draw_bounds = True
        self.scroll = [0, 0]
        self.top_pad = 15
        self.bottom_pad = 15
        self.left_pad = 55
        self.right_pad = 10


    def __json__(self):
        json = super().__json__()
        json['class'] = self.__class__.__name__
        json['csv_filepath'] = self.csv_filepath
        return json


    def load_data(self, csv_filepath):
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



    def draw(self):

        wr = self.get_world_rect()
        y0 = wr.y + self.top_pad

        if self.rows is not None:
            assert(len(self.opens) == len(self.closes) == len(self.highs) == len(self.lows))

            top_price = ceil(max(self.highs))
            bottom_price = floor(min(self.lows))
            y_scale = (wr.h - self.top_pad - self.bottom_pad) / (top_price - bottom_price)

            def y_from_price(price: float):
                return int(0.5 + y0 + (top_price - price) * y_scale)
                
            old_color = set_color(self.renderer, (255, 255, 255, 255))

            # Draw the y-axis
            sdl2.SDL_RenderDrawLine(self.renderer.sdlrenderer, wr.x + self.left_pad, wr.y + self.top_pad, wr.x + self.left_pad, wr.y + wr.h - self.bottom_pad)


            p = bottom_price
            while p <= top_price + 0.05:
                y = y_from_price(p)
                
                draw_number = False
                tick_width = 4

                if isclose(p % 1.0, 0.0, abs_tol=0.01):
                    draw_number = True
                    tick_width = 12
                elif isclose(p % 0.5, 0.0, abs_tol=0.01):
                    draw_number = True
                    tick_width = 8

                if draw_number:
                    draw_text(self.renderer, self.font_manager, f'{p:0.1f}', wr.x + self.left_pad - 45, y - 8)

                sdl2.SDL_RenderDrawLine(self.renderer.sdlrenderer, wr.x + self.left_pad, y, wr.x + self.left_pad - tick_width, y)

                p += 0.1

            # Draw the candlesticks
            candle_w = 4
            for i, row in enumerate(self.opens):
                # print(i)
                x0 = wr.x + self.left_pad + i * candle_w - self.scroll[0]
                if x0 < wr.x + self.left_pad:
                    continue

                y_open = y_from_price(self.opens[i])
                y_close = y_from_price(self.closes[i])
                y_high = y_from_price(self.highs[i])
                y_low = y_from_price(self.lows[i])

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


    def handle_event(self, event):
        # @note: I don't like that each derived class has to remember to do this
        if self._pre_handle_event(event):
            return True

        if event.type == sdl2.SDL_MOUSEWHEEL:
            self.scroll_by(dx=event.wheel.x * 8, dy=event.wheel.y * -8)
            return True


    def scroll_by(self, dx=0, dy=0):
        self.scroll[0] = max(0, self.scroll[0] + dx)  # adjust x_scroll by dx
        self.scroll[1] = max(0, self.scroll[1] + dy)  # adjust y_scroll by dy
        # self.set_needs_redraw()

GUI.register_control_type("CandlestickPlot", CandlestickPlot)
