import string
import random
# Todo: Random not crypto safe!

class pin_gen:

    def __init__(self, length):
        self.length = length
        self.pin = None

    def generate_pin(self, alphabet=True):
        pin = ""
        dict = string.digits
        if alphabet:
            dict += string.ascii_uppercase
        for i in range(self.length):
            pin += str(dict[random.randint(-1, len(dict)-1)])
        self.pin = pin
        return pin

    def verify_pin(self, pin):
        return pin == self.pin

gen = pin_gen(4)
pin = gen.generate_pin(alphabet=False)
print(pin)
print(gen.verify_pin(pin))
