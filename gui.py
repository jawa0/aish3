# (C) 2023 by Jabavu Adams. All Rights Reserved.

import datetime
import json
import pytz
from rect_utils import rect_union
import sdl2
from tzlocal import get_localzone
from gui_layout import ColumnLayout
from gui_focus import FocusRing
import weakref


#===============================================================================
class GUI:
    _factories = {}

    @classmethod
    def register_control_type(cls, class_name, control_class):
        cls._factories[class_name] = control_class


    @classmethod
    def control_class(cls, class_name):
        return cls._factories.get(class_name, None)
    

    def create_control(self, class_name, **kwargs):
        cls = self.__class__
        control_class = cls.control_class(class_name)
        if control_class:
            if not "gui" in kwargs:
                kwargs["gui"] = self
            gui = kwargs["gui"]

            if not "renderer" in kwargs:
                kwargs["renderer"] = gui.renderer
            if not "font_manager" in kwargs:
                kwargs["font_manager"] = gui.font_manager

            return control_class(**kwargs)
        else:
            return None


    def __init__(self, renderer, font_manager):        
        self.renderer = renderer
        self.font_manager = font_manager

        assert(self.renderer)
        assert(self.font_manager)

        self._content = GUIContainer(gui=self, renderer=self.renderer, font_manager=self.font_manager)
        assert(self._content.focusRing is not None)
        self.focus_stack = []
        self.push_focus_ring(self._content.focusRing)
        
        # May be self.content or any depth of descendant of self.content
        self._focused_control = None


    class JSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if hasattr(obj, '__json__'):
                return obj.__json__()
            return json.JSONEncoder.default(self, obj)


    def __json__(self):
        return {"class": self.__class__.__name__, 
                "content": self._content.__json__()}
    

    def content(self):
        return self._content
    
    
    def get_ancestor_chain(self, control):
        chain = []
        while control is not None:
            chain.append(control)
            control = control.parent
        chain.reverse()
        chain.pop()  # Don't want the control, itself
        return chain
    

    def handle_event(self, event):
        handled = False
        if self._focused_control:
            handled = self._focused_control.handle_event(event)

        if not handled:    
            if event.type == sdl2.SDL_KEYDOWN:
                # Cmd+S saves GUI
                if event.key.keysym.sym == sdl2.SDLK_s and (event.key.keysym.mod & (sdl2.KMOD_LGUI | sdl2.KMOD_RGUI)):
                    self.save()
                    return True  # event was handled
                # Cmd+L loads GUI
                if event.key.keysym.sym == sdl2.SDLK_l and (event.key.keysym.mod & (sdl2.KMOD_LGUI | sdl2.KMOD_RGUI)):
                    self.load()
                    return True  # event was handled
                # Cmd+N add new LLM chat
                if event.key.keysym.sym == sdl2.SDLK_n and (event.key.keysym.mod & (sdl2.KMOD_LGUI | sdl2.KMOD_RGUI)):
                    self.content().sizeToChildren()
                    chat = self.create_control("LLMChatContainer", y=10, x=10+self.content().bounding_rect.w)
                    self.content().add_child(chat)
                    # self.set_focus(chat)
                    return True  # event was handled

                # Cmd+R remove LLM chain
                if event.key.keysym.sym == sdl2.SDLK_r and (event.key.keysym.mod & (sdl2.KMOD_LGUI | sdl2.KMOD_RGUI)):
                    assert(self.chats is not None)
                    control = self.get_focus()
                    print(control)
                    print(self.get_ancestor_chain(control))

                    return True  # event was handled

            elif event.key.keysym.sym == sdl2.SDLK_RETURN:
                # Focus down into FocusRing of currently focused control...
                focused = self._focused_control
                if focused:
                    if hasattr(focused, "focusRing"):
                        self.push_focus_ring(focused.focusRing)
                        focused.focusRing.focus_first()
                        return True

            elif event.key.keysym.sym == sdl2.SDLK_ESCAPE:
                # Focus up into previous FocusRing on stack
                self.pop_focus_ring()

                oldFocusRing = self.get_focus_ring()
                assert(oldFocusRing is not None)
                oldFocusRing.focus(oldFocusRing.get_focus())
                return True

            elif event.key.keysym.sym == sdl2.SDLK_TAB:
                # TAB focuses next control in focus ring
                # Shift+TAB focuses previous control

                focusRing = self.get_focus_ring()
                assert(focusRing is not None)

                if event.key.keysym.mod & sdl2.KMOD_LCTRL:
                    # Ctrl+TAB inserts a tab character - we handle this in the TextArea class
                    pass
                else:
                    if event.key.keysym.mod & sdl2.KMOD_SHIFT:  # if shift was also held
                        if focusRing.focus_previous():
                            return True  # event was handled
                    else:
                        if focusRing.focus_next():
                            return True  # event was handled
                
        return handled
    

    def draw(self):
        if self._content:
            self._content.draw()


    def push_focus_ring(self, focusRing):
        assert(focusRing is not None)
        self.focus_stack.append(focusRing)


    def pop_focus_ring(self):
        if len(self.focus_stack) > 1:
            return self.focus_stack.pop()
        return None


    def get_focus_ring(self):
        return self.focus_stack[-1] if len(self.focus_stack) > 0 else None


    def get_focus(self):
        return self._focused_control
    
    
    def set_focus(self, control, focus_it=True):
        assert(control is not None and isinstance(control, GUIControl))

        if focus_it:
            # Can't focus on a control that can't be focused.
            # @shouldn't this happen automatically?

            if not control.can_focus:
                return False
        
            # If another control has focus, then remove focus from it.
            if focus_it and \
                self._focused_control is not None and \
                self._focused_control != control:

                    self._focused_control._set_focus(False)
                    self._focused_control = None

            self._focused_control = control
            
            # containing_ring = control.containing_focus_ring()
            # if containing_ring is not None:
            #     currentFocusRing = self.focus_stack[-1] if len(self.focus_stack) > 0 else None

            #     if currentFocusRing != containing_ring:
            #         self.focus_stack.append(containing_ring)
                    
            return self._focused_control._set_focus(True)
        else:
            # Make sure it's not focused.
            if self._focused_control == control:
                self._focused_control = None
            return control._set_focus(False)
        

    def save(self):        
        utc_now = datetime.datetime.now(pytz.utc)
        local_timezone = get_localzone()
        local_now = utc_now.astimezone(local_timezone)

        print("Saving GUI...")
        with open("aish_workspace.json", "w") as f:
            gui_json = {
                "saved_at_utc": utc_now.isoformat(),
                "saved_at_local": local_now.isoformat(),
                "gui": self.__json__()
            }
            json.dump(gui_json, f, indent=2, cls=GUI.JSONEncoder)
        print("GUI saved.")


    def load(self):
        bak_content = self._content
        bak_focused_control = self._focused_control
        self.focus_stack = []

        print("Loading GUI...")
        try:
            with open("aish_workspace.json", "r") as f:
                gui_json = json.load(f)
                content_json = gui_json["gui"]["content"]
                gui_class = GUI.control_class(content_json["class"])
                self._content = gui_class.from_json(content_json, gui=self, renderer=self.renderer, font_manager=self.font_manager)
                self.push_focus_ring(self._content.focusRing)

                focusRing = self.get_focus_ring()
                assert(focusRing is not None)
                focusRing.focus_first()

        except Exception as e:
            print("Error loading GUI. Exception: ", str(e))
            self._content = bak_content
            self._focused_control = bak_focused_control
            return False
        
        print("GUI loaded.")
        return True

