Run the application
==
This is a Python command-line (CLI) application.

`python aish3.py`

If you want to make GPT API requests, you'll need to provide a couple of environment variables in a .env file:

  OPENAI_ORGANIZATION = "..."
  OPENAI_API_KEY="..."

It doesn't do much right now, except provide a GUI framework using text, and rectangles. The goal is to rapidly prototype GUI + LLM ideas. If I stick to using only text and rectangles, the hope is that this can be auto-translated to other platforms and languages.

This is not meant to replace front-end developers. Instead it's meant so that any of us can build working prototypes almost like functional wireframes. My first personal goal is to have a replacement for the ChatGPT web-interface and Playgrounds.

|Command|Description|
|-------|-----------|
|Cmd+Q|Quit|
|Cmd+N|Create a new GPT-4 chat|
|Cmd+G|Send messages to GPT-4 for chat completion|
|Cmd+S|Save workspace to aish_workspace.json|
|Cmd+L|Load workspace from aish_workspace.json
|TAB|Focus next control|
|Shift+TAB|Focus previous control|
|Enter|Move focus down into children of currently focused control|
|Esc|Move focus up to parent contaioer|
|Ctrl+TAB|Insert TAB char into currently focused TextArea|
|Arrow L/R/U/D|Move within TextArea|
|Cmd+V|Paste text from clipboard into focused TextArea|
|Delete|Remove previous char in TextArea|
|Other keys|Insert text char into focused TextArea|
|Mouse Wheel Up/Down|Scroll focused TextArea|
|Cmd+U|Add another "user" message text field|

NOTES:

Requirements / Prerequisites:
--

Python 3

Python SDL2 libraries for macOS: 
`brew install sdl2`

PySDL2 Python wrapper
`pip install pysdl2`

Build a stand-alone macOS application
--
You can build a standalone application by doing:
`make macos`

Run it as:
`./dist/aish3`

This requires the pyinstaller Python module
`pip3 install pyinstaller`
