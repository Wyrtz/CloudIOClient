import string
import unittest

from pin_generator import pin_gen


class TestServercoms(unittest.TestCase):
    """Class for unittesting the pin_generator.py module"""

    def setUp(self):
        self.pin_gen = pin_gen(length=4)

    def test_verify_pin(self):
        """test the modules ability to verify the generated pin"""
        pin = self.pin_gen.generate_pin(alphabet=True)
        self.assertEqual(self.pin_gen.verify_pin(pin), True, "Pin-gen could not verify the just generated pin!")

    def test_alphabet_option(self):
        """test the modules alphabet function"""
        pin = self.pin_gen.generate_pin(alphabet=False)
        alp = string.ascii_uppercase
        self.assertNotIn(alp, pin, "Letters in pin " + pin)
