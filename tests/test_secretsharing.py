from unittest import TestCase

from security.secretsharing import FInt, Polynomial, recover_secret, split_secret, byteorder


class TestOperations(TestCase):

    def test_subtraction(self):
        prime = 11
        f1 = FInt(10, prime)
        f2 = FInt(5, prime)
        f3 = FInt(1, prime)
        f4 = FInt(0, prime)
        f9 = FInt(9, prime)
        self.assertTrue((f1 - f2) == f2)
        self.assertTrue((f3 - f4) == f3)
        self.assertTrue((f1 - f4) == f1)
        self.assertTrue((f1 - f3) == f9)

    def test_addition(self):
        prime = 11
        f1 = FInt(10, prime)
        f2 = FInt(5, prime)
        f3 = FInt(1, prime)
        f4 = FInt(0, prime)
        self.assertTrue((f1 + f3) == f4)
        self.assertTrue((f2 + f2) == f1)
        self.assertTrue((f3 + f3 + f3 + f3 + f3) == f2)
        self.assertTrue((f3 + f4) == f3)

    def test_multiplication(self):
        prime = 11
        f1 = FInt(10, prime)
        f2 = FInt(5, prime)
        f3 = FInt(1, prime)
        f4 = FInt(0, prime)
        self.assertTrue((f1 * f4) == f4)
        self.assertTrue((f1 * f3) == f1)
        self.assertTrue((f2 * f2 * f2) == (f2 - f3))
        self.assertTrue((f3 * f3) == f3)

    def test_division(self):
        prime = 5
        f1 = FInt(1, prime)
        f2 = FInt(2, prime)
        f3 = FInt(3, prime)
        f4 = FInt(4, prime)
        self.assertTrue((f4 / f3) == f3)
        self.assertTrue((f2 / f2) == f1)
        self.assertTrue((f1 / f4) == f4)

    def test_power(self):
        prime = 11
        f3 = FInt(3, prime)
        f5 = FInt(5, prime)
        self.assertTrue((f3 ** f3) == f5)

    def test_imul(self):
        prime = 11
        f3 = FInt(3, prime)
        f3 *= f3
        f9 = FInt(9, prime)
        self.assertTrue(f3 == f9)
        f3 *= f3
        f4 = FInt(4, prime)
        self.assertTrue(f3 == f4)

    def test_negation(self):
        prime = 11
        f3 = FInt(3, prime)
        f4 = FInt(4, prime)
        f5 = FInt(5, prime)
        f6 = FInt(6, prime)
        f7 = FInt(7, prime)
        f8 = FInt(8, prime)
        self.assertTrue(-f3 == f8)
        self.assertTrue(-f4 == f7)
        self.assertTrue(-f5 == f6)


class TestPolynomial(TestCase):

    def test_evaluate_point(self):
        prime = 17
        p = Polynomial(13, 2, prime)
        p.coefficients = [FInt(x, prime) for x in [13, 2, 5]]
        # p = 13 + 2x + 5x² -> p(1) = 13 + 2 + 5 = 20 = 3
        self.assertTrue(p.evaluate_point(1)[1] == FInt(3, prime),
                        str(p.evaluate_point(1)[1]) + " != " + str(FInt(3, prime)))
        # p = 13 + 2x + 5x² -> p(3) = 13 + 6 + 45 = 64 = 13
        self.assertTrue(p.evaluate_point(3)[1] == FInt(13, prime),
                        str(p.evaluate_point(1)[1]) + " != " + str(FInt(13, prime)))

    def test_can_recover_secret(self):
        prime = 11
        secret = (7).to_bytes(256, byteorder, signed=False)
        degree = 2
        # P = 7 + 5x + 2x² -> P(2) = 7 + 10 + 8 = 25 = 3, P(4) = 7 + 20 + 32 = 59 = 4, P(6) = 7 + 30 + 72 = 109 = 10
        points = [(2, FInt(3, prime)), (4, FInt(4, prime)), (6, FInt(10, prime))]
        secret_ = recover_secret(degree, points, prime)
        self.assertTrue(secret == secret_, str(secret_) + " != " + str(secret))
        secret = (3).to_bytes(256, byteorder, signed=False)
        # P = 3 + 2x + 5x² -> P(1) = 10, P(2) = 5, P(3) = 10
        points = [(1, FInt(10, prime)), (2, FInt(5, prime)), (3, FInt(10, prime))]
        secret_ = recover_secret(degree, points, prime)
        self.assertTrue(secret == secret_, str(secret_) + " != " + str(secret))

    def test_can_split_then_recover_secret(self):
        secret = (10).to_bytes(256, byteorder=byteorder, signed=False)
        t = 4
        n = 10
        shares = split_secret(secret, t, n)
        secret_ = recover_secret(t, shares)
        self.assertEqual(secret, secret_, "Secrets don't match ergo didn't recover secret.")