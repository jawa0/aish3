AISH(3) -- AI Shell 
==

_Aish (אֵשׁ): The Hebrew word "Aish" translates to "fire" in English._


_In Korean, "Aish (아이씨)" or sometimes just "Ai (아이)" is a common informal exclamation often used to express frustration, annoyance, or mild surprise, somewhat equivalent to "Oh no!", "Darn!", or "Ugh!" in English._


This is a Python command-line (CLI) application. It doesn't do much right now, except submit chat completions to GPT-4, and provide a GUI framework using text and rectangles. The eventual goal is to rapidly prototype GUI + LLM ideas. The first goal is to have a replacement for the ChatGPT web-interface and Playgrounds.

### Running it

`python aish3.py`

If you want to make GPT API requests, you'll need to provide a couple of environment variables in a .env file:

    OPENAI_ORGANIZATION = "..."
    OPENAI_API_KEY="..."

### Keyboard Commands

|Command|Description|
|-------|-----------|
|Cmd+Q|Quit|
|Cmd+N|Create a new GPT-4 chat|
|Cmd+G|Send messages to GPT-4 for chat completion|
|Cmd+U|Add another "user" message text field|
|Cmd+Delete|Delete the currently selected chat message (inside a chat), or the current chat (if whole chat is focused). Also works for other controls|
|Cmd+R|Toggle recording when a VoiceTranscriptContainer is focused.|
|Cmd+T|Create a new TextArea (use it like a post-it note)|
|Cmd+S|Save workspace to aish_workspace.json|
|Cmd+L|Load workspace from aish_workspace.json
|Cmd+V|Paste text from clipboard into focused TextArea|
|TAB|Focus next control|
|Shift+TAB|Focus previous control|
|Enter|Move focus down into children of currently focused control|
|Esc|If the currently focused control has selected text, then clear the selection. Otherwise, move focus up to parent container|
|Ctrl+TAB|Insert TAB char into currently focused TextArea|
|Arrow L/R/U/D|Move within TextArea|
|Option/Alt+Arrow L/R|Move to start of previous / next word|
|Cmd+L/R Arrow|Move to beginning/end of current line.|
|Mouse Wheel Up/Down|Scroll focused TextArea|
|Cmd+Up|Move to beginning of focused TextArea|
|Cmd+Down|Move to end of focused TextArea|
|Shift+Movement Command|Extend selection within TextArea|
|Delete|Remove previous char in TextArea|
|Other keys|Insert text char into focused TextArea|

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
