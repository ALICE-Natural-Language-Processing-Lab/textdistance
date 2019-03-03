from __main__ import unittest, textdistance
from fractions import Fraction


class ArithNCDTest(unittest.TestCase):
    alg = textdistance.arith_ncd

    def test_make_probs(self):
        probs = self.alg._make_probs('lol', 'lal')
        self.assertEqual(probs['l'], (Fraction(0, 1), Fraction(4, 7)))
        self.assertEqual(probs['o'][1], Fraction(1, 7))
        self.assertEqual(probs['a'][1], Fraction(1, 7))

    def test_arith_output(self):
        fraction = self.alg._compress('BANANA')
        self.assertEqual(fraction.numerator, 1525)

    def test_arith_distance(self):
        same = self.alg('test', 'test')
        similar = self.alg('test', 'text')
        diffirent = self.alg('test', 'nani')
        self.assertLess(same, similar)
        self.assertLess(similar, diffirent)
