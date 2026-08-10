from django.contrib import admin

from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'kind', 'is_published', 'published_at', 'email_sent_at')
    list_filter = ('kind', 'is_published')
    search_fields = ('title', 'body')
    readonly_fields = ('published_at', 'email_sent_at', 'created_at', 'updated_at')
