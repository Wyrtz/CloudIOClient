import secrets
import string


class pin_gen:

    def __init__(self, length):
        self.length = length
        self.pin = None # Todo: Hash the pin ?

    def generate_pin(self, alphabet=True):
        dict = string.digits
        if alphabet:
            dict += string.ascii_uppercase
        secGen = secrets.SystemRandom()
        self.pin = "".join(secGen.sample(dict, self.length))
        return self.pin

    def verify_pin(self, pin):
        return secrets.compare_digest(pin, self.pin)

gen = pin_gen(4)
pin = gen.generate_pin(alphabet=True)
print(pin)
print(gen.verify_pin(pin))
print(gen.pin) # ToDo: is this a problem ?
