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


class TextEditBuffer(object):

    # When constructing TextEditBuffer with non-empty text,
    # POINT is not moved to the end. It will be 0.
    def __init__(self, initial_text="", tab_spaces=4, **kwargs):
        self.TEXT_BUFFER = initial_text
        self.TAB_SPACES = tab_spaces

        # @note: POINT has no knowledge of expanded tabs. It's an index into the
        # un-expanded TEXT_BUFFER. It's between 0 and len(TEXT_BUFFER). @note that
        # this means it can point one char past the end of the buffer.
        self.POINT = len(initial_text)
        self.MARK = None
        self.desired_col = 0


    def insert(self, text='\n'):
        self.TEXT_BUFFER = self.TEXT_BUFFER[:self.POINT] + text + self.TEXT_BUFFER[self.POINT:]
        self.set_point(self.POINT + len(text))
        
        _, col = self.get_row_col(self.POINT)
        self.desired_col = col


    def delete_char(self):
        self.TEXT_BUFFER = self.TEXT_BUFFER[:self.POINT - 1] + self.TEXT_BUFFER[self.POINT:]
        self.set_point(self.POINT - 1)
        
        _, col = self.get_row_col(self.POINT)
        self.desired_col = col


    def get_text(self, expand_tabs=False):
        if expand_tabs:
            return self.expand_tabs(self.TEXT_BUFFER)
        else:
            return self.TEXT_BUFFER

    
    def set_text(self, text):
        self.TEXT_BUFFER = text
        self.set_point(len(text))
        self.clear_mark()

        
    def expand_tabs(self, text):
        return text.replace('\t', ' ' * self.TAB_SPACES)
    

    def get_line(self, row, expand_tabs=True):
        lines = self.get_lines(expand_tabs=expand_tabs)
        if 0 <= row < len(lines):
            if expand_tabs:
                return self.expand_tabs(lines[row])
            else:
                return lines[row]
        raise IndexError("Row index out of range")
    

    # @return a list of strings, one for each line. The line strings do not contain
    # terminating newline characters.

    def get_lines(self, expand_tabs=True):
        if expand_tabs:
            return self.get_text(expand_tabs=True).split('\n')
        else:
            return self.TEXT_BUFFER.split('\n')


    def get_tab_spaces(self):
        return self.TAB_SPACES


    def set_tab_spaces(self, num_spaces):
        self.TAB_SPACES = num_spaces


    def count_tab_expanded_spaces(self, string):
        count = 0
        for char in string:
            if char == '\t':
                count += self.TAB_SPACES
            else:
                count += 1
        return count
    
    
    def get_row_col(self, point):
        row = None
        col = None

        lines = self.get_lines(expand_tabs=False)  # Do not expand tabs!
        cumulative_length = 0
        for row, line in enumerate(lines):
            line_length = len(line) + 1   # +1 for the '\n' character
            if cumulative_length <= point < cumulative_length + line_length:
                col = point - cumulative_length
                return row, col
            cumulative_length += line_length
        return len(lines) - 1, line_length
    
        print('*********')
    

    def get_point(self):
        return self.POINT


    def set_point(self, point):
        self.POINT = min(max(0, point), len(self.TEXT_BUFFER))


    def set_mark(self, mark_position=None):
        self.MARK = self.POINT if mark_position is None else mark_position


    def clear_mark(self):
        self.MARK = None


    def get_mark(self):
        return self.MARK


    def get_selection(self):
        if self.MARK is None:
            return None
        else:
            return min(self.POINT, self.MARK), max(self.POINT, self.MARK)
        

    def delete_selection(self):
        if self.MARK is not None:
            start, end = self.get_selection()
            self.TEXT_BUFFER = self.TEXT_BUFFER[:start] + self.TEXT_BUFFER[end:]
            self.set_point(start)
            self.clear_mark()
            
    def move_point_left(self):
        if self.POINT > 0:
            self.POINT -= 1
            row, col = self.get_row_col(self.POINT)
            self.desired_col = col
            print(f'POINT = {self.POINT} row = {row}  col = {col}  desired_col = {self.desired_col}')


    def move_point_word_left(self):
        # If we are inside a word, then move to the beginning of the current word.
        # If we are at the start of a word, move to the start of the previous word.
        # If there are no previous words, move to the start of the buffer.

        # If we're already at the start of the buffer, do nothing.
        if self.POINT == 0:
            return

        # Move back from the current position until a space or the start of the buffer is found.
        while self.POINT > 0 and self.TEXT_BUFFER[self.POINT - 1].isalnum():
            self.POINT -= 1
        self.POINT += 1

        # # If we're still within the buffer and at a space, move back to find the start of the previous word.
        # while self.POINT > 0 and not self.TEXT_BUFFER[self.POINT - 1].isalnum():
        #     self.POINT -= 1

        # # If we're at the start of a word, move back until a space or the start of the buffer is found.
        # while self.POINT > 0 and self.TEXT_BUFFER[self.POINT - 1].isalnum():
        #     self.POINT -= 1


    def move_point_right(self):
        if self.POINT < len(self.TEXT_BUFFER):
            self.POINT += 1
            row, col = self.get_row_col(self.POINT)
            self.desired_col = col
            print(f'POINT = {self.POINT} row = {row}  col = {col}  desired_col = {self.desired_col}')


    def move_point_up(self):
        row, col = self.get_row_col(self.POINT)
        if row > 0:
            from_line_length = len(self.get_line(row))

            to_line = self.get_line(row - 1, expand_tabs=False)
            to_line_length = len(to_line)
            to_col = min(self.desired_col, to_line_length)

            new_point = self.POINT - col - 1 - len(to_line) + to_col  # The -1 is for the newline char
            self.set_point(new_point)
            print(f'POINT = {self.POINT} row = {row}  col = {col}')

    
    def move_point_to_start(self):
        self.set_point(0)


    def move_point_to_end(self):
        self.set_point(len(self.TEXT_BUFFER))


    def move_point_down(self):
        row, col = self.get_row_col(self.POINT)
        num_rows = len(self.get_lines())
        if row < num_rows - 1:
            from_line_length = len(self.get_line(row, expand_tabs=False))

            to_line = self.get_line(row + 1)
            to_line_length = len(to_line)
            to_col = min(self.desired_col, to_line_length)

            new_point = self.POINT - col + from_line_length + 1 + to_col  # +1 is for the newline char
            self.set_point(new_point)
            return True   

        return False
