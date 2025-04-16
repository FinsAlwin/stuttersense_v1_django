from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import os
from django.conf import settings
import logging
from django.db.models.signals import pre_delete
from django.dispatch import receiver

# Set up logging
logger = logging.getLogger(__name__)

def user_directory_path(instance, filename):
    # Get the file extension
    ext = os.path.splitext(filename)[1]
    # Generate unique filename
    filename = f"{uuid.uuid4()}{ext}"
    return os.path.join('audio_files', filename)

class AudioFile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    audio_file = models.FileField(upload_to=user_directory_path)
    duration = models.FloatField()  # Duration in seconds
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.user.username}'s audio - {self.uploaded_at.strftime('%Y-%m-%d %H:%M')}"

    def delete(self, *args, **kwargs):
        # Get the file path before deletion
        file_path = self.audio_file.path if self.audio_file else None
        logger.info(f"Attempting to delete audio file: {file_path}")
        
        # Delete the main audio file
        if self.audio_file:
            try:
                if os.path.isfile(self.audio_file.path):
                    os.remove(self.audio_file.path)
                    logger.info(f"Successfully deleted audio file: {self.audio_file.path}")
                else:
                    logger.warning(f"File does not exist: {self.audio_file.path}")
            except Exception as e:
                logger.error(f"Error deleting audio file: {e}")

        # Delete any temporary files associated with this audio
        try:
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
            if os.path.exists(temp_dir):
                for filename in os.listdir(temp_dir):
                    if str(self.id) in filename:
                        file_path = os.path.join(temp_dir, filename)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            logger.info(f"Successfully deleted temporary file: {file_path}")
        except Exception as e:
            logger.error(f"Error deleting temporary files: {e}")

        super().delete(*args, **kwargs)

# Add signal to ensure file deletion even if model is deleted through queryset
@receiver(pre_delete, sender=AudioFile)
def delete_audio_file(sender, instance, **kwargs):
    if instance.audio_file:
        try:
            if os.path.isfile(instance.audio_file.path):
                os.remove(instance.audio_file.path)
                logger.info(f"Signal: Successfully deleted audio file: {instance.audio_file.path}")
            else:
                logger.warning(f"Signal: File does not exist: {instance.audio_file.path}")
        except Exception as e:
            logger.error(f"Signal: Error deleting audio file: {e}")

    # Delete temporary files
    try:
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                if str(instance.id) in filename:
                    file_path = os.path.join(temp_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        logger.info(f"Signal: Successfully deleted temporary file: {file_path}")
    except Exception as e:
        logger.error(f"Signal: Error deleting temporary files: {e}")

class ClassificationPrompt(models.Model):
    name = models.CharField(max_length=50, help_text="Short name for the class (e.g., 'repetition')")
    prompt = models.TextField(help_text="Full prompt text (e.g., 'speech with stuttering characterized by repeated sounds...')")
    is_active = models.BooleanField(default=True, help_text="Whether this prompt should be used in predictions")
    priority = models.IntegerField(default=0, help_text="Higher priority prompts will be used first if there are too many prompts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'name']

    def __str__(self):
        return f"{self.name} ({'active' if self.is_active else 'inactive'})"

class PredictionSettings(models.Model):
    name = models.CharField(max_length=100, unique=True)
    softmax_temperature = models.FloatField(
        default=0.1,
        validators=[MinValueValidator(0.01), MaxValueValidator(1.0)],
        help_text="Temperature for softmax (default: 0.1)"
    )
    min_segment_duration = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.1), MaxValueValidator(10.0)],
        help_text="Minimum segment duration in seconds"
    )
    max_segment_duration = models.FloatField(
        default=3.0,
        validators=[MinValueValidator(0.5), MaxValueValidator(30.0)],
        help_text="Maximum segment duration in seconds"
    )
    silence_threshold_db = models.FloatField(
        default=15.0,
        validators=[MinValueValidator(1.0), MaxValueValidator(60.0)],
        help_text="Silence threshold in dB"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Prediction Settings"
        verbose_name_plural = "Prediction Settings"

    def __str__(self):
        return f"{self.name} ({'active' if self.is_active else 'inactive'})"
