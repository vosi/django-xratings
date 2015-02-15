# coding=utf-8
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from xratings.views import AddRatingView

urlpatterns = patterns('',
    url(r'xrating/add/$', AddRatingView.as_view(), name='rating_add'),
)

