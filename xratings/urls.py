# coding=utf-8

from django.conf.urls import patterns, url
from xratings.views import AddRatingView

urlpatterns = patterns('',
    url(r'xrating/add/$', AddRatingView.as_view(), name='rating_add'),
)

