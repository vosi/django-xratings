# coding=utf-8
from __future__ import unicode_literals

import itertools
from operator import itemgetter

from django.db.models import Manager
from django.db.models.query import QuerySet
from django.contrib.contenttypes.models import ContentType


class VoteQuerySet(QuerySet):
    def delete(self, *args, **kwargs):
        # Handles updating the related `votes` and `score` fields attached to
        # the model.
        qs = self.distinct()\
            .values_list('score', 'content_type', 'object_id')\
            .order_by('content_type', 'object_id')

        qs = list(qs)
        for ct_type, votes_a in itertools.groupby(qs, itemgetter(1)):
            model = ContentType.objects.get(pk=ct_type).model_class()
            for ct_pk, votes_b in itertools.groupby(votes_a, itemgetter(2)):
                obj = model.objects.get(pk=ct_pk)
                for vote in votes_b:
                    for field in getattr(obj, '_xratings', []):
                        getattr(obj, field.name)._rm_vote(score=vote[0])
                obj.save()

        retval = super(VoteQuerySet, self).delete(*args, **kwargs)
        return retval


class VoteManager(Manager):
    def get_query_set(self):
        return VoteQuerySet(self.model)

    def get_for_user_in_bulk(self, objects, user):
        objects = list(objects)
        if len(objects) > 0:
            ctype = ContentType.objects.get_for_model(objects[0])
            votes = self.filter(content_type__pk=ctype.id,
                                object_id__in=[obj._get_pk_val()
                                               for obj in objects],
                                user__pk=user.id)
            vote_dict = dict([(vote.object_id, vote) for vote in votes])
        else:
            vote_dict = {}
        return vote_dict
