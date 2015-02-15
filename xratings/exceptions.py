# coding=utf-8
from __future__ import unicode_literals


class InvalidRating(ValueError):
    pass


class AuthRequired(TypeError):
    pass


class CannotChangeVote(Exception):
    pass


class CannotDeleteVote(Exception):
    pass


class IPLimitReached(Exception):
    pass
