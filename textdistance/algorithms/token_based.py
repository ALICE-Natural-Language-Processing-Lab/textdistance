from itertools import repeat
# python3
try:
    from functools import reduce
except ImportError:
    pass
from .base import Base as _Base, BaseSimilarity as _BaseSimilarity


__all__ = ['jaccard', 'sorensen', 'tversky', 'overlap', 'cosine']


class Jaccard(_Base):
    '''
    Compute the Jaccard distance between the two sequences.
    They should contain hashable items.
    The return value is a float between 0 and 1, where 0 means equal,
    and 1 totally different.
    '''
    def maximum(self, *sequences):
        return 1

    def __call__(self, *sequences):
        sequences = self._get_counters(*sequences)               # sets
        intersection = self._intersect_counters(*sequences)      # set
        intersection = self._count_counters(intersection)        # int
        union = self._union_counters(*sequences)             # set
        union = self._count_counters(union)                      # int
        return 1 - intersection / float(union)


class Sorensen(_Base):
    '''
    Compute the Sorensen distance between the two sequences.
    They should contain hashable items.
    The return value is a float between 0 and 1, where 0 means equal,
    and 1 totally different.
    '''
    def __call__(self, *sequences):
        sequences = self._get_counters(*sequences)               # sets
        intersection = self._intersect_counters(*sequences)      # set
        intersection = self._count_counters(intersection)        # int
        union = self._intersect_counters(*sequences)             # set
        union = self._count_counters(union)                      # int
        return 1 - (2 * intersection) / float(union)


class Tversky(_BaseSimilarity):
    """Tversky index
    https://en.wikipedia.org/wiki/Tversky_index
    """
    def __init__(self, qval=1, ks=None, bias=None):
        self.qval = qval
        self.ks = ks or repeat(1)
        self.bias = bias

    def __call__(self, *sequences):
        # all is equeal
        if len(set(sequences)) <= 1:
            return 1.0
        # any set is empty
        elif not min(map(len, sequences)):
            return 0.0

        sequences = self._get_counters(*sequences)               # sets
        intersection = self._intersect_counters(*sequences)      # set
        intersection = self._count_counters(intersection)        # int
        sequences = [self._count_counter(s) for s in sequences]  # ints
        ks = self.ks[:len(sequences)]

        if self.bias is None:
            result = intersection
            for k, s in zip(ks, sequences):
                result += k * (s - intersection)
            return intersection / result

        a_val = min([s - intersection for s in sequences])
        b_val = max([s - intersection for s in sequences])
        c_val = float(intersection + self.bias)
        ks_prod = map(lambda a, b: a * b, ks)
        ks_beta = ks[0] and (ks_prod / ks[0])
        result = ks_prod * (a_val - b_val) + b_val * ks_beta
        return c_val / (result + c_val)


class Overlap(_BaseSimilarity):
    """overlap coefficient
    """
    def __call__(self, *sequences):
        # all is equeal
        if len(set(sequences)) <= 1:
            return 1.0
        # any set is empty
        elif not min(map(len, sequences)):
            return 0.0

        sequences = self._get_counters(*sequences)               # sets
        intersection = self._intersect_counters(*sequences)      # set
        intersection = self._count_counters(intersection)        # int
        sequences = [self._count_counter(s) for s in sequences]  # ints

        return float(intersection) / min(sequences)


class Cosine(_BaseSimilarity):
    """cosine similarity (Ochiai coefficient)
    """
    def __call__(self, *sequences):
        # all is equeal
        if len(set(sequences)) <= 1:
            return 1.0
        # any set is empty
        elif not min(map(len, sequences)):
            return 0.0

        sequences = self._get_counters(*sequences)               # sets
        intersection = self._intersect_counters(*sequences)      # set
        intersection = self._count_counters(intersection)        # int
        sequences = [self._count_counter(s) for s in sequences]  # ints
        prod = reduce(lambda x, y: x * y, sequences)

        return intersection / prod


jaccard = Jaccard()
sorensen = Sorensen()
tversky = Tversky()
sorensen_dice = Tversky(ks=[.5, .5])
overlap = Overlap()
cosine = Cosine()
