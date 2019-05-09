import os
the_prime = 231584178474632390847141970017375815706539969331281128078915168015826259277639
byteorder = 'big'
signed = 'False'


class FInt:
    def __init__(self, value, prime):
        self.value = value % prime
        self.prime = prime

    def is_fint(self, other):
        if type(other) is not FInt:
            raise TypeError
        other: FInt = other
        if other.prime != self.prime:
            raise AssertionError
        return other

    def __add__(self, other):
        other = self.is_fint(other)
        return FInt((self.value + other.value) % self.prime, self.prime)

    def __sub__(self, other):
        other = self.is_fint(other)
        return FInt(self.value - other.value % self.prime, self.prime)

    def __mul__(self, other):
        other = self.is_fint(other)
        return FInt((self.value * other.value) % self.prime, self.prime)

    def __truediv__(self, other):
        other = self.is_fint(other)
        if other.value is 0:
            raise AssertionError
        return self * other.inverse()

    def inverse(self):
        def extended_euclidean_algorithm(a, b):
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
        return FInt(x, self.prime)

    def __iadd__(self, other):
        other = self.is_fint(other)
        return self + other

    def __isub__(self, other):
        other = self.is_fint(other)
        return self - other

    def __imul__(self, other):
        other = self.is_fint(other)
        return self * other

    def __idiv__(self, other):
        other = self.is_fint(other)
        return self / other

    def __eq__(self, other):
        if type(other) is int:
            return (other % self.prime) == self.value
        other = self.is_fint(other)
        return self.value == other.value

    def __pow__(self, power):
        power = self.is_fint(power)
        return FInt(pow(self.value, power.value, self.prime), self.prime)

    def __str__(self):
        return "F" + str(self.value)

    def __neg__(self):
        return FInt(-self.value % self.prime, self.prime)

    def __repr__(self):
        return "F" + str(self.value)


class Polynomial:
    def __init__(self, secret, degree, prime=the_prime):  # 2**256 < the_prime < 2**257
        self.prime = prime
        self.degree = degree
        if type(secret) == bytes:
            secret = int.from_bytes(secret, byteorder)
        assert secret < prime, "Secret should be smaller than prime"
        assert degree < 128, "Degree can at most be 127"
        self.coefficients = [FInt(secret, prime)] + [FInt(int.from_bytes(os.urandom(32), byteorder) % prime,
                                                          prime) for _ in range(degree)]

    def evaluate_point(self, x_val: int) -> (int, int):
        y_val = FInt(0, self.prime)
        for pwr in range(0, len(self.coefficients)):
            y_val += (FInt(x_val, self.prime) ** FInt(pwr, self.prime)) * self.coefficients[pwr]
        return x_val, y_val

    def __str__(self):
        s = str(self.coefficients[0].value) + "x^0"
        for idx in range(1, len(self.coefficients)):
            s += "+" + str(self.coefficients[idx].value) + "x^" + str(idx)
        return s


def recover_secret(t, points, prime=the_prime) -> bytes:
    assert len(points) > t
    k = t + 1

    points_ = points[:k]
    x_vals, y_vals = zip(*[(FInt(point[0], prime), point[1]) for point in points_])

    K = FInt(0, prime)
    for idx in range(k):
        yi = y_vals[idx]
        PI = FInt(1, prime)
        for jdx in range(k):
            if jdx == idx: continue
            xi = x_vals[idx]
            xj = x_vals[jdx]
            PI *= xj / (xj - xi)
        K += yi * PI
    return K.value.to_bytes(32, byteorder=byteorder, signed=False)


def split_secret(secret: bytes, t: int, n: int) -> list:
    assert len(secret) == 32, "Secret should be 256 long."
    p = Polynomial(secret, t)
    return [p.evaluate_point(idx) for idx in range(1, n+1)]