import string
import unittest

from pin_generator import pin_gen


class TestServercoms(unittest.TestCase):
    def setUp(self):
        self.pin_gen = pin_gen(length=4)

    def test_verify_pin(self):
        pin = self.pin_gen.generate_pin(alphabet=True)
        self.assertEqual(self.pin_gen.verify_pin(pin), True, "Pin-gen could not verify the just generated pin!")

    def test_alphabet_option(self):
        pin = self.pin_gen.generate_pin(alphabet=False)
        alp = string.ascii_uppercase
        self.assertEqual(alp in pin, False, "Letters in pin " + pin)


if __name__ == '__main__':
    unittest.main()
