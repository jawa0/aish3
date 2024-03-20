# Copyright 2023-2024 Jabavu W. Adams

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
    def __init__(self, text="", tab_spaces=4, **kwargs):
        self.TEXT_BUFFER = text
        self.TAB_SPACES = tab_spaces
        
        # @note: This code is contradicts the comment abocve about not moving point to the end.
        # I'm not sure why I did this. Trying to get automated test working again, and a test
        # of POINT after creation is failing due to this. I'm going to change it back to setting
        # POINT to 0 and see how the app behaves... 2023-11-05
        
        # self.POINT = len(text)
        self.POINT = 0

        # @note: POINT has no knowledge of expanded tabs. It's an index into the
        # un-expanded TEXT_BUFFER. It's between 0 and len(TEXT_BUFFER). @note that
        # this means it can point one char past the end of the buffer.
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
        """
        Replace the tab characters in the given text with the appropriate number of space characters.

        Tab width is important for maintaining consistent visual representation in different text editors. 

        Parameters:
        text (str): The text to process.

        Returns:
        str: The passed text, but with tab characters replaced by the appropriate number of spaces.

        See Also:
        get_tab_spaces: Method to get the current number of spaces per tab.
        set_tab_spaces: Method to set the number of spaces to be used per tab.
        """
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

        lines = self.get_lines(expand_tabs=False)
        cumulative_length = 0
        for row, line in enumerate(lines):
            line_length = len(line) + 1   # +1 for the '\n' character
            if cumulative_length <= point < cumulative_length + line_length:
                col = point - cumulative_length
                return row, col
            cumulative_length += line_length
        return len(lines) - 1, line_length
    

    def get_point(self):
        return self.POINT


    def set_point(self, point):
        # Need to check if we changed rows. If not then update desired_col.
        # If so, don't update it. This is because we use desired_col to
        # keep track of which column we should be on when moving up and down,
        # across lines with different lengths.

        before_row, _ = self.get_row_col(self.POINT)
        self.POINT = min(max(0, point), len(self.TEXT_BUFFER))
        after_row, after_col = self.get_row_col(self.POINT)

        if after_row == before_row:
            self.desired_col = after_col

        # print(f'POINT = {self.POINT} row = {after_row}  col = {after_col}  desired_col = {self.desired_col}')            


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
            self.set_point(self.POINT - 1)
            row, col = self.get_row_col(self.POINT)
            self.desired_col = col


    def move_point_word_left(self):
        i = self._prev_word_point(self.POINT)
        self.set_point(i)


    def move_point_word_right(self):    # @todo handle all whitespace and runs of it
        i = self._next_word_point(self.POINT)
        self.set_point(i)


    def move_point_start_of_line(self):
        row, col = self.get_row_col(self.POINT)
        self.set_point(self.POINT - col)


    def move_point_end_of_line(self):
        row, col = self.get_row_col(self.POINT)
        line = self.get_line(row)
        self.set_point(self.POINT + len(line) - col)


    def move_point_right(self):
        if self.POINT < len(self.TEXT_BUFFER):
            self.set_point(self.POINT + 1)
            row, col = self.get_row_col(self.POINT)
            self.desired_col = col


    def move_point_up(self):
        row, col = self.get_row_col(self.POINT)
        if row > 0:
            from_line_length = len(self.get_line(row))

            to_line = self.get_line(row - 1, expand_tabs=False)
            to_line_length = len(to_line)
            to_col = min(self.desired_col, to_line_length)

            new_point = self.POINT - col - 1 - len(to_line) + to_col  # The -1 is for the newline char
            self.set_point(new_point)

    
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


    # Find POINT for the start of the next word (to the right) of the given point.
    def _next_word_point(self, point):
        # Check characters from point forward
        while point < len(self.TEXT_BUFFER):
            # If we encounter a non-whitespace character immediately, continue scanning
            if not self.TEXT_BUFFER[point].isspace():
                point += 1
            else:
                # When we encounter our first whitespace, start scanning for the next non-whitespace character
                while point < len(self.TEXT_BUFFER) and self.TEXT_BUFFER[point].isspace():
                    point += 1
                
                # If a non-whitespace character is found after a whitespace character,
                # return its position
                if point < len(self.TEXT_BUFFER):
                    return point

        # Return the end of the buffer if no non-whitespace character is found
        return len(self.TEXT_BUFFER)


    # Find POINT for the start of the previous word (to the left) of the given point. If the
    # given point is inside of a word, return the start of that word.
    def _prev_word_point(self, point):
        if point == len(self.TEXT_BUFFER):
            point -= 1
        elif point == 0:
            return 0
        
        started_on_space = self.TEXT_BUFFER[point].isspace()
        past_end_of_word = not started_on_space and not self.TEXT_BUFFER[point - 1].isspace()

        # Check characters from point backward
        point -= 1
        while point > 0:
            # If we aren't in a word, or haven't hit the rightmost boundary of a word,
            # then continue scanning until we hit a non-blank character
            if not past_end_of_word:
                if not self.TEXT_BUFFER[point].isspace():
                    past_end_of_word = True
                else:
                    point -= 1
            else:
                # Now we are in a word, so stop at the first (left-most) blank character
                # we find.
                if self.TEXT_BUFFER[point].isspace():
                    if point < len(self.TEXT_BUFFER) - 1:
                        return point + 1
                    else:
                        return point
                else:
                    point -= 1
                
        # Return the start of the buffer if no non-whitespace character is found
        return 0
