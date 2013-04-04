from datetime import datetime

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from default_settings import RATINGS_USER_MODEL

try:
    from django.utils.timezone import now
except ImportError:
    now = datetime.now

from managers import VoteManager


class Vote(models.Model):
    content_type = models.ForeignKey(ContentType, related_name="votes")
    object_id = models.PositiveIntegerField()
    key = models.CharField(max_length=32)
    score = models.IntegerField()
    user = models.ForeignKey(RATINGS_USER_MODEL, blank=True,
                             null=True, related_name="votes")
    ip_address = models.GenericIPAddressField(unpack_ipv4=True)
    cookie = models.CharField(max_length=32, blank=True, null=True)
    date_added = models.DateTimeField(default=now, editable=False)
    date_changed = models.DateTimeField(default=now, editable=False)

    objects = VoteManager()

    content_object = generic.GenericForeignKey()

    class Meta:
        unique_together = (('content_type', 'object_id', 'key', 'user',
                            'ip_address', 'cookie'))

    def __unicode__(self):
        return u"%s voted %s on %s" % (self.user_display, self.score,
                                       self.content_object)

    def save(self, *args, **kwargs):
        self.date_changed = now()
        super(Vote, self).save(*args, **kwargs)

    def user_display(self):
        if self.user:
            return "%s (%s)" % (self.user.username, self.ip_address)
        return self.ip_address

    user_display = property(user_display)
