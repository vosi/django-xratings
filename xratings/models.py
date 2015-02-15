# coding=utf-8
from __future__ import unicode_literals

from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.utils.encoding import python_2_unicode_compatible

from ratings.managers import VoteManager


@python_2_unicode_compatible
class Vote(models.Model):
    key = models.CharField(max_length=32)
    score = models.IntegerField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True,
                             null=True, related_name='votes')
    ip_address = models.GenericIPAddressField(unpack_ipv4=True)
    cookie = models.CharField(max_length=32, blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True, editable=False)
    date_changed = models.DateTimeField(auto_now=True, editable=False)

    content_type = models.ForeignKey(ContentType, related_name='votes')
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey()

    objects = VoteManager()

    class Meta:
        unique_together = (
            ('content_type', 'object_id', 'key', 'user',
             'ip_address', 'cookie'))

    def __str__(self):
        return '%s voted %s on %s' % (
            self.user_display, self.score, self.content_object)

    @property
    def user_display(self):
        if self.user:
            return '%s (%s)' % (self.user.username, self.ip_address)
        return self.ip_address