#===============================================================================
class GUIControl:
    def __init__(self, can_focus=True, x=0, y=0, w=20, h=20, **kwargs):
        self.gui = kwargs.get('gui')
        self.renderer = kwargs.get('renderer')
        self.font_manager = kwargs.get('font_manager')
        self.draw_bounds = kwargs.get('draw_bounds', False)

        assert(self.gui)
        assert(self.renderer)
        assert(self.font_manager)

        self.can_focus = can_focus
        self.parent = None
        self.set_bounds(x, y, w, h)
        self.containing_focus_ring = None


    def has_focus(self):
        return self.gui.get_focus() == self
    

    def set_bounds(self, x, y, w, h):
        if hasattr(self, "bounding_rect"):
            self.bounding_rect.x = x
            self.bounding_rect.y = y
            self.bounding_rect.w = w
            self.bounding_rect.h = h
        else:
            self.bounding_rect = sdl2.SDL_Rect(x, y, w, h)


    @classmethod
    def from_json(cls, json, **kwargs):
        assert(json["class"] == cls.__name__)

        if "bounding_rect" in json:
            x, y, w, h = json["bounding_rect"]
            kwargs["x"] = x
            kwargs["y"] = y
            kwargs["w"] = w
            kwargs["h"] = h
            
        instance = cls(**kwargs)
        return instance


    def __json__(self):
        json = {}
        json["class"] = self.__class__.__name__
        json["bounding_rect"] = (self.bounding_rect.x, self.bounding_rect.y, self.bounding_rect.w, self.bounding_rect.h)
        return json

    # In local coordinates (relative to parent)
    def get_position(self):
        return (self.bounding_rect.x, self.bounding_rect.y)


    # In local coordinates (relative to parent)
    def set_position(self, x, y):
        self.bounding_rect = sdl2.SDL_Rect(x,
                                           y,
                                           self.bounding_rect.w,
                                           self.bounding_rect.h)


    def get_size(self):
        return (self.bounding_rect.w, self.bounding_rect.h)


    def set_size(self, w, h, updateLayout=True):
        self.bounding_rect = sdl2.SDL_Rect(self.bounding_rect.x,
                                           self.bounding_rect.y,
                                           w,
                                           h)
        if updateLayout:
            self.updateLayout()
            if self.parent is not None:
                self.parent.updateLayout()
        

    def updateLayout(self):
        pass

    
    def get_world_rect(self):
        if self.parent:
            parent_rect = self.parent.get_world_rect()
            return sdl2.SDL_Rect(parent_rect.x + self.bounding_rect.x,
                                 parent_rect.y + self.bounding_rect.y,
                                 self.bounding_rect.w,
                                 self.bounding_rect.h)
        else:
            return self.bounding_rect
        

    def _set_focus(self, has_focus):
        if self.can_focus:
            if self.has_focus() and self.parent and has_focus == False:
                self.parent.focused_child = None  # @todo still need this? GUI should handle this @todo
            return True
        else:
            return False


    def handle_event(self, event):
        return self.parent_handle_event(event)
    

    def parent_handle_event(self, event):
        # Pass unhandled events up the runtime child/parent hierarchy.
        if self.parent:
            return self.parent.handle_event(event)
        else:
            return False


