from math import log, sqrt
from itertools import repeat, islice, permutations
# python3
try:
    from functools import reduce
except ImportError:
    pass
from .base import Base as _Base, BaseSimilarity as _BaseSimilarity
from .edit_based import DamerauLevenshtein


__all__ = [
    'jaccard', 'sorensen', 'tversky', 'sorensen_dice',
    'overlap', 'cosine', 'monge_elkan',
]


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
        union = self._union_counters(*sequences)                 # set
        union = self._count_counters(union)                      # int
        return 1 - intersection / float(union)


class Sorensen(_Base):
    '''
    Compute the Sorensen distance between the two sequences.
    They should contain hashable items.
    The return value is a float between 0 and 1, where 0 means equal,
    and 1 totally different.
    '''
    def maximum(self, *sequences):
        return 1

    def __call__(self, *sequences):
        length = sum(map(len, sequences))
        sequences = self._get_counters(*sequences)               # sets
        intersection = self._intersect_counters(*sequences)      # set
        intersection = self._count_counters(intersection)        # int
        return 1 - (2 * intersection) / float(length)


class Tversky(_BaseSimilarity):
    """Tversky index
    https://en.wikipedia.org/wiki/Tversky_index
    """
    def __init__(self, qval=1, ks=None, bias=None):
        self.qval = qval
        self.ks = ks or repeat(1)
        self.bias = bias

    def maximum(self, *sequences):
        return 1

    def __call__(self, *sequences):
        sequences = self._get_counters(*sequences)                # sets
        intersection = self._intersect_counters(*sequences)       # set
        intersection = self._count_counters(intersection)         # int
        sequences = [self._count_counters(s) for s in sequences]  # ints
        ks = list(islice(self.ks, len(sequences)))

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
    def maximum(self, *sequences):
        return 1

    def __call__(self, *sequences):
        sequences = self._get_counters(*sequences)               # sets
        intersection = self._intersect_counters(*sequences)      # set
        intersection = self._count_counters(intersection)        # int
        sequences = [self._count_counters(s) for s in sequences] # ints

        return float(intersection) / min(sequences)


class Cosine(_BaseSimilarity):
    """cosine similarity (Ochiai coefficient)
    """
    def maximum(self, *sequences):
        return 1

    def __call__(self, *sequences):
        sequences = self._get_counters(*sequences)               # sets
        intersection = self._intersect_counters(*sequences)      # set
        intersection = self._count_counters(intersection)        # int
        sequences = [self._count_counters(s) for s in sequences] # ints
        prod = reduce(lambda x, y: x * y, sequences)

        return intersection / sqrt(prod)


class Tanimoto(Jaccard):
    """Tanimoto distance
    This is identical to the Jaccard similarity coefficient
    and the Tversky index for alpha=1 and beta=1.
    """
    def __call__(self, *sequences):
        result = super(Tanimoto, self)(*sequences)
        if result == 0:
            return float('-inf')
        else:
            return log(result, 2)


class MongeElkan(_BaseSimilarity):
    def __init__(self, sim_func=DamerauLevenshtein().similarity, symmetric=False, qval=1):
        self.sim_func = sim_func
        self.symmetric = symmetric
        self.qval = qval

    def maximum(self, *sequences):
        return 1

    def _calc(self, seq, *sequences):
        maxes = []
        for c1 in seq:
            for s in sequences:
                max_sim = float('-inf')
                for c2 in s:
                    max_sim = max(max_sim, self.sim_func(c1, c2))
                maxes.append(max_sim)
        return float(sum(maxes)) / len(maxes)

    def __call__(self, *sequences):
        if not all(sequences):
            return 0
        sequences = self._get_sequences(*sequences)

        if self.symmetric:
            result = []
            for seqs in permutations(sequences):
                result.append(self._calc(*seqs))
            return float(sum(result)) / len(result)
        else:
            return self._calc(*sequences)


jaccard = Jaccard()
sorensen_dice = dice = sorensen = Sorensen()
tversky = Tversky()
#sorensen_dice = Tversky(ks=[.5, .5])
overlap = Overlap()
cosine = Cosine()
tanimoto = Tanimoto()
monge_elkan = MongeElkan()
