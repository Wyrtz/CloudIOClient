import unittest
from resources import globals


class TestGlobals(unittest.TestCase):
    """Class for unittesting the globals.py module"""

    def setUp(self):
        pass

    def test_list_diff(self):
        """Test the functionality of list_diff from globals behaves as expected"""
        list_1 = [1, 2, 3, 4]
        list_2 = [3, 4, 5, 6]
        elements_not_in_2 = globals.get_list_difference(list_1, list_2)
        elements_not_in_1 = globals.get_list_difference(list_2, list_1)
        self.assertEqual(elements_not_in_2, [1, 2])
        self.assertEqual(elements_not_in_1, [5, 6])
