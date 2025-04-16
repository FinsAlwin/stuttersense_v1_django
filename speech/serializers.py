from rest_framework import serializers
from .models import AudioFile

class AudioFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioFile
        fields = ['id', 'audio_file', 'duration', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

class PredictionResultSerializer(serializers.Serializer):
    segment_start = serializers.FloatField()
    segment_end = serializers.FloatField()
    classification = serializers.CharField()
    confidence = serializers.FloatField()
    details = serializers.ListField(child=serializers.DictField())

class AudioPredictionSerializer(serializers.Serializer):
    audio_url = serializers.URLField()
    segments = PredictionResultSerializer(many=True) 