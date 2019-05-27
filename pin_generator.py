import secrets
import string
from profanity import profanity


class pin_gen:
    """Class for creating and verifying random alphanumerical pin-codes"""

    def __init__(self, length: int) -> None:
        """
        Args:
            length: the length of the pincode to be generated
        """
        self.length = length
        self.pin = None  # Todo: Hash the pin ?

    def generate_pin(self, alphabet: bool = True) -> str:
        """
        method for generating a random pin
        Args:
            alphabet: whether or not the pin can contain capital letters

        Returns:
            str: a random pin code containing numbers and possible letters depending on argument input

        """
        dict = string.digits
        if alphabet:
            dict += string.ascii_uppercase

        secGen = secrets.SystemRandom()
        self.pin = "".join(secGen.sample(dict, self.length))
        if profanity.contains_profanity(self.pin):
            return self.generate_pin(alphabet)
        return self.pin

    def verify_pin(self, pin: str) -> bool:
        """
        Verifies whether or not the provided pin is the same as self.pin
        Args:
            pin: the pin to compare with self.pin

        Returns:
            bool: True if same pin, false otherwise
        """
        return secrets.compare_digest(pin, self.pin)
