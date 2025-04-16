import os
import torch
import torch.nn.functional as F
from msclap import CLAP
import traceback
from .models import ClassificationPrompt, PredictionSettings

class MSCLAPModel:
    def __init__(self):
        try:
            # Force CPU-only operation as in your Flask app
            os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
            print("Initializing MS-CLAP model...")
            self.model = CLAP(version='2023', use_cuda=False)
            print("MS-CLAP model initialized successfully")
            
        except Exception as e:
            print(f"Error initializing MS-CLAP model: {e}")
            traceback.print_exc()
            raise

    def get_active_settings(self):
        try:
            return PredictionSettings.objects.filter(is_active=True).first() or \
                   PredictionSettings.objects.create(
                       name="Default Settings",
                       softmax_temperature=0.1,
                       min_segment_duration=1.0,
                       max_segment_duration=3.0,
                       silence_threshold_db=15.0
                   )
        except Exception as e:
            print(f"Error getting settings: {e}")
            return None

    def get_active_prompts(self):
        try:
            prompts = ClassificationPrompt.objects.filter(is_active=True).order_by('-priority')
            print(f"Found {prompts.count()} active prompts in database")  # Debug log
            
            if prompts.exists():
                # Log the prompts we're using
                for p in prompts:
                    print(f"Using prompt: {p.name} - {p.prompt} (priority: {p.priority})")
                return prompts
                
            else:
                print("No prompts found, creating defaults...")  # Debug log
                # Create default prompts if none exist
                defaults = [
                    ('repetition', 'speech with stuttering characterized by repeated sounds or syllables'),
                    ('prolongation', 'speech with stuttering featuring prolonged sounds'),
                    ('blocks', 'speech with stuttering marked by silent blocks or pauses'),
                    ('fillers', 'speech with stuttering including frequent interjections'),
                    ('restarts', 'speech with stuttering involving phrase restarts or revisions'),
                ]
                for priority, (name, prompt) in enumerate(defaults):
                    ClassificationPrompt.objects.create(
                        name=name,
                        prompt=prompt,
                        priority=len(defaults) - priority
                    )
                return ClassificationPrompt.objects.filter(is_active=True)
                
        except Exception as e:
            print(f"Error getting prompts: {e}")
            traceback.print_exc()  # Add full traceback for debugging
            return []

    def predict(self, audio_path):
        try:
            settings = self.get_active_settings()
            if not settings:
                raise ValueError("No active prediction settings found")

            prompts = self.get_active_prompts()
            if not prompts:
                raise ValueError("No active classification prompts found")

            # Debug logging
            print(f"\nMaking prediction with {prompts.count()} prompts:")
            for p in prompts:
                print(f"- {p.name}: {p.prompt}")

            # Generate prompts
            prompt_texts = [f"The/audio contains: {p.prompt}" for p in prompts]
            prompt_names = [p.name for p in prompts]
            
            # Get embeddings
            audio_emb = self.model.get_audio_embeddings([audio_path], resample=True)
            text_emb = self.model.get_text_embeddings(prompt_texts)
            
            # Compute similarity with dynamic temperature
            similarity = self.model.compute_similarity(audio_emb, text_emb)
            similarity = F.softmax(similarity / settings.softmax_temperature, dim=1)
            values, indices = similarity[0].topk(min(3, len(prompts)))
            
            # Format results (removed settings_used and prompts_used)
            return {
                'classification': prompt_names[indices[0].item()],
                'confidence': float(values[0].item() * 100),
                'details': [
                    {
                        'class': prompt_names[indices[i].item()],
                        'confidence': float(values[i].item() * 100)
                    }
                    for i in range(len(indices))
                ]
            }
            
        except Exception as e:
            print(f"MS-CLAP prediction error: {e}")
            traceback.print_exc()
            return None

# Initialize the model when the module is loaded
print("Initializing MS-CLAP model...")
try:
    clap_model = MSCLAPModel()
    print("MS-CLAP model initialized successfully")
except Exception as e:
    print(f"Failed to initialize MS-CLAP model: {e}")
    clap_model = None 