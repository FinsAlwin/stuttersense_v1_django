from django.contrib import admin
from .models import AudioFile, ClassificationPrompt, PredictionSettings
from django.utils.html import format_html
from django.urls import reverse
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from stuttersense_v1.admin import custom_admin_site

class AudioFileAdmin(admin.ModelAdmin):
    list_display = ('user', 'audio_file_link', 'duration', 'uploaded_at')
    list_filter = ('user', 'uploaded_at')
    search_fields = ('user__username',)
    readonly_fields = ('duration', 'uploaded_at')

    def audio_file_link(self, obj):
        if obj.audio_file:
            download_url = reverse('custom_admin:download_audio', args=[obj.id])
            return format_html(
                '<a href="{}" class="button" download>Download</a>',
                download_url
            )
        return "No file"
    audio_file_link.short_description = 'Audio File'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:audio_id>/download/',
                self.admin_site.admin_view(self.download_audio),
                name='download_audio',
            ),
        ]
        return custom_urls + urls

    def download_audio(self, request, audio_id):
        audio_file = get_object_or_404(AudioFile, id=audio_id)
        response = FileResponse(
            audio_file.audio_file,
            as_attachment=True,
            filename=audio_file.audio_file.name.split('/')[-1]
        )
        return response

class ClassificationPromptAdmin(admin.ModelAdmin):
    list_display = ['name', 'prompt', 'is_active', 'priority', 'updated_at']
    list_filter = ['is_active']
    search_fields = ['name', 'prompt']
    ordering = ['-priority', 'name']

class PredictionSettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'softmax_temperature', 'min_segment_duration', 
                   'max_segment_duration', 'silence_threshold_db', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']

# Register models with the custom admin site
custom_admin_site.register(AudioFile, AudioFileAdmin)
custom_admin_site.register(ClassificationPrompt, ClassificationPromptAdmin)
custom_admin_site.register(PredictionSettings, PredictionSettingsAdmin)
