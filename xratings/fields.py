# coding=utf-8
from __future__ import unicode_literals

from hashlib import md5
from django.conf import settings

from django.utils.six import python_2_unicode_compatible
from django.utils.timezone import now
from django.contrib.contenttypes.models import ContentType
from django.db.models import IntegerField, FloatField
from django_extensions.db.fields.json import JSONField

from xratings.default_settings import RATINGS_VOTES_PER_IP
from xratings.models import Vote
from xratings.exceptions import (InvalidRating, CannotDeleteVote, AuthRequired,
                                IPLimitReached, CannotChangeVote)
from xratings.default_settings import RATINGS_DEFAULT_FORMULA, \
    RATINGS_VOTES_PER_IP_TIMEDELTA

if 'django.contrib.contenttypes' not in settings.INSTALLED_APPS:
    raise ImportError('xratings requires django.contrib.contenttypes in your '
                      'INSTALLED_APPS')


__all__ = ('Rating', 'RatingField', 'AnonymousRatingField')


def md5_hexdigest(value):
    return md5(value).hexdigest()


class Rating(object):
    def __init__(self, score, votes):
        self.scores = None
        self.score_month = None
        self.score_week = None
        self.score_day = None
        self.score = score
        self.votes = votes


@python_2_unicode_compatible
class RatingManager(object):
    def __init__(self, instance, field):
        self.content_type = None
        self.instance = instance
        self.field = field

        self.score_field_name = '%s_score' % (self.field.name,)
        self.score_day_field_name = '%s_day' % (self.field.name,)
        self.score_week_field_name = '%s_week' % (self.field.name,)
        self.score_month_field_name = '%s_month' % (self.field.name,)
        self.scores_field_name = '%s_scores' % (self.field.name,)

    def __str__(self):
        return '%d' % self.get_rating()

    def get_ratings(self):
        # Returns a Vote QuerySet for this rating field.
        return Vote.objects.filter(content_type=self.get_content_type(),
                                   object_id=self.instance.pk,
                                   key=self.field.key)

    def get_rating(self):
        # Returns the calculated rating.
        return self.field.rating_calculator(self.scores, self.field.range)

    def get_real_rating(self):
        # Returns the unmodified rating.
        if len(self.scores) == 0:
            return 0
        return sum([a * b for a, b in zip(self.field.range, self.scores)])

    def get_sum_votes(self):
        # Returns number of votes
        return sum(self.scores)

    def get_avg_rating(self):
        # Returns simple avg rating
        if self.get_sum_votes() == 0:
            return 0
        return float(self.get_real_rating()) / self.get_sum_votes()

    def get_rating_for_user(self, user, ip_address=None, cookies=None):
        # Returns the rating for a user or anonymous IP.
        if not cookies:
            cookies = {}
        kwargs = {
            'content_type': self.get_content_type(),
            'object_id': self.instance.pk,
            'key': self.field.key
        }

        if not (user and user.is_authenticated()):
            if not ip_address:
                raise ValueError('``user`` or ``ip_address`` must be present.')
            kwargs['user__isnull'] = True
            kwargs['ip_address'] = ip_address
        else:
            kwargs['user'] = user

        use_cookies = (self.field.allow_anonymous and self.field.use_cookies)
        if use_cookies:
            # TODO: move 'vote-%d.%d.%s' to settings or something
            cookie_name = 'vote-%d.%d.%s' % (
                kwargs['content_type'].pk, kwargs['object_id'],
                kwargs['key'][:6],)  # -> md5_hexdigest?
            cookie = cookies.get(cookie_name)
            if cookie:
                kwargs['cookie'] = cookie
            else:
                kwargs['cookie__isnull'] = True
        try:
            rating = Vote.objects.get(**kwargs)
            return rating.score
        except Vote.MultipleObjectsReturned:
            pass
        except Vote.DoesNotExist:
            pass
        return

    def add(self, score, user, ip_address, cookies=None, commit=True):
        if not cookies:
            cookies = {}

        try:
            score = int(score)
        except (ValueError, TypeError):
            raise InvalidRating('%s is not a valid choice for %s' %
                                (score, self.field.name))

        delete = (score == 0)
        if delete and not self.field.allow_delete:
            raise CannotDeleteVote('you are not allowed to delete votes for %s' %
                                   (self.field.name,))

        if not self.field.check_range(score):
            raise InvalidRating('%s is not a valid choice for %s' %
                                (score, self.field.name))

        is_anonymous = (user is None or not user.is_authenticated())
        if is_anonymous and not self.field.allow_anonymous:
            raise AuthRequired('user must be a user, not `%r`' % (user,))

        if is_anonymous:
            user = None

        defaults = {
            'score': score,
            'ip_address': ip_address
        }
        kwargs = {
            'content_type': self.get_content_type(),
            'object_id': self.instance.pk,
            'key': self.field.key,
            'user': user
        }
        if not user:
            kwargs['ip_address'] = ip_address

        use_cookies = (self.field.allow_anonymous and self.field.use_cookies)
        if use_cookies:
            defaults['cookie'] = now().strftime('%Y%m%d%H%M%S%f')
            cookie_name = 'vote-%d.%d.%s' % (kwargs['content_type'].pk,
                                             kwargs['object_id'],
                                             kwargs['key'][:6],)
            cookie = cookies.get(cookie_name)
            if not cookie:
                kwargs['cookie__isnull'] = True
            kwargs['cookie'] = cookie

        try:
            rating, created = Vote.objects.get(**kwargs), False
        except Vote.DoesNotExist:
            if delete:
                raise CannotDeleteVote(
                    'attempt to find and delete your vote for %s is failed' %
                    (self.field.name,))
            if RATINGS_VOTES_PER_IP > 0:
                num_votes = Vote.objects.filter(
                    content_type=kwargs['content_type'],
                    object_id=kwargs['object_id'],
                    key=kwargs['key'],
                    ip_address=ip_address,
                    date_changed__gte=now() - RATINGS_VOTES_PER_IP_TIMEDELTA
                ).count()
                if num_votes >= RATINGS_VOTES_PER_IP:
                    raise IPLimitReached()
            kwargs.update(defaults)
            if use_cookies:
                cookie = defaults['cookie']
                kwargs.pop('cookie__isnull', '')
            rating, created = Vote.objects.create(**kwargs), True

        # self.score = self.get_rating()

        if not created:
            if self.field.can_change_vote:
                self.scores[self.field.range.index(rating.score)] -= 1
                if not delete:
                    self.scores[self.field.range.index(score)] += 1
                else:
                    rating.delete()
            else:
                raise CannotChangeVote()
        else:
            if not (isinstance(self.scores, list) and len(self.scores) == len([0] * len(self.field.range))):
                self.scores = [0] * len(self.field.range)
            self.scores[self.field.range.index(score)] += 1

        self.score = self.get_rating()

        # return value
        adds = {
            'status_code': 0,
            'instance': self.instance,
            'score': self.score,
            'score_avg': self.get_avg_rating(),
            'score_sum': self.get_real_rating(),
            'scores': self.scores,
            'deleted': delete,
            'created': created}
        if use_cookies:
            adds['cookie_name'] = cookie_name
            adds['cookie'] = cookie
        return adds

    def _rm_vote(self, score):
        self.scores[self.field.range.index(score)] -= 1
        self.score = self.get_rating()

    @property
    def score(self, default=None):
        return getattr(self.instance, self.score_field_name, default)

    @score.setter
    def score(self, value):
        old = getattr(self.instance, self.score_field_name, 0)

        old_day = getattr(self.instance, self.score_day_field_name, 0)
        new_day = old_day + value - old
        setattr(self.instance, self.score_day_field_name, new_day)

        old_week = getattr(self.instance, self.score_week_field_name, 0)
        new_week = old_week + value - old
        setattr(self.instance, self.score_week_field_name, new_week)

        old_month = getattr(self.instance, self.score_month_field_name, 0)
        new_month = old_month + value - old
        setattr(self.instance, self.score_month_field_name, new_month)

        setattr(self.instance, self.score_field_name, value)

    @property
    def scores(self, default=None):
        return getattr(self.instance, self.scores_field_name, default)

    @scores.setter
    def scores(self, value):
        setattr(self.instance, self.scores_field_name, value)

    def get_content_type(self):
        if self.content_type is None:
            self.content_type = ContentType.objects\
                .get_for_model(self.instance)
        return self.content_type


