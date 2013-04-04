# coding=utf-8
from django.contrib.contenttypes.models import ContentType
from django.views.generic import View
from exceptions import *
from xadditions.views.common import JSONResponseMixin
from xratings.signals import xrating_rated, xrating_will_rate


class AddRatingView(View, JSONResponseMixin):
    def get_context_data(self, **kwargs):
        return {'params': kwargs}

    def post(self, request, *args, **kwargs):
        add_response = self.add(request)

        if add_response.get('status_code', 100) == 0:
            if add_response.get('created', False):
                add_response.update({
                    'content': 'Vote recorded.'
                })
            else:
                if add_response.get('deleted', False):
                    add_response.update({
                        'content': 'Vote deleted.'
                    })
                else:
                    add_response.update({
                        'content': 'Vote modified.'
                    })
            del add_response['instance']

        response = self.render_to_response(add_response)

        if 'cookie' in add_response:
            cookie_name, cookie = add_response['cookie_name'], \
                add_response['cookie']
            if 'deleted' in add_response:
                response.delete_cookie(cookie_name)
            else:
                response.set_cookie(cookie_name, cookie, 31536000)

        return response

    def add(self, request):

        try:
            content_type = int(request.POST.get('content_type_id'))
            object_id = int(request.POST.get('object_id'))
            rating_type = request.POST.get('rating_type')
            score = int(request.POST.get('score'))
        except TypeError:
            return self.invalid_params_response()

        try:
            ct = ContentType.objects.get(pk=content_type)
        except ContentType.DoesNotExist:
            return self.invalid_ct_response()

        try:
            obj = ct.model_class().objects.get(pk=object_id)
        except ct.model_class().DoesNotExist:
            return self.invalid_obj_response()

        try:
            field = getattr(obj, rating_type)
        except AttributeError:
            return self.invalid_field_response()

        if not score in field.field.range:
            return self.invalid_score_response()

        responses = xrating_will_rate.send(
            sender=self, obj=obj, score=score, user=request.user)

        #TODO: somehow, pass a message to response
        for (receiver, response) in responses:
            if not response:
                return self.abort_will_rate_response()

        try:
            add = field.add(score, request.user,
                            request.META.get('REMOTE_ADDR'), request.COOKIES)
        except IPLimitReached:
            return self.too_many_votes_from_ip_response()
        except AuthRequired:
            return self.authentication_required_response()
        except InvalidRating:
            return self.invalid_rating_response()
        except CannotChangeVote:
            return self.cannot_change_vote_response()
        except CannotDeleteVote:
            return self.cannot_delete_vote_response()

        xrating_rated.send(
            sender=self, obj=add['instance'], score=score, user=request.user)

        add.update({
            'content_type': content_type,
            'object_id': object_id,
            'rating_type': rating_type,
            'voted': score
        })
        return add

    def authentication_required_response(self):
        return {'content': 'You must be logged in to vote.',
                'status_code': 1}

    def cannot_change_vote_response(self):
        return {'content': 'You have already voted.',
                'status_code': 2}

    def cannot_delete_vote_response(self):
        return {'content': 'You can\'t delete this vote.',
                'status_code': 3}

    def invalid_params_response(self):
        return {'content': 'Invalid params provided.',
                'status_code': 4}

    def invalid_field_response(self):
        return {'content': 'Invalid field name.',
                'status_code': 5}

    def invalid_ct_response(self):
        return {'content': 'Invalid ct provided.',
                'status_code': 6}

    def invalid_obj_response(self):
        return {'content': 'Invalid obj provided.',
                'status_code': 7}

    def invalid_rating_response(self):
        return {'content': 'Invalid rating value.',
                'status_code': 8}

    def invalid_score_response(self):
        return {'content': 'Invalid score value.',
                'status_code': 9}

    def too_many_votes_from_ip_response(self):
        return {'content': 'Too many votes from this IP address for '
                           'this object.',
                'status_code': 10}

    def abort_will_rate_response(self):
        return {'content': 'Vote aborted by \'will rate\' signal.',
                'status_code': 11}
