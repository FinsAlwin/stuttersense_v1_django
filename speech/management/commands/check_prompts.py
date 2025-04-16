from django.core.management.base import BaseCommand
from speech.models import ClassificationPrompt

class Command(BaseCommand):
    help = 'Check and clean up classification prompts'

    def handle(self, *args, **kwargs):
        # List all prompts
        self.stdout.write("Current prompts in database:")
        for prompt in ClassificationPrompt.objects.all():
            self.stdout.write(f"- {prompt.name}: {prompt.prompt} (active: {prompt.is_active})") 