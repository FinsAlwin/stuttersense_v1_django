from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import AudioFile
from .serializers import AudioFileSerializer
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from pydub import AudioSegment
from django.conf import settings
import uuid
from .utils import preprocess_and_split_audio
from .serializers import AudioPredictionSerializer
import shutil
from urllib.parse import urlparse, unquote
from speech.ms_clap import clap_model
from datetime import datetime

# Create your views here.

class AudioFileUploadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        audio_file = request.FILES.get('audio_file')
        if not audio_file:
            return Response({'error': 'No audio file provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create a temporary file to check duration
            temp_path = default_storage.save(f'temp_{audio_file.name}', ContentFile(audio_file.read()))
            temp_full_path = os.path.join(settings.MEDIA_ROOT, temp_path)

            try:
                # Check file duration
                audio = AudioSegment.from_file(temp_full_path)
                duration = len(audio) / 1000  # Convert to seconds

                if duration > 10:
                    os.remove(temp_full_path)
                    return Response({'error': 'Audio duration exceeds 10 seconds'}, status=status.HTTP_400_BAD_REQUEST)

                # Generate unique filename
                file_extension = os.path.splitext(audio_file.name)[1]
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                final_path = os.path.join('audio_files', unique_filename)

                # Save the file to its final location
                with open(temp_full_path, 'rb') as temp_file:
                    final_path = default_storage.save(final_path, ContentFile(temp_file.read()))

                # Create the AudioFile instance
                audio_file_instance = AudioFile.objects.create(
                    user=request.user,
                    audio_file=final_path,
                    duration=duration
                )

                # Generate the playback URL
                playback_url = request.build_absolute_uri(settings.MEDIA_URL + str(audio_file_instance.audio_file))

                # Serialize the response
                serializer = AudioFileSerializer(audio_file_instance)
                response_data = serializer.data
                response_data['playback_url'] = playback_url

                return Response(response_data, status=status.HTTP_201_CREATED)

            finally:
                # Clean up temporary file
                if os.path.exists(temp_full_path):
                    os.remove(temp_full_path)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PredictionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if clap_model is None:
            return Response({
                'error': 'MS-CLAP model not initialized properly',
                'details': 'Please check server logs for initialization errors'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            # Get and clean the audio_url parameter
            audio_url = request.query_params.get('audio_url')
            if not audio_url:
                return Response({'error': 'audio_url parameter is required'}, 
                              status=status.HTTP_400_BAD_REQUEST)

            # Clean the URL and get the file path
            audio_url = unquote(audio_url)
            parsed_url = urlparse(audio_url)
            relative_path = parsed_url.path.split('/media/')[-1]
            audio_path = os.path.join(settings.MEDIA_ROOT, relative_path)

            if not os.path.exists(audio_path):
                return Response({
                    'error': 'Audio file not found',
                    'details': {
                        'checked_path': audio_path,
                        'media_root': settings.MEDIA_ROOT,
                        'relative_path': relative_path
                    }
                }, status=status.HTTP_404_NOT_FOUND)

            # Get direct prediction from MS-CLAP model
            try:
                prediction = clap_model.predict(audio_path)
                if not prediction:
                    return Response({
                        'error': 'Failed to get prediction',
                        'details': 'Model returned no results'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                # Format response similar to Flask app
                response_data = {
                    'filename': os.path.basename(audio_path),
                    'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
                    'msclap_result': prediction,
                    'status': 'success'
                }

                return Response(response_data, status=status.HTTP_200_OK)

            except Exception as e:
                return Response({
                    'error': 'Prediction failed',
                    'details': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return Response({
                'error': str(e),
                'traceback': traceback.format_exc()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
