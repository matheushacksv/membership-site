from django.contrib import admin

from .models import EvolutionConfig, PandaConfig


@admin.register(EvolutionConfig)
class EvolutionConfigAdmin(admin.ModelAdmin):
    list_display = ('instance', 'is_active', 'updated_at')


@admin.register(PandaConfig)
class PandaConfigAdmin(admin.ModelAdmin):
    list_display = ('base_url', 'is_active', 'updated_at')
