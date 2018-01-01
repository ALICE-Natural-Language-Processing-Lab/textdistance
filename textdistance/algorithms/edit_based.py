# built-in
from collections import defaultdict
try:
    # python3
    from itertools import zip_longest
except ImportError:
    # python2
    from itertools import izip_longest as zip_longest
# external
try:
    import numpy
except ImportError:
    numpy = None
# project
from .base import Base as _Base, BaseSimilarity as _BaseSimilarity


__all__ = [
    'hamming', 'mlipns',
    'levenshtein', 'damerau_levenshtein',
    'jaro', 'jaro_winkler', 'strcmp95',
    'needleman_wunsch', 'gotoh',
    'smith_waterman', 'editex',
]


class Hamming(_Base):
    '''
    Compute the Hamming distance between the two or more sequences.
    The Hamming distance is the number of differing items in ordered sequences.
    '''
    def __init__(self, qval=1, test_func=None, truncate=False):
        self.qval = qval
        self.test_func = test_func or self._ident
        self.truncate = truncate

    def __call__(self, *sequences):
        sequences = self._get_sequences(*sequences)
        _zip = zip if self.truncate else zip_longest
        return sum([not self.test_func(*es) for es in _zip(*sequences)])


class Levenshtein(_Base):
    '''
    Compute the absolute Levenshtein distance between the two sequences.
    The Levenshtein distance is the minimum number of edit operations necessary
    for transforming one sequence into the other. The edit operations allowed are:

        * deletion:     ABC -> BC, AC, AB
        * insertion:    ABC -> ABCD, EABC, AEBC..
        * substitution: ABC -> ABE, ADC, FBC..
    '''
    def __init__(self, qval=1, test_func=None):
        self.qval = qval
        self.test_func = test_func or self._ident

    def __call__(self, s1, s2):
        s1, s2 = self._get_sequences(s1, s2)
        if not s1 or not s2:
            return len(s1) + len(s2)

        if self.test_func(s1[-1], s2[-1]):
            return self(s1[:-1], s2[:-1])

        # deletion/insertion
        d = min(
            self(s1[:-1], s2),
            self(s1, s2[:-1]),
        )
        # substitution
        s = self(s1[:-1], s2[:-1])
        return min(d, s) + 1


class DamerauLevenshtein(_Base):
    '''
    Compute the absolute Damerau-Levenshtein distance between the two sequences.
    The Damerau-Levenshtein distance is the minimum number of edit operations necessary
    for transforming one sequence into the other. The edit operations allowed are:

        * deletion:      ABC -> BC, AC, AB
        * insertion:     ABC -> ABCD, EABC, AEBC..
        * substitution:  ABC -> ABE, ADC, FBC..
        * transposition: ABC -> ACB, BAC
    '''
    def __init__(self, qval=1, test_func=None):
        self.qval = qval
        self.test_func = test_func or self._ident

    def __call__(self, s1, s2):
        s1, s2 = self._get_sequences(s1, s2)
        d = {}

        # matrix
        for i in range(-1, len(s1) + 1):
            d[i, -1] = i + 1
        for j in range(-1, len(s2) + 1):
            d[-1, j] = j + 1

        for i, cs1 in enumerate(s1):
            for j, cs2 in enumerate(s2):
                cost = int(not self.test_func(cs1, cs2))
                # ^ 0 if equal, 1 otherwise

                d[i, j] = min(
                    d[i - 1, j] + 1,            # deletion
                    d[i, j - 1] + 1,            # insertion
                    d[i - 1, j - 1] + cost,     # substitution
                )

                # transposition
                if not i or not j:
                    continue
                if not self.test_func(cs1, s2[j - 1]):
                    continue
                d[i, j] = min(
                    d[i, j],
                    d[i - 2, j - 2] + cost,
                )

        return d[len(s1) - 1, len(s2) - 1]


