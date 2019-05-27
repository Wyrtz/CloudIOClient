import os
the_prime = 231584178474632390847141970017375815706539969331281128078915168015826259277639
byteorder = 'big'
signed = 'False'


class FFInt:
    """data type for representing whole numbers within a finite field"""

    def __init__(self, value: int, prime: int=the_prime):
        """
        Args:
            value: the value in the Finite Field
            prime: the (filed) prime
        """

        self.value = value % prime
        self.prime = prime

    def is_ffint_of_same_field(self, other):
        if type(other) is not FFInt:
            raise TypeError
        other: FFInt = other
        if other.prime != self.prime:
            raise(AssertionError, ("Not same field! " + str(self.prime) + "!=" + str(other.prime)))
        return other

    def __add__(self, other):
        other = self.is_ffint_of_same_field(other)
        return FFInt((self.value + other.value) % self.prime, self.prime)

    def __sub__(self, other):
        other = self.is_ffint_of_same_field(other)
        return FFInt(self.value - other.value % self.prime, self.prime)

    def __mul__(self, other):
        other = self.is_ffint_of_same_field(other)
        return FFInt((self.value * other.value) % self.prime, self.prime)

    def __truediv__(self, other):
        other = self.is_ffint_of_same_field(other)
        if other.value is 0:
            raise AssertionError
        return self * other.inverse

    def inverse(self):
        """The inverse of self.value in this field

        Returns:
            FFInt: the inversed FFint
        """
        def extended_euclidean_algorithm(a: int, b: int) -> tuple:
            """
            perform the extended euclidean algorithm: (upgraded greatest common divisor algorithm)
            Args:
                a: first number
                b: second number

            Returns:
                tuple: a tuple with the (inverse of a, 1, the divisor)

            """
            if abs(b) > abs(a):
                (x, y, d) = extended_euclidean_algorithm(b, a)
                return (y, x, d)

            if abs(b) == 0:
                return (1, 0, a)

            x1, x2, y1, y2 = 0, 1, 1, 0
            while abs(b) > 0:
                q, r = divmod(a, b)
                x = x2 - q * x1
                y = y2 - q * y1
                a, b, x2, x1, y2, y1 = b, r, x1, x, y1, y

            return (x2, y2, a)
        x, y, d = extended_euclidean_algorithm(self.value, self.prime)
        return FFInt(x, self.prime)

    def __iadd__(self, other):
        other = self.is_ffint_of_same_field(other)
        return self + other

    def __isub__(self, other):
        other = self.is_ffint_of_same_field(other)
        return self - other

    def __imul__(self, other):
        other = self.is_ffint_of_same_field(other)
        return self * other

    def __idiv__(self, other):
        other = self.is_ffint_of_same_field(other)
        return self / other

    def __eq__(self, other):
        if type(other) is int:
            return (other % self.prime) == self.value
        other = self.is_ffint_of_same_field(other)
        return self.value == other.value

    def __pow__(self, power):
        power = self.is_ffint_of_same_field(power)
        return FFInt(pow(self.value, power.value, self.prime), self.prime)

    def __str__(self):
        return str(self.value)

    def __neg__(self):
        return FFInt(-self.value % self.prime, self.prime)

    def __repr__(self):
        return str(self.value)


class Polynomial:
    """Data type to represent polynomials"""

    def __init__(self, secret: int, degree: int, prime: int = the_prime) -> None:  # 2**256 < the_prime < 2**257
        """
        Args:
            secret: the secret
            degree: the degree of the polynomial
            prime: the prime of the filed we are operation within
        """
        self.prime = prime
        self.degree = degree
        if type(secret) == bytes:
            secret = int.from_bytes(secret, byteorder)
        assert secret < prime, "Secret should be smaller than prime"
        assert degree < 128, "Degree can at most be 127"
        self.coefficients = [FFInt(secret, prime)] + [FFInt(int.from_bytes(os.urandom(32), byteorder) % prime,
                                                            prime) for _ in range(degree)]

    def evaluate_point(self, x_val: int) -> (int, int):
        """
        Get the y coordinate the given x value produces when evaluating

        Args:
            x_val: the x value to evaluate

        Returns:
            (int, int): the x value as provided along with the y coordinate
        """

        y_val = FFInt(0, self.prime)
        for pwr in range(0, len(self.coefficients)):
            y_val += (FFInt(x_val, self.prime) ** FFInt(pwr, self.prime)) * self.coefficients[pwr]
        return x_val, y_val

    def __str__(self):
        s = str(self.coefficients[0].value) + "x^0"
        for idx in range(1, len(self.coefficients)):
            s += "+" + str(self.coefficients[idx].value) + "x^" + str(idx)
        return s


def recover_secret(points: list, prime: int=the_prime) -> bytes:
    """
    Recover a Shamir Secret Sharing Scheme secret from the given points

    Args:
        points: the points to recover the secret
        prime: the prime of the field we are looking for the secret in

    Returns:
        bytes: the recovered key
    """
    t = points[0][2]
    for point in points: assert point[2] == t
    assert len(points) > t
    k = t + 1

    points_ = points[:k]
    x_vals, y_vals = zip(*[(FFInt(point[0], prime), point[1]) for point in points_])

    K = FFInt(0, prime)
    for idx in range(k):
        yi = y_vals[idx]
        PI = FFInt(1, prime)
        for jdx in range(k):
            if jdx == idx: continue
            xi = x_vals[idx]
            xj = x_vals[jdx]
            PI *= xj / (xj - xi)
        K += yi * PI
    return K.value.to_bytes(32, byteorder=byteorder, signed=False)


def split_secret(secret: bytes, threshold: int, n: int) -> list:
    """
    Split a secret into parts

    Args:
        secret: The secret to be split into pieces
        threshold: the number of points one can have without being able to recover the secret
        n: amount of shares to split the secret into

    Returns:
        list: a list of shares (points) representing the split secret
    """

    assert len(secret) == 32, f"Secret should be 256 bits long but was {len(secret)}"
    p = Polynomial(int.from_bytes(secret, byteorder), threshold)
    return [(point[0], point[1], threshold) for point in [p.evaluate_point(idx) for idx in range(1, n + 1)]]
