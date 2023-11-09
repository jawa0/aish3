from dotenv import load_dotenv
load_dotenv()

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui import GUI, GUIContainer, GUIControl
from session import Session
from text_edit_buffer import TextEditBuffer


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
        # print(f'test_parented_control_coordinates')
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        # print('create GUIContainer c0')
        c0 = GUIContainer(gui=g)
        # print('add c0 to g.content()')
        g.content().add_child(c0)
        c0.set_position(5, 7)

        # print('create GUIControl c')
        c = GUIControl(gui=g)
        # print('add c to c0')
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


    def test_parented_control_coordinates_negative(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        c0 = GUIContainer(gui=g)
        g.content().add_child(c0)
        c0.set_position(-2, -3)

        c = GUIControl(gui=g)
        c0.add_child(c)
        c.set_position(-1, -2)

        r = c.bounding_rect
        self.assertEqual(r.x, -1)
        self.assertEqual(r.y, -2)

        wr = c.get_world_rect()
        self.assertEqual(wr.x, -3)
        self.assertEqual(wr.y, -5)

        vr = c.get_view_rect()
        self.assertEqual(vr.x, -3)
        self.assertEqual(vr.y, -5)


    def test_size_to_children_0(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        cont = GUIContainer(gui=g)
        g.content().add_child(cont)

        c0 = GUIControl(gui=g)
        cont.add_child(c0)
        c0.set_position(5, 7)
        c0.set_size(10, 20, updateLayout=False)

        r_c0 = c0.bounding_rect
        self.assertEqual(r_c0.x, 5)
        self.assertEqual(r_c0.y, 7)

        c1 = GUIControl(gui=g)
        cont.add_child(c1)
        c1.set_position(31, 37)
        c1.set_size(10, 20, updateLayout=False)

        r_c1 = c1.bounding_rect
        self.assertEqual(r_c1.x, 31)
        self.assertEqual(r_c1.y, 37)

        self.assertEqual(cont.bounding_rect.x, 0)
        self.assertEqual(cont.bounding_rect.y, 0)

        # !!!!
        cont.sizeToChildren(inset_x=0, inset_y=0)
        r_cont = cont.bounding_rect

        self.assertEqual(r_cont.x, r_c0.x)
        self.assertEqual(r_cont.y, r_c0.y)


    def test_world_to_view_00(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        wx, wy = 0, 0
        vx, vy = g.world_to_view(wx, wy)
        self.assertEqual((vx, vy), (wx, wy))


    def test_world_to_view_01(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        wx, wy = 5, 7
        vx, vy = g.world_to_view(wx, wy)
        self.assertEqual((vx, vy), (wx, wy))


    def test_world_to_view_02(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        wx, wy = -5, -7
        vx, vy = g.world_to_view(wx, wy)
        self.assertEqual((vx, vy), (wx, wy))


    def test_world_to_view_03(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        g.set_view_pos(5, 7)
        wx, wy = 0, 0
        vx, vy = g.world_to_view(wx, wy)
        self.assertEqual((vx, vy), (-5, -7))


    def test_view_to_world_00(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        vx, vy = 0, 0
        wx, wy = g.view_to_world(vx, vy)
        self.assertEqual((wx, wy), (vx, vy))

    
    def test_view_to_world_01(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        vx, vy = 5, 7
        wx, wy = g.view_to_world(vx, vy)
        self.assertEqual((wx, wy), (vx, vy))


    def test_view_to_world_02(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        vx, vy = -5, -7
        wx, wy = g.view_to_world(vx, vy)
        self.assertEqual((wx, wy), (vx, vy))


    def test_view_to_world_03(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        g.set_view_pos(5, 7)
        wx, wy = g.view_to_world(0, 0)
        self.assertEqual((wx, wy), (5, 7))


    def test_view_to_world_04(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        g.set_view_pos(-5, -7)
        wx, wy = g.view_to_world(0, 0)
        self.assertEqual((wx, wy), (-5, -7))


    def test_view_to_world_05(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        g.set_view_pos(5, 7)
        wx, wy = g.view_to_world(5, 7)
        self.assertEqual((wx, wy), (10, 14))


    def test_view_to_world_06(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        g.set_view_pos(-5, -7)
        wx, wy = g.view_to_world(-5, -7)
        self.assertEqual((wx, wy), (-10, -14))


if __name__ == '__main__':
    unittest.main()