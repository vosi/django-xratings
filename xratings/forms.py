# coding=utf-8
from __future__ import unicode_literals

from django import forms


__all__ = ('RatingField',)


class RatingField(forms.ChoiceField):
    pass
