AISH(3) -- AI Shell 
==

![Screenshot showing a black screen with blue-bordered text areas, white labels, and LLM chat controls](./res/img/aish3-screenshot.png)

This is a Python GUI (SDL) application. The goal is to have a portable hands-free AI assistant and playground.

_Aish (אֵשׁ): The Hebrew word "Aish" translates to "fire, light, or flame" in English._


_In Korean, "Aish (아이씨)" or sometimes just "Ai (아이)" is a common informal exclamation often used to express frustration, annoyance, or mild surprise, somewhat equivalent to "Oh no!", "Darn!", or "Ugh!" in English._

So, Prometheus and Dr. Faustus. It captures the promise and the peril of AI.


Features:
* Have multiple LLM chats (with ChatGPT)
    * Save and load workspaces containing everything as JSON files
* Almost have minimalist Miro-like note-taking
    * Boxes (done) and arrows (todo. Pan around huge workspace. Zoom in and out (todo)
* Working towards (optional) full hands-free operation
    * Voice-in speech-to-text transcription
    * Voice-out reading of chat results and other text
    * Voice commands
* Working towards no-code app building
    * Define GUI in native app and then deploy to web and mobile (todo). The opposite of Electron.

### Running it

`python aish3.py`

#### Build a stand-alone macOS application

You can build a standalone application by doing:
`make macos`

This requires the pyinstaller Python module
`pip3 install pyinstaller`

This will create a dist folder, with the app in a subfolder, called aish3.

Run it as:
`./dist/aish3/aish3`

Note that you will have to supply your own .env file with for instance your OpenAI API key. The
.env file can be placed in the aish3 directory, or any containing directory. To move or distribute the
app, you copy the dist/aish3 folder somewhere else. Everything required (except .env file) is inside that folder.

#### Command-line parameters/settings:

`python aish3.py --help`

yields:

    usage: aish3.py [-h] [--fullscreen] [--width WIDTH] [--height HEIGHT] [--voice-in] [--workspace WORKSPACE]
    
    AISH window application.
    
    options:
      -h, --help            show this help message and exit
      --fullscreen          run in fullscreen mode
      --width WIDTH         window width (default: 1450)
      --height HEIGHT       window height (default: 800)
      --voice-in            Enable voice input (default: False)
      --workspace WORKSPACE workspace file (default: aish_workspace.json)

#### Setting up required environment variables

If you want to make GPT API requests, you'll need to provide a couple of environment variables in a .env file:

    OPENAI_ORGANIZATION = "..."
    OPENAI_API_KEY="..."

To use speech-to-text transcription, you'll need an AssemblyAI API KEY

    ASSEMBLYAI_API_KEY="..."

In order to use voice output (text to speech), you'll need Google Cloud credentials:

    GOOGLE_APPLICATION_CREDENTIALS="..."

And finally, to use the wakeup phrase detection, you'll need a PicoVoice access key:

    PICOVOICE_ACCESS_KEY="..."

If you get tired of entering System prompt text into LLM chats, you can set
a default system prompt using:

    DEFAULT_SYSTEM_PROMPT="..."

### Keyboard Commands

|Command|Description|
|-------|-----------|
|Cmd+Q|Quit|
|Cmd+N|Create a new GPT-4 chat|
|Cmd+G|Send messages to GPT-4 for chat completion|
|Cmd+U|Add another "user" message text field|
|Cmd+Delete|Delete the currently selected chat message (inside a chat), or the current chat (if whole chat is focused). Also works for other controls|
|Cmd+B|Add a new Label at the current cursor position|
|Cmd+R|Use Voice out to say some sample text|
|Cmd+Enter|Toggle active listening mode (speech to text transcription)|
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
