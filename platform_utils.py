import sys
import sdl2


def is_cmd_pressed(event: sdl2.SDL_Event) -> bool:
    """
    Check if the platform-specific command modifier key is pressed.

    Args:
        event (sdl2.SDL_Event): The SDL event to check for the modifier key.

    Returns:
        bool: True if the command modifier key is pressed, False otherwise.

    Notes:
        - On macOS, the command modifier key is the Command (Cmd) key.
        - On Windows and Linux, the command modifier key is the Control (Ctrl) key.
    """
    if sys.platform == 'darwin':
        return 0 != event.key.keysym.mod & sdl2.KMOD_GUI
    elif sys.platform == 'win32' or sys.platform == 'linux':
        return 0 != event.key.keysym.mod & sdl2.KMOD_CTRL
    else:
        # Unknown operating system
        return False