#===============================================================================
class GUIContainer(GUIControl):
    @classmethod
    def from_json(cls, json, **kwargs):
        assert(json["class"] == cls.__name__)
        gui = kwargs.get('gui')

        instance = gui.create_control(json["class"], **kwargs)
        instance.set_bounds(*json["bounding_rect"])

        for child_json in json["children"]:
            child_class = GUI.control_class(child_json["class"])
            instance.add_child(child_class.from_json(child_json, **kwargs))

        if "layout" in json:
            layout_class_name = json["layout"]
            if layout_class_name == "ColumnLayout":
                instance.set_layout(ColumnLayout())
        return instance
    

    def __init__(self, children=None, layout=None, **kwargs):
        super().__init__(**kwargs)
        self.draw_bounds = False  #kwargs.get('draw_bounds', True)
        
        self.children = children if children is not None else []

        self.set_layout(layout)
        self.focusRing = FocusRing(gui=self.gui)


    def __json__(self):
        json = super().__json__()
        json["class"] = self.__class__.__name__
        json["layout"] =  self.layout.__class__.__name__ if self.layout else None
        json["children"] =  [child.__json__() for child in self.children]
        return json


    def set_layout(self, layout):
        self.layout = layout
        if layout is not None:
            self.layout.set_container(self)
            if self.children:
                self.updateLayout()


    def draw(self):
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

        # Draw children @test drawinb bounnds after
        for child in self.children:
            child.draw()


    def get_children(self):
        return self.children if self.children else []


    def add_child(self, child, add_to_focus_ring=True):
        child.parent = self
        self.children.append(child)

        self.updateLayout()

        child_rect_wrt_my_parent = sdl2.SDL_Rect(child.bounding_rect.x + self.bounding_rect.x,
                                                 child.bounding_rect.y + self.bounding_rect.y,
                                                 child.bounding_rect.w,
                                                 child.bounding_rect.h)
        self.bounding_rect = rect_union(self.bounding_rect, child_rect_wrt_my_parent)
        
        if add_to_focus_ring:
            self.focusRing.add(child)
            self.focusRing.focus(child)


    def remove_child(self, child):
        child.parent = None
        self.children.remove(child)
        self.updateLayout()


    def updateLayout(self):
        if self.layout is not None:
            self.layout.update()

        self.sizeToChildren()

        if self.parent is not None:
            self.parent.updateLayout()


    def sizeToChildren(self):
        # @todo DRY
        INSET_X = 1
        INSET_Y = 1

        if self.children:
            w = max([child.bounding_rect.x + child.bounding_rect.w for child in self.children])
            h = max([child.bounding_rect.y + child.bounding_rect.h for child in self.children])
            self.set_size(w + INSET_X, h + INSET_Y, updateLayout=False)


    def handle_event(self, event):
        return self.parent_handle_event(event)
    

GUI.register_control_type("GUIContainer", GUIContainer)
GUI.register_control_type("GUIControl", GUIControl)
