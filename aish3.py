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

# @todo log chat gpt reqeusts and responses
# @todo animated control resizing - jarring when textareas shrink on chat completion
# @todo make chat completion wait asynch. Show some kind of busy indicator
# @todo when cycling focus in LLMChatContainer, enlarge focused container, shrink others.
# @todo token streaming output from gpt
# @todo selected text should have a more drab background colour if TextArea is not focused
# @todo move to beginning/end of line
# @todo move to prev/next word
# @todo TextArea/TextEditBuffer word wrap
# @todo focus controls using mouse click
# @todo @bug weird behaviour when deleting past start of buffer
# @todo tabs don't just insert spaces, but move to a multiple of tab_spaces
# @todo hitting line down on last line goes to end of line doesn't affect desired_col
# @todo hitting line up on first line goes to start of line doesn't affect desired_col
# @todo flashing cursor
# @todo key repeat
# @todo copy text to clipboard
# @todo @bug ONLY FOR VARIABLE-WIDTH FONT: k and w misalignment between letters and cursor after drawing red boxes

import sdl2
import sdl2.ext
import sdl2.sdlttf as ttf
import argparse
import time
from gui import GUI
from llm_chat_container import LLMChatContainer
from transcribe_audio import VoiceTranscriptContainer
from gui_layout import RowLayout
from draw import draw_text
from dotenv import load_dotenv
import candlestick


def run(fullscreen, width, height, workspace_filename):
    # sdl2.ext.init()
    sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_EVENTS)
    ttf.TTF_Init()

    window = sdl2.ext.Window("AISH", size=(width, height), 
                             flags=sdl2.SDL_WINDOW_ALLOW_HIGHDPI | 
                             sdl2.SDL_WINDOW_RESIZABLE)

    if fullscreen:
        sdl2.SDL_SetWindowFullscreen(window.window, sdl2.SDL_WINDOW_FULLSCREEN)

    window.show()

    renderer = sdl2.ext.Renderer(window, 
                                    flags=sdl2.SDL_RENDERER_ACCELERATED | 
                                    sdl2.SDL_RENDERER_PRESENTVSYNC)

    WHITE = sdl2.ext.Color(255, 255, 255)
    font_path = "./res/fonts/FiraCode-Regular.ttf"
    # font_path = "./res/fonts/Menlo-Regular.ttf"
    font_size = 12
    font_manager = sdl2.ext.FontManager(font_path, size=font_size, color=WHITE)

    
    gui = GUI(renderer, font_manager, workspace_filename=workspace_filename)
    # gui = GUI(renderer, font_manager, workspace_filename=None)

    # chat1 = gui.create_control("LLMChatContainer", x=10, y=200)
    # chat2 = gui.create_control("LLMChatContainer", x=380, y=200)

    # label = gui.create_control("Label", text="This is a Label", x=10, y=10, w=120)

    # text = gui.create_control("TextArea", text="This is a TextArea.", x=10, y=50, w=300, h=100)

    # gui.content().add_child(chat1)
    # gui.content().add_child(chat2)
    # gui.content().add_child(label)
    # gui.content().add_child(text)

    # filename = "./data/test1.csv"
    # sticks = gui.create_control("CandlestickPlot", csv_filepath=filename, x=10, y=40, w=1380, h=600)
    # gui.content().add_child(sticks)

    running = True
    t_prev_update = time.time()

    fps_smoothed = 0.0
    while running:
        events = sdl2.ext.get_events()
        if events:
            for event in events:
                if event.type == sdl2.SDL_QUIT:
                    running = False
                    gui.on_quit()
                    break
                elif event.type == sdl2.SDL_WINDOWEVENT and \
                    event.window.event == sdl2.SDL_WINDOWEVENT_SIZE_CHANGED:
                        # Update renderer viewport to new window size
                        new_width = event.window.data1
                        new_height = event.window.data2

                        print("SDL_WINDOWEVENT_SIZE_CHANGED")

                        sdl2.SDL_RenderSetLogicalSize(renderer.renderer, new_width, new_height)

                        renderer.clear()
                        gui.draw()
                        renderer.present()

                else:
                    gui.handle_event(event)

        # Pump chat completions...
        for chat in gui._running_completions:
            completion = gui._running_completions[chat]
            chat.update_completion(completion)

        # Remove finished completion callbacks
        for chat, completion in list(gui._running_completions.items()):
            if completion is None:
                del gui._running_completions[chat]



        else:
            t_update = time.time()
            dt = t_update - t_prev_update
            gui.update(dt)
            t_prev_update = t_update

            t0 = time.time()
            renderer.clear()
            gui.draw()

            t1 = time.time()
            elapsed = t1 - t0
            fps = 1.0 / elapsed
            fps_smoothed = 0.9 * fps_smoothed + 0.1 * fps
            fps_str = f"FPS: {fps_smoothed:.2f}"
            draw_text(renderer, font_manager, fps_str, width - 100, 10)
            # print(fps_str)

            renderer.present()

    ttf.TTF_Quit()
    sdl2.ext.quit()


if __name__ == "__main__":
    # Load the .env file
    load_dotenv()

    parser = argparse.ArgumentParser(description='AISH window application.')
    parser.add_argument('--fullscreen', action='store_true', help='run in fullscreen mode')
    parser.add_argument('--width', type=int, default=1400, help='window width (default: 1450)')
    parser.add_argument('--height', type=int, default=800, help='window height (default: 800)')

    parser.add_argument('--workspace', default='aish_workspace.json', help='workspace file (default: aish_workspace.json)')
    args = parser.parse_args()

    run(args.fullscreen, args.width, args.height, args.workspace)
