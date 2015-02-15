# coding=utf-8
from __future__ import unicode_literals

from math import sqrt
from datetime import timedelta

from django.conf import settings

# Used to limit the number of unique IPs that can vote on a single object+field.
#   useful if you're getting rating spam by users registering multiple accounts
RATINGS_VOTES_PER_IP = getattr(settings, 'RATINGS_VOTES_PER_IP', 3)
RATINGS_VOTES_PER_IP_TIMEDELTA = getattr(settings,
                                         'RATINGS_VOTES_PER_IP_TIMEDELTA',
                                         timedelta(days=1))


def rating_bin_formula(scores, vrange):
    #reddit furmula
    if len(scores) == 0:
        return 0
    downs, ups = scores
    n = ups + downs
    if n == 0:
        return 0
    z = 1.25
    p = float(ups) / n

    left = p + 1 / (2 * n) * z * z
    right = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    under = 1 + 1 / n * z * z
    return (left - right) / under


def rating_var_formula(scores, vrange):
    if (not(isinstance(scores, list) and isinstance(vrange, list)) or
            not (sum(scores) > 0 and len(vrange) > 0)):
        return 0
    votes = float(sum(scores))
    vmin = float(0)
    avg = sum([a * b for a, b in zip(vrange, scores)]) / sum(scores)
    fix = 0.1
    return (votes / (votes + vmin)) * avg + (vmin / (votes + vmin)) * fix

RATINGS_DEFAULT_FORMULA = getattr(settings, 'RATINGS_DEFAULT_FORMULA',
                                  rating_bin_formula)
