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


import argparse
import asyncio
import logging
import os
import time

import sdl2
import sdl2.ext
import sdl2.sdlttf as ttf

import config
from gui import GUI, FontRegistry
from llm_chat_container import LLMChatContainer
from gui_layout import RowLayout
from command_console import CommandConsole
from draw import draw_text
from session import Session
from label import Label
from textarea import TextArea
from llm_agent_chat import LLMAgentChat


async def run(*, fullscreen: bool, width: int, height: int, workspace_filename: str, enable_voice_in: bool):
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

    font_filename = "FiraCode-Regular.ttf"
    font_descriptor = FontRegistry().create_fontmanager(font_filename, 12, string_key="default")
    FontRegistry().create_fontmanager(font_filename, 24, string_key="large-label")

    session: Session = Session()
    session.start()

    # Can we enable voice in? @todo DRY
    ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

    if enable_voice_in and not ASSEMBLYAI_API_KEY:
        logging.error("ASSEMBLYAI_API_KEY is not set. Cannot enable voice input. Either set the environment variable, or disable voice input.")
        raise Exception("ASSEMBLYAI_API_KEY is not set. Cannot enable voice input. Either set the environment variable, or disable voice input.")

    def setup_gui(gui: GUI):
        gui.listening_indicator = Label(saveable=False, screen_relative=True, x=5, y=5, w=200, gui=gui)
        gui.content().add_child(gui.listening_indicator)

        voice_transcript_height = 60
        gui.voice_transcript = TextArea(saveable=False, screen_relative=True, can_focus=False, visible=False, x=5, y= height - voice_transcript_height - 5, w=width-5, h=voice_transcript_height, gui=gui)
        gui.voice_transcript.input_q = gui.session.subscribe('transcribed_text')
        gui.content().add_child(gui.voice_transcript)

        # gui.command_console = CommandConsole(saveable=False,
        #                                      screen_relative=True,
        #                                     can_focus=True,
        #                                     visible=False,
        #                                     x=10,
        #                                     y=50,
        #                                     w=1000,
        #                                     h=500,
        #                                     gui=gui)
        # gui.content().add_child(gui.command_console)

    # Need to fixup path so we an work from inside a PyInstaller distribution.
    print('__file__:', __file__)
    app_path = os.path.dirname(os.path.abspath(__file__))
    print(f'app_path: {app_path}')

    workspace_filepath = os.path.abspath(os.path.join(app_path, workspace_filename))
    print(f'workspace_filepath: {workspace_filepath}')

    gui = GUI(renderer, 
                font_descriptor, 
                workspace_filename=workspace_filepath, 
                client_session=session,
                enable_voice_in=enable_voice_in,
                enable_voice_out=False,
                create_hook=setup_gui)
    
    running = True
    t_prev_update = time.time()

    fps_smoothed = 0.0
    while running:
        #
        # Handle any pending SDL events, to prevent GUI from becoming unresponsive.
        #

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

                            # gui.command_console.set_bounds(10, 10, new_width-10, 200)

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
            #
            # Give a chance for the asyncio event loop to do some work...
            #

            await asyncio.sleep(0.0001)
            await session.update()

            #
            # Update our app GUI and draw scene
            #

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
            draw_text(renderer, font_descriptor, fps_str, width - 100, 10)
            # print(fps_str)

            renderer.present()

    session.stop()

    ttf.TTF_Quit()
    sdl2.ext.quit()
    logging.info('App quit.')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='AISH window application.')
    parser.add_argument('--fullscreen', action='store_true', help='run in fullscreen mode')
    parser.add_argument('--width', type=int, default=1400, help='window width (default: 1450)')
    parser.add_argument('--height', type=int, default=800, help='window height (default: 800)')
    parser.add_argument('--voice-in', action='store_true', help='Enable voice input.')
    parser.add_argument('--workspace', default='aish_workspace.json', help='workspace file (default: aish_workspace.json)')
    args = parser.parse_args()

    asyncio.run(
        run(fullscreen=args.fullscreen, 
            width=args.width, 
            height=args.height, 
            workspace_filename=args.workspace, 
            enable_voice_in=args.voice_in)
    )