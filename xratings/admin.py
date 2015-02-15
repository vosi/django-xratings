# coding=utf-8
from __future__ import unicode_literals

from django.contrib import admin

from ratings.models import Vote


class VoteAdmin(admin.ModelAdmin):
    list_display = ('content_object', 'user', 'ip_address', 'cookie', 'score',
                    'date_changed')
    list_filter = ('score', 'content_type', 'date_changed')
    search_fields = ('ip_address',)
    raw_id_fields = ('user',)


admin.site.register(Vote, VoteAdmin)
