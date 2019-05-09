import secrets
import string
from profanity import profanity


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
        if profanity.contains_profanity(self.pin):
            return self.generate_pin(alphabet)
        return self.pin

    def verify_pin(self, pin):
        return secrets.compare_digest(pin, self.pin)