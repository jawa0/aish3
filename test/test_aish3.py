import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from text_edit_buffer import TextEditBuffer
from gui import GUI, GUIContainer, GUIControl
from session import Session


class TestTextEditBuffer(unittest.TestCase):
    def test_initial_point(self):
        obj = TextEditBuffer()
        self.assertEqual(obj.get_point(), 0)

    def test_construct_with_text(self):
        obj = TextEditBuffer("hello")
        self.assertEqual(obj.get_point(), 0)

    def test_insert_text(self):
        text = "some text"
        obj = TextEditBuffer()
        obj.insert(text)
        self.assertEqual(obj.get_point(), len(text))

    def test_set_point_valid_range(self):
        text = "some text"
        obj = TextEditBuffer(text)
        valid_point = len(text) // 2
        obj.set_point(valid_point)
        self.assertEqual(obj.get_point(), valid_point)

    def test_set_point_too_small(self):
        text = "some text"
        obj = TextEditBuffer(text)
        too_small_point = -1
        obj.set_point(too_small_point)
        self.assertEqual(obj.get_point(), 0)

    def test_set_point_too_large(self):
        text = "some text"
        obj = TextEditBuffer(text)
        too_large_point = len(text) + 1
        obj.set_point(too_large_point)
        self.assertEqual(obj.get_point(), len(text))

    def test_move_point_left_middle(self):
        text = "some text"
        obj = TextEditBuffer(text)
        middle_point = len(text) // 2
        obj.set_point(middle_point)
        obj.move_point_left()
        self.assertEqual(obj.get_point(), middle_point - 1)

    def test_move_point_left_start(self):
        text = "some text"
        obj = TextEditBuffer(text)
        obj.set_point(0)
        obj.move_point_left()
        self.assertEqual(obj.get_point(), 0)

    def test_move_point_right_middle(self):
        text = "some text"
        obj = TextEditBuffer(text)
        middle_point = len(text) // 2
        obj.set_point(middle_point)
        obj.move_point_right()
        self.assertEqual(obj.get_point(), middle_point + 1)

    def test_move_point_right_end(self):
        text = "some text"
        obj = TextEditBuffer(text)
        obj.set_point(len(text))
        obj.move_point_right()
        self.assertEqual(obj.get_point(), len(text))
        
    def test_get_row_col_valid_point(self):
        text = "some\ntext"
        obj = TextEditBuffer(text)
        point = 6
        expected_row, expected_col = 1, 1
        row, col = obj.get_row_col(point)
        self.assertEqual((row, col), (expected_row, expected_col))

    def test_get_row_col_point_beginning(self):
        text = "some\ntext"
        obj = TextEditBuffer(text)

        point = 0
        expected_row, expected_col = 0, 0
        row, col = obj.get_row_col(point)
        self.assertEqual((row, col), (expected_row, expected_col))

    def test_get_row_col_eol(self):
        text = "some\ntext"
        obj = TextEditBuffer(text)

        point = 4
        expected_row, expected_col = 0, 4
        row, col = obj.get_row_col(point)
        self.assertEqual((row, col), (expected_row, expected_col))

    def test_get_row_col_bol(self):
        text = "some\ntext"
        obj = TextEditBuffer(text)

        point = 5
        expected_row, expected_col = 1, 0
        row, col = obj.get_row_col(point)
        self.assertEqual((row, col), (expected_row, expected_col))

    def test_get_row_col_point_end(self):
        text = "some\ntext"
        obj = TextEditBuffer(text)

        point = len(text)
        expected_row, expected_col = 1, 4
        row, col = obj.get_row_col(point)
        self.assertEqual((row, col), (expected_row, expected_col))

    # def test_get_row_col_point_after_end(self):
    #     text = "some\ntext"
    #     obj = TextEditBuffer(text)

    #     point = len(text) + 1
    #     row, col = obj.get_row_col(point)
    #     self.assertEqual((row, col), (None, None))

    # def test_get_row_col_point_before_beginning(self):
    #     text = "some\ntext"
    #     obj = TextEditBuffer(text)

    #     point = -1
    #     row, col = obj.get_row_col(point)
    #     self.assertEqual((row, col), (None, None))

    def test_delete_char(self):
        obj = TextEditBuffer()
        obj.insert('hello world')
        obj.set_point(6)
        obj.delete_char()
        self.assertEqual(obj.get_text(), "helloworld")
        self.assertEqual(obj.get_point(), 5)


    def test_content_init_world_rect(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        r_content = g.content().bounding_rect
        self.assertEqual(r_content.x, 0)
        self.assertEqual(r_content.y, 0)

    
    def test_unparented_control_coordinates(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        c = GUIControl(gui=g)
        c.set_position(5, 7)

        r = c.bounding_rect
        self.assertEqual(r.x, 5)
        self.assertEqual(r.y, 7)

        wr = c.get_world_rect()
        self.assertEqual(wr.x, 5)
        self.assertEqual(wr.y, 7)

        vr = c.get_view_rect()
        self.assertEqual(vr.x, 5)
        self.assertEqual(vr.y, 7)


    def test_unparented_control_coordinates_negative(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        c = GUIControl(gui=g)
        c.set_position(-5, -7)

        r = c.bounding_rect
        self.assertEqual(r.x, -5)
        self.assertEqual(r.y, -7)

        wr = c.get_world_rect()
        self.assertEqual(wr.x, -5)
        self.assertEqual(wr.y, -7)

        vr = c.get_view_rect()
        self.assertEqual(vr.x, -5)
        self.assertEqual(vr.y, -7)
        

    def test_parented_control_coordinates(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        c0 = GUIContainer(gui=g)
        g.content().add_child(c0)
        c0.set_position(5, 7)

        c = GUIControl(gui=g)
        c0.add_child(c)
        c.set_position(5, 7)

        r = c.bounding_rect
        self.assertEqual(r.x, 5)
        self.assertEqual(r.y, 7)

        wr = c.get_world_rect()
        self.assertEqual(wr.x, 10)
        self.assertEqual(wr.y, 14)

        vr = c.get_view_rect()
        self.assertEqual(vr.x, 10)
        self.assertEqual(vr.y, 14)



if __name__ == '__main__':
    unittest.main()