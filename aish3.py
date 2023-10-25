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
import logging
import time

import config
from gui import GUI
from llm_chat_container import LLMChatContainer
from gui_layout import RowLayout
from draw import draw_text
from session import Session
from label import Label
from textarea import TextArea


def run(fullscreen, width, height, workspace_filename):
    try:
        logging.info('App start.')

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


        session: Session = Session()
        session.start()

        gui = GUI(renderer, font_manager, workspace_filename=workspace_filename, client_session=session)
        logging.info(f'Voice input available? {gui.voice_input_available()}')

        # @hack
        gui.listening_indicator = Label(screen_relative=True, x=5, y=5, w=200, gui=gui, renderer=renderer, font_manager=font_manager)
        gui.content().add_child(gui.listening_indicator)

        voice_transcript_height = 80
        gui.voice_transcript = TextArea(screen_relative=True, can_focus=False, visible=False, x=5, y= height - voice_transcript_height - 5, w=width-5, h=voice_transcript_height, gui=gui, renderer=renderer, font_manager=font_manager)
        gui.voice_transcript.input_q = gui.session.subscribe('transcribed_text')
        gui.content().add_child(gui.voice_transcript)

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

                            # @hack
                            if gui.voice_transcript is not None:
                                gui.voice_transcript.set_bounds(gui.voice_transcript.bounding_rect.x,
                                                                new_height - voice_transcript_height - 5, 
                                                                new_width-5, 
                                                                voice_transcript_height)

                            width = new_width
                            height = new_height

                            print("SDL_WINDOWEVENT_SIZE_CHANGED")

                            sdl2.SDL_RenderSetLogicalSize(renderer.renderer, new_width, new_height)

                            renderer.clear()
                            gui.draw()
                            renderer.present()

                    else:
                        gui.handle_event(event)

            else:
                session.update()

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

        session.stop()

        ttf.TTF_Quit()
        sdl2.ext.quit()
        logging.info('App quit.')
    
    except Exception as e:
        logging.exception('Unhandled exception at app level: ', e)
        raise e


if __name__ == "__main__":
    
    config.load()

    parser = argparse.ArgumentParser(description='AISH window application.')
    parser.add_argument('--fullscreen', action='store_true', help='run in fullscreen mode')
    parser.add_argument('--width', type=int, default=1400, help='window width (default: 1450)')
    parser.add_argument('--height', type=int, default=800, help='window height (default: 800)')

    parser.add_argument('--workspace', default='aish_workspace.json', help='workspace file (default: aish_workspace.json)')
    args = parser.parse_args()

    run(args.fullscreen, args.width, args.height, args.workspace)