class RatingCreator(object):
    def __init__(self, field):
        self.field = field
        self.score_field_name = '%s_score' % (self.field.name,)
        self.score_day_field_name = '%s_day' % (self.field.name,)
        self.score_week_field_name = '%s_week' % (self.field.name,)
        self.score_month_field_name = '%s_month' % (self.field.name,)
        self.scores_field_name = '%s_scores' % (self.field.name,)

    def __get__(self, instance, type=None):
        if instance is None:
            raise AttributeError('Can only be accessed via an instance.')
            # return self.field
        return RatingManager(instance, self.field)


class RatingField(IntegerField):
    def __init__(self, *args, **kwargs):
        if 'choices' not in kwargs:
            kwargs['choices'] = [1, 2]
        if not isinstance(kwargs['choices'], list):
            raise TypeError('%s: invalid type for attribute `choices`. '
                            'Must be a list.' % (self.__class__.__name__,))
        self.range = kwargs['choices']
        self.can_change_vote = kwargs.pop('can_change_vote', False)
        self.allow_anonymous = kwargs.pop('allow_anonymous', False)
        self.use_cookies = kwargs.pop('use_cookies', False)
        self.allow_delete = kwargs.pop('allow_delete', False)
        self.rating_calculator = kwargs.pop('formula', RATINGS_DEFAULT_FORMULA)
        kwargs['editable'] = False
        kwargs['default'] = 0
        kwargs['blank'] = True
        super(RatingField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name, virtual_only=False):
        self.name = name

        # Computed rating
        self.score_field = FloatField(editable=False, db_index=True,
                                      default=0)
        cls.add_to_class('%s_score' % (self.name,), self.score_field)

        self.score_day_field = FloatField(editable=False, db_index=True,
                                          default=0)
        cls.add_to_class('%s_day' % (self.name,), self.score_day_field)

        self.score_week_field = FloatField(editable=False, db_index=True,
                                           default=0)
        cls.add_to_class('%s_week' % (self.name,), self.score_week_field)

        self.score_month_field = FloatField(editable=False, db_index=True,
                                            default=0)
        cls.add_to_class('%s_month' % (self.name,), self.score_month_field)

        # Each score qty [5,9]
        scores = [0] * len(self.range)
        self.scores_field = JSONField(editable=False, default=scores)
        cls.add_to_class('%s_scores' % (self.name,), self.scores_field)
        self.key = md5_hexdigest(self.name)

        field = RatingCreator(self)

        if not hasattr(cls, '_xratings'):
            cls._xratings = []
        cls._xratings.append(self)

        setattr(cls, name, field)

    def get_db_prep_save(self, value, connection):
        # XXX: what happens here?
        pass

    def get_db_prep_lookup(self, lookup_type, value, connection,
                           prepared=False):
        raise NotImplementedError(self.get_db_prep_lookup)

    def formfield(self, **kwargs):
        defaults = {'form_class': RatingField}
        defaults.update(kwargs)
        return super(RatingField, self).formfield(**defaults)

    def check_range(self, score):
        if isinstance(self.range, list):
            return score in self.range
        return False


class AnonymousRatingField(RatingField):
    def __init__(self, *args, **kwargs):
        kwargs['allow_anonymous'] = True
        super(AnonymousRatingField, self).__init__(*args, **kwargs)
