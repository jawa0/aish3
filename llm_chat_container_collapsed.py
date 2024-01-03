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


import uuid
from gui import GUI, GUIContainer
from gui_layout import ColumnLayout
from label import Label


class LLMChatContainerCollapsed(GUIContainer):

  def __init__(self, layout=ColumnLayout(), **kwargs):
    super().__init__(**kwargs)
    self._uid = uuid.uuid4()

    self.draw_bounds = True

    # Add title and caption labels 
    self.title = Label(text="LLM Chat", **kwargs) 
    self.caption = Label(text="<caption>", **kwargs)

    # SourceGraph Cody suggestion:
    # super().__init__(children=[
    #   ColumnLayout(children=[
    #     self.title,
    #     self.caption  
    #   ])
    # ])

    super().add_child(self.title)
    super().add_child(self.caption)



  def set_caption(self, text):
    self.caption.set_text(text)


  def draw(self):
    super().draw()
