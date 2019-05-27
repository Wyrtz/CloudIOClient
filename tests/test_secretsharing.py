from unittest import TestCase

from security.secretsharing import FFInt, Polynomial, recover_secret, split_secret, byteorder


class TestOperations(TestCase):
    """Class for unittesting the class FInt under secretsharing.py module"""

    def test_subtraction(self):
        """Ensure subtraction works as expected"""
        prime = 11
        f1 = FFInt(10, prime)
        f2 = FFInt(5, prime)
        f3 = FFInt(1, prime)
        f4 = FFInt(0, prime)
        f9 = FFInt(9, prime)
        self.assertTrue((f1 - f2) == f2)
        self.assertTrue((f3 - f4) == f3)
        self.assertTrue((f1 - f4) == f1)
        self.assertTrue((f1 - f3) == f9)

    def test_addition(self):
        """Ensure addition works as expected"""
        prime = 11
        f1 = FFInt(10, prime)
        f2 = FFInt(5, prime)
        f3 = FFInt(1, prime)
        f4 = FFInt(0, prime)
        self.assertTrue((f1 + f3) == f4)
        self.assertTrue((f2 + f2) == f1)
        self.assertTrue((f3 + f3 + f3 + f3 + f3) == f2)
        self.assertTrue((f3 + f4) == f3)

    def test_multiplication(self):
        """Ensure multiplication works as expected"""
        prime = 11
        f1 = FFInt(10, prime)
        f2 = FFInt(5, prime)
        f3 = FFInt(1, prime)
        f4 = FFInt(0, prime)
        self.assertTrue((f1 * f4) == f4)
        self.assertTrue((f1 * f3) == f1)
        self.assertTrue((f2 * f2 * f2) == (f2 - f3))
        self.assertTrue((f3 * f3) == f3)

    def test_division(self):
        """Ensure division works as expected"""
        prime = 5
        f1 = FFInt(1, prime)
        f2 = FFInt(2, prime)
        f3 = FFInt(3, prime)
        f4 = FFInt(4, prime)
        self.assertTrue((f4 / f3) == f3)
        self.assertTrue((f2 / f2) == f1)
        self.assertTrue((f1 / f4) == f4)

    def test_power(self):
        """Ensure power (raising) works as expected"""
        prime = 11
        f3 = FFInt(3, prime)
        f5 = FFInt(5, prime)
        self.assertTrue((f3 ** f3) == f5)

    def test_imul(self):
        """Ensure imuliplication works as expected"""
        prime = 11
        f3 = FFInt(3, prime)
        f3 *= f3
        f9 = FFInt(9, prime)
        self.assertTrue(f3 == f9)
        f3 *= f3
        f4 = FFInt(4, prime)
        self.assertTrue(f3 == f4)

    def test_negation(self):
        """Ensure negation works as expected"""
        prime = 11
        f3 = FFInt(3, prime)
        f4 = FFInt(4, prime)
        f5 = FFInt(5, prime)
        f6 = FFInt(6, prime)
        f7 = FFInt(7, prime)
        f8 = FFInt(8, prime)
        self.assertTrue(-f3 == f8)
        self.assertTrue(-f4 == f7)
        self.assertTrue(-f5 == f6)


class TestPolynomial(TestCase):
    """Class for unittesting the class Polynomial under secretsharing.py module"""

    def test_evaluate_point(self):
        """test that evaluating a point return the expected value"""
        prime = 17
        p = Polynomial(13, 2, prime)
        p.coefficients = [FFInt(x, prime) for x in [13, 2, 5]]
        # p = 13 + 2x + 5x² -> p(1) = 13 + 2 + 5 = 20 = 3
        self.assertTrue(p.evaluate_point(1)[1] == FFInt(3, prime),
                        str(p.evaluate_point(1)[1]) + " != " + str(FFInt(3, prime)))
        # p = 13 + 2x + 5x² -> p(3) = 13 + 6 + 45 = 64 = 13
        self.assertTrue(p.evaluate_point(3)[1] == FFInt(13, prime),
                        str(p.evaluate_point(1)[1]) + " != " + str(FFInt(13, prime)))

    def test_can_recover_secret(self):
        """"Test that a split secret can be restored"""
        prime = 11
        secret = (7).to_bytes(32, byteorder, signed=False)
        degree = 2
        # P = 7 + 5x + 2x² -> P(2) = 7 + 10 + 8 = 25 = 3, P(4) = 7 + 20 + 32 = 59 = 4, P(6) = 7 + 30 + 72 = 109 = 10
        points = [(2, FFInt(3, prime), degree), (4, FFInt(4, prime), degree), (6, FFInt(10, prime), degree)]
        secret_ = recover_secret(points, prime)
        self.assertTrue(secret == secret_, str(secret_) + " != " + str(secret))
        secret = (3).to_bytes(32, byteorder, signed=False)
        # P = 3 + 2x + 5x² -> P(1) = 10, P(2) = 5, P(3) = 10
        points = [(1, FFInt(10, prime), degree), (2, FFInt(5, prime), degree), (3, FFInt(10, prime), degree)]
        secret_ = recover_secret(points, prime)
        self.assertTrue(secret == secret_, str(secret_) + " != " + str(secret))

    def test_can_split_then_recover_secret(self):
        """Test can split then recover a secret"""
        secret = (10).to_bytes(32, byteorder=byteorder, signed=False)
        t = 4  # The max number of points one should be able to obtain without being able to recover secret.
        n = 10
        shares = split_secret(secret, t, n)
        print(shares)
        secret_ = recover_secret(shares)
        self.assertEqual(secret, secret_, "Secrets don't match ergo didn't recover secret.")