class JaroWinkler(_BaseSimilarity):
    """
    Computes the Jaro-Winkler measure between two strings.
    The Jaro-Winkler measure is designed to capture cases where two strings
    have a low Jaro score, but share a prefix.
    and thus are likely to match.
    """
    def __init__(self, long_tolerance, winklerize, qval=1):
        self.qval = qval
        self.long_tolerance = long_tolerance
        self.winklerize = winklerize

    def maximum(self, *sequences):
        return 1

    def __call__(self, s1, s2, prefix_weight=0.1):
        s1, s2 = self._get_sequences(s1, s2)
        s1_len = len(s1)
        s2_len = len(s2)

        if not s1_len or not s2_len:
            return 0.0

        min_len = max(s1_len, s2_len)
        search_range = (min_len // 2) - 1
        if search_range < 0:
            search_range = 0

        s1_flags = [False]*s1_len
        s2_flags = [False]*s2_len

        # looking only within search range, count & flag matched pairs
        common_chars = 0
        for i, s1_ch in enumerate(s1):
            low = i - search_range if i > search_range else 0
            hi = i + search_range if i + search_range < s2_len else s2_len - 1
            for j in range(low, hi+1):
                if not s2_flags[j] and s2[j] == s1_ch:
                    s1_flags[i] = s2_flags[j] = True
                    common_chars += 1
                    break

        # short circuit if no characters match
        if not common_chars:
            return 0.0

        # count transpositions
        k = trans_count = 0
        for i, s1_f in enumerate(s1_flags):
            if s1_f:
                for j in range(k, s2_len):
                    if s2_flags[j]:
                        k = j + 1
                        break
                if s1[i] != s2[j]:
                    trans_count += 1
        trans_count /= 2

        # adjust for similarities in nonmatched characters
        common_chars = float(common_chars)
        weight = ((common_chars/s1_len + common_chars/s2_len +
                  (common_chars-trans_count) / common_chars)) / 3

        # stop to boost if strings are not similar
        if not self.winklerize or weight <= 0.7 or s1_len <= 3 or s2_len <= 3:
            return weight

        # winkler modification
        # adjust for up to first 4 chars in common
        j = min(min_len, 4)
        i = 0
        while i < j and s1[i] == s2[i] and s1[i]:
            i += 1
        if i:
            weight += i * prefix_weight * (1.0 - weight)

        # optionally adjust for long strings
        # after agreeing beginning chars, at least two or more must agree and
        # agreed characters must be > half of remaining characters
        if not self.long_tolerance or min_len <= 4:
            return weight
        if common_chars < i or 2 * common_chars < min_len + i:
            return weight
        weight += (1.0 - weight) * float(common_chars-i-1) / float(s1_len+s2_len-i*2+2)
        return weight


class NeedlemanWunsch(_BaseSimilarity):
    """
    Computes the Needleman-Wunsch measure between two strings.
    The Needleman-Wunsch generalizes the Levenshtein distance and considers global
    alignment between two strings. Specifically, it is computed by assigning
    a score to each alignment between two input strings and choosing the
    score of the best alignment, that is, the maximal score.
    An alignment between two strings is a set of correspondences between the
    characters of between them, allowing for gaps.
    """
    def __init__(self, gap_cost=1.0, sim_func=None, qval=1):
        self.qval = qval
        self.gap_cost = gap_cost
        if sim_func:
            self.sim_func = sim_func
        else:
            self.sim_func = self._ident

    def maximum(self, *sequences):
        return min(map(len, sequences))

    def __call__(self, s1, s2):
        if not numpy:
            raise ImportError('Please, install numpy for Needleman-Wunsch measure')
        s1, s2 = self._get_sequences(s1, s2)
        dist_mat = numpy.zeros(
            (len(s1) + 1, len(s2) + 1),
            dtype=numpy.float,
        )
        # DP initialization
        for i in range(len(s1) + 1):
            dist_mat[i, 0] = -(i * self.gap_cost)
        # DP initialization
        for j in range(len(s2) + 1):
            dist_mat[0, j] = -(j * self.gap_cost)
        # Needleman-Wunsch DP calculation
        for i in range(1, len(s1) + 1):
            for j in range(1, len(s2) + 1):
                match = dist_mat[i - 1, j - 1] + self.sim_func(s1[i - 1], s2[j - 1])
                delete = dist_mat[i - 1, j] - self.gap_cost
                insert = dist_mat[i, j - 1] - self.gap_cost
                dist_mat[i, j] = max(match, delete, insert)
        return dist_mat[dist_mat.shape[0] - 1, dist_mat.shape[1] - 1]


class SmithWaterman(_BaseSimilarity):
    """
    Computes the Smith-Waterman measure between two strings.
    The Smith-Waterman algorithm performs local sequence alignment;
    that is, for determining similar regions between two strings.
    Instead of looking at the total sequence, the Smith-Waterman algorithm compares
    segments of all possible lengths and optimizes the similarity measure.
    """
    def __init__(self, gap_cost=1.0, sim_func=None, qval=1):
        self.qval = qval
        self.gap_cost = gap_cost
        if sim_func:
            self.sim_func = sim_func
        else:
            self.sim_func = self._ident

    def maximum(self, *sequences):
        return min(map(len, sequences))

    def __call__(self, s1, s2):
        if not numpy:
            raise ImportError('Please, install numpy for Smith-Waterman measure')
        s1, s2 = self._get_sequences(s1, s2)
        dist_mat = numpy.zeros(
            (len(s1) + 1, len(s2) + 1),
            dtype=numpy.float,
        )
        max_value = 0
        for i, sc1 in enumerate(s1, start=1):
            for j, sc2 in enumerate(s2, start=1):
                # The score for substituting the letter a[i-1] for b[j-1].
                # Generally low for mismatch, high for match.
                match = dist_mat[i - 1, j - 1] + self.sim_func(sc1, sc2)
                # The scores for for introducing extra letters in one of the strings
                # (or by symmetry, deleting them from the other).
                delete = dist_mat[i - 1, j] - self.gap_cost
                insert = dist_mat[i, j - 1] - self.gap_cost
                dist_mat[i, j] = max(0, match, delete, insert)
                max_value = max(max_value, dist_mat[i, j])
        return max_value


class Gotoh(_BaseSimilarity):
    """Gotoh score
    Gotoh's algorithm is essentially Needleman-Wunsch with affine gap
    penalties:
    https://www.cs.umd.edu/class/spring2003/cmsc838t/papers/gotoh1982.pdf
    """
    def __init__(self, gap_open=1, gap_ext=0.4, sim_func=None, qval=1):
        self.qval = qval
        self.gap_open = gap_open
        self.gap_ext = gap_ext
        if sim_func:
            self.sim_func = sim_func
        else:
            self.sim_func = self._ident

    def maximum(self, *sequences):
        return min(map(len, sequences))

    def __call__(self, s1, s2):
        s1, s2 = self._get_sequences(s1, s2)
        len_s1 = len(s1)
        len_s2 = len(s2)
        d_mat = numpy.zeros((len_s1 + 1, len_s2 + 1), dtype=numpy.float)
        p_mat = numpy.zeros((len_s1 + 1, len_s2 + 1), dtype=numpy.float)
        q_mat = numpy.zeros((len_s1 + 1, len_s2 + 1), dtype=numpy.float)

        d_mat[0, 0] = 0
        p_mat[0, 0] = float('-inf')
        q_mat[0, 0] = float('-inf')
        for i in range(1, len_s1 + 1):
            d_mat[i, 0] = float('-inf')
            p_mat[i, 0] = -self.gap_open - self.gap_ext * (i - 1)
            q_mat[i, 0] = float('-inf')
            q_mat[i, 1] = -self.gap_open
        for j in range(1, len_s2 + 1):
            d_mat[0, j] = float('-inf')
            p_mat[0, j] = float('-inf')
            p_mat[1, j] = -self.gap_open
            q_mat[0, j] = -self.gap_open - self.gap_ext * (j - 1)

        for i, sc1 in enumerate(s1, start=1):
            for j, sc2 in enumerate(s2, start=1):
                sim_val = self.sim_func(sc1, sc2)
                d_mat[i, j] = max(
                    d_mat[i-1, j-1] + sim_val,
                    p_mat[i-1, j-1] + sim_val,
                    q_mat[i-1, j-1] + sim_val,
                )
                p_mat[i, j] = max(
                    d_mat[i-1, j] - self.gap_open,
                    p_mat[i-1, j] - self.gap_ext,
                )
                q_mat[i, j] = max(
                    d_mat[i, j-1] - self.gap_open,
                    q_mat[i, j-1] - self.gap_ext,
                )

        i, j = (n - 1 for n in d_mat.shape)
        return max(d_mat[i, j], p_mat[i, j], q_mat[i, j])


class StrCmp95(_BaseSimilarity):
    """strcmp95 similarity
    """
    sp_mx = (
        ('A', 'E'), ('A', 'I'), ('A', 'O'), ('A', 'U'), ('B', 'V'), ('E', 'I'),
        ('E', 'O'), ('E', 'U'), ('I', 'O'), ('I', 'U'), ('O', 'U'), ('I', 'Y'),
        ('E', 'Y'), ('C', 'G'), ('E', 'F'), ('W', 'U'), ('W', 'V'), ('X', 'K'),
        ('S', 'Z'), ('X', 'S'), ('Q', 'C'), ('U', 'V'), ('M', 'N'), ('L', 'I'),
        ('Q', 'O'), ('P', 'R'), ('I', 'J'), ('2', 'Z'), ('5', 'S'), ('8', 'B'),
        ('1', 'I'), ('1', 'L'), ('0', 'O'), ('0', 'Q'), ('C', 'K'), ('G', 'J')
    )

    def __init__(self, long_strings=False):
        self.long_strings = long_strings

    def maximum(self, *sequences):
        return 1

    @staticmethod
    def _in_range(char):
        return 0 < ord(char) < 91

    def __call__(self, s1, s2):
        s1 = s1.strip().upper()
        s2 = s2.strip().upper()
        len_s1 = len(s1)
        len_s2 = len(s2)

        adjwt = defaultdict(int)

        # Initialize the adjwt array on the first call to the function only.
        # The adjwt array is used to give partial credit for characters that
        # may be errors due to known phonetic or character recognition errors.
        # A typical example is to match the letter "O" with the number "0"
        for i in self.sp_mx:
            adjwt[(i[0], i[1])] = 3
            adjwt[(i[1], i[0])] = 3

        if len_s1 > len_s2:
            search_range = len_s1
            minv = len_s2
        else:
            search_range = len_s2
            minv = len_s1

        # Blank out the flags
        s1_flag = [0] * search_range
        s2_flag = [0] * search_range
        search_range = max(0, search_range // 2 - 1)

        # Looking only within the search range, count and flag the matched pairs.
        num_com = 0
        yl1 = len_s2 - 1
        for i, sc1 in enumerate(s1):
            lowlim = (i - search_range) if (i >= search_range) else 0
            hilim = (i + search_range) if ((i + search_range) <= yl1) else yl1
            for j in range(lowlim, hilim + 1):
                if s2_flag[j] == 0 and s2[j] == sc1:
                    s2_flag[j] = 1
                    s1_flag[i] = 1
                    num_com += 1
                    break

        # If no characters in common - return
        if num_com == 0:
            return 0.0

        # Count the number of transpositions
        k = n_trans = 0
        for i, sc1 in enumerate(s1):
            if s1_flag[i] != 0:
                for j in range(k, len_s2):
                    if s2_flag[j] != 0:
                        k = j + 1
                        break
                if sc1 != s2[j]:
                    n_trans += 1
        n_trans = n_trans // 2

        # Adjust for similarities in unmatched characters
        n_simi = 0
        if minv > num_com:
            for i in range(len_s1):
                if s1_flag[i] != 0:
                    continue
                if not self._in_range(s1[i]):
                    continue
                for j in range(len_s2):
                    if s2_flag[j] != 0:
                        continue
                    if not self._in_range(s2[j]):
                        continue
                    if (s1[i], s2[j]) not in adjwt:
                        continue
                    n_simi += adjwt[(s1[i], s2[j])]
                    s2_flag[j] = 2
                    break
        num_sim = n_simi/10.0 + num_com

        # Main weight computation
        weight = num_sim / len_s1 + num_sim / len_s2
        weight += (num_com - n_trans) / num_com
        weight = weight / 3.0

        # Continue to boost the weight if the strings are similar
        if weight <= 0.7:
            return weight

        # Adjust for having up to the first 4 characters in common
        j = 4 if (minv >= 4) else minv
        i = 0
        for sc1, sc2 in zip(s1, s2):
            if i >= j:
                break
            if sc1 != sc2:
                continue
            if sc1.isdigit():
                continue
            i += 1
        if i:
            weight += i * 0.1 * (1.0 - weight)

        # Optionally adjust for long strings.

        # After agreeing beginning chars, at least two more must agree and
        # the agreeing characters must be > .5 of remaining characters.
        if not self.long_strings:
            return weight
        if minv <= 4:
            return weight
        if num_com <= i + 1 or 2 * num_com < minv + i:
            return weight
        if s1[0].isdigit():
            return weight
        res = (num_com-i-1) / (len_s1+len_s2-i*2+2)
        weight += (1.0 - weight) * res
        return weight


class MLIPNS(_BaseSimilarity):
    '''
    Compute the Hamming distance between the two or more sequences.
    The Hamming distance is the number of differing items in ordered sequences.
    '''
    def __init__(self, threshold=0.25, maxmismatches=2, qval=1):
        self.qval = qval
        self.threshold = threshold
        self.maxmismatches = maxmismatches

    def maximum(self, *sequences):
        return 1

    def __call__(self, *sequences):
        sequences = self._get_sequences(*sequences)
        mismatches = 0
        ham = Hamming()(*sequences)
        maxlen = max(map(len, sequences))
        while all(sequences) and mismatches <= self.maxmismatches:
            if not maxlen:
                return 1
            if 1 - float(maxlen - ham) / maxlen <= self.threshold:
                return 1
            mismatches += 1
            ham -= 1
            maxlen -= 1

        if not maxlen:
            return 1
        return 0


class Editex(_Base):
    letter_groups = (
        frozenset('AEIOUY'),
        frozenset('BP'),
        frozenset('CKQ'),
        frozenset('DT'),
        frozenset('LR'),
        frozenset('MN'),
        frozenset('GJ'),
        frozenset('FPV'),
        frozenset('SXZ'),
        frozenset('CSZ'),
    )
    all_letters = frozenset('AEIOUYBPCKQDTLRMNGJFVSXZ')

    def __init__(self, local=False, match_cost=0, group_cost=1, mismatch_cost=2):
        self.match_cost = match_cost
        self.group_cost = group_cost
        self.mismatch_cost = mismatch_cost
        self.local = local

    def maximum(self, *sequences):
        return max(map(len, sequences)) * self.mismatch_cost

    def r_cost(self, *sequences):
        if self._ident(*sequences):
            return self.match_cost
        if any(map(lambda x: x not in self.all_letters, sequences)):
            return self.mismatch_cost
        for group in self.letter_groups:
            if all(map(lambda x: x not in group, sequences)):
                return self.group_cost
        return self.mismatch_cost

    def d_cost(self, *sequences):
        if not self._ident(*sequences) and sequences[0] in 'HW':
            return self.group_cost
        return self.r_cost(*sequences)

    def __call__(self, s1, s2):
        if not numpy:
            raise ImportError('Please, install numpy for Editex measure')
        if len(s1) == 0:
            return len(s2) * self.mismatch_cost
        if len(s2) == 0:
            return len(s1) * self.mismatch_cost

        d_mat = numpy.zeros((len(s1) + 1, len(s2) + 1), dtype=numpy.int)
        lens = len(s1)
        lent = len(s2)
        s1 = ' ' + s1
        s2 = ' ' + s2

        if not self.local:
            for i in range(1, lens+1):
                d_mat[i, 0] = d_mat[i-1, 0] + self.d_cost(s1[i-1], s1[i])
        for j in range(1, lent+1):
            d_mat[0, j] = d_mat[0, j-1] + self.d_cost(s2[j-1], s2[j])

        for i in range(1, lens+1):
            for j in range(1, lent+1):
                d_mat[i, j] = min(
                    d_mat[i-1, j] + self.d_cost(s1[i-1], s1[i]),
                    d_mat[i, j-1] + self.d_cost(s2[j-1], s2[j]),
                    d_mat[i-1, j-1] + self.r_cost(s1[i], s2[j]),
                )

        return d_mat[lens, lent]


hamming = Hamming()
levenshtein = Levenshtein()
damerau = damerau_levenshtein = DamerauLevenshtein()
jaro = JaroWinkler(long_tolerance=False, winklerize=False)
jaro_winkler = JaroWinkler(long_tolerance=False, winklerize=True)
needleman_wunsch = NeedlemanWunsch()
smith_waterman = SmithWaterman()
gotoh = Gotoh()
strcmp95 = StrCmp95()
mlipns = MLIPNS()
editex = Editex()
