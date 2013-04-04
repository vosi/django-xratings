# coding=utf-8
from django import template
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.template.loader import render_to_string


register = template.Library()


class RatingByRequestNode(template.Node):
    def __init__(self, request, obj, context_var):
        self.request = request
        self.obj, self.field_name = obj.split('.')
        self.context_var = context_var

    def render(self, context):
        try:
            request = template.resolve_variable(self.request, context)
            obj = template.resolve_variable(self.obj, context)
            field = getattr(obj, self.field_name)
        except (template.VariableDoesNotExist, AttributeError):
            return ''
        try:
            vote = field.get_rating_for_user(request.user,
                                             request.META['REMOTE_ADDR'],
                                             request.COOKIES)
            context[self.context_var] = vote
        except ObjectDoesNotExist:
            context[self.context_var] = 0
        return ''


def get_rating_by_request(parser, token):
    """
        {% rating_by_request request on instance as vote %}
    """

    bits = token.contents.split()
    if len(bits) != 6:
        raise template.TemplateSyntaxError("'%s' tag takes exactly five "
                                           "arguments" % bits[0])
    if bits[2] != 'on':
        raise template.TemplateSyntaxError("second argument to '%s' tag must "
                                           "be 'on'" % bits[0])
    if bits[4] != 'as':
        raise template.TemplateSyntaxError("fourth argument to '%s' tag must "
                                           "be 'as'" % bits[0])
    return RatingByRequestNode(bits[1], bits[3], bits[5])
register.tag('rating_by_request', get_rating_by_request)


class RatingByUserNode(RatingByRequestNode):
    def render(self, context):
        try:
            user = template.resolve_variable(self.request, context)
            obj = template.resolve_variable(self.obj, context)
            field = getattr(obj, self.field_name)
        except template.VariableDoesNotExist:
            return ''
        try:
            vote = field.get_rating_for_user(user)
            context[self.context_var] = vote
        except ObjectDoesNotExist:
            context[self.context_var] = 0
        return ''


def do_rating_by_user(parser, token):
    """
        {% rating_by_user user on instance as vote %}
    """

    bits = token.contents.split()
    if len(bits) != 6:
        raise template.TemplateSyntaxError("'%s' tag takes exactly five "
                                           "arguments" % bits[0])
    if bits[2] != 'on':
        raise template.TemplateSyntaxError("second argument to '%s' tag must "
                                           "be 'on'" % bits[0])
    if bits[4] != 'as':
        raise template.TemplateSyntaxError("fourth argument to '%s' tag must "
                                           "be 'as'" % bits[0])
    return RatingByUserNode(bits[1], bits[3], bits[5])
register.tag('rating_by_user', do_rating_by_user)


class RatingField(template.Node):
    def __init__(self, request, obj):
        self.request = request
        self.obj, self.field_name = obj.split('.')

    def render(self, context):
        try:
            request = template.resolve_variable(self.request, context)
            obj = template.resolve_variable(self.obj, context)
            field = getattr(obj, self.field_name)
        except (template.VariableDoesNotExist, AttributeError):
            return ''

        ct = ContentType.objects.get_for_model(obj)

        try:
            vote = field.get_rating_for_user(request.user,
                                             request.META['REMOTE_ADDR'],
                                             request.COOKIES)
        except ObjectDoesNotExist:
            vote = None

        template_search_list = ['xratings/widget.html']
        liststr = render_to_string(template_search_list, {
            'choices': field.field.choices,
            'rating_type': field.field.name,
            'vote': vote,
            'content_type_id': ct.pk,
            'object_id': obj.pk,
            'votes': field
        }, context)
        return liststr


def get_rating_field(parser, token):
    """
        {% rating_field for request on instance  %}
    """

    bits = token.contents.split()
    if len(bits) != 5:
        raise template.TemplateSyntaxError("'%s' tag takes exactly five "
                                           "arguments" % bits[0])
    if bits[1] != 'for':
        raise template.TemplateSyntaxError("first argument to '%s' tag must "
                                           "be 'for'" % bits[0])
    if bits[3] != 'on':
        raise template.TemplateSyntaxError("third argument to '%s' tag must "
                                           "be 'on'" % bits[0])
    return RatingField(bits[2], bits[4])
register.tag('rating_field', get_rating_field)
