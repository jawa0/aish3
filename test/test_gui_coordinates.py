from dotenv import load_dotenv
load_dotenv()

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui import GUI, GUIContainer, GUIControl
from session import Session


class TestGUICoordinateTransforms(unittest.TestCase):
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


    def test_view_to_world_and_back(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        c = GUIControl(gui=g, x=5, y=7, w=200, h=30)
        g.content().add_child(c)

        vx0, vy0 = 150, 160
        wx, wy = g.view_to_world(vx0, vy0)
        vx1, vy1 = g.world_to_view(wx, wy)

        self.assertEqual((vx0, vy0), (vx1, vy1))


    def test_coordinates(self):
        s = Session()
        g = GUI(renderer=None, font_descriptor=None, client_session=s)

        parent = g.content()

        c0 = GUIControl(gui=g, x=5, y=7, w=200, h=30)
        parent.add_child(c0)
        wr0 = c0.get_world_rect()
        lr0 = c0.bounding_rect

        # We've added c0 to the GUI.content(), so we expect that its local coordinates
        # relative to its parent (5, 7) are the same as its world coordinates.

        self.assertEquals((wr0.x, wr0.y), (5, 7))

        # Since we haven't moved the viewport, we expect its view coordinates to
        # be the same as its world coordinates.

        vr0 = c0.get_view_rect()
        self.assertEquals(vr0, wr0)

        # Now, let's add another control. This will cause a call to sizeToChildren(),
        # which will update the parent's bounding_rect. Make sure all updates are valid.

        # First, check again that since we haven't moved the viewport, we expect its
        # view coordinates to bet the same as its world coordinates.

        vx1, vy1 = 11, 13
        wx1, wy1 = g.view_to_world(vx1, vy1)
        self.assertEqual((wx1, wy1), (vx1, vy1))

        # Now, let's add it to the content.
        x1, y1 = parent.world_to_local(wx1, wy1)
        self.assertEqual((x1, y1), (6, 6))  # (11, 13) - (5, 7)

        c1 = GUIControl(gui=g, x=x1, y=y1, w=200, h=30)
        print(f'*** c1 coordinates, before adding to parent: {c1.bounding_rect}')
        parent.add_child(c1)
        print(f'*** c1 coordinates, after adding to parent: {c1.bounding_rect}')

        # Verify that c1's world position is where we wanted it.
        
        wr1 = c1.get_world_rect()
        self.assertEquals((wr1.x, wr1.y), (wx1, wy1))


if __name__ == '__main__':
    unittest.main()