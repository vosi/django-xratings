# coding=utf-8
from django.dispatch import Signal


xrating_rated = Signal(
    providing_args=['obj', 'score', 'user'])

xrating_will_rate = Signal(
    providing_args=['obj', 'score', 'user'])
