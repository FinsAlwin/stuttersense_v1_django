from django.urls import path
from .views import AudioFileUploadView, PredictionView

urlpatterns = [
    path('upload/', AudioFileUploadView.as_view(), name='audio_upload'),
    path('predict/', PredictionView.as_view(), name='predict'),
] 