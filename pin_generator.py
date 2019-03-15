import string
import random
# Todo: Random not crypto safe!

class pin_gen:

    def __init__(self, length):
        self.length = length

    def generate_pin(self, alphabet=True):
        pin = ""
        dict = string.digits
        if alphabet:
            dict += string.ascii_uppercase
        print(dict)
        for i in range(self.length):
            pin += str(dict[random.randint(-1, len(dict)-1)])
        return pin

gen = pin_gen(4)
print(gen.generate_pin())
