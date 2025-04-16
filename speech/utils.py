import os
import librosa
import numpy as np
from pydub import AudioSegment
import torch
import torch.nn.functional as F
from django.conf import settings

# Constants
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 30
MIN_SEGMENT_LENGTH = 500  # milliseconds
SEGMENT_LENGTH = 3000  # 3 seconds in milliseconds

def create_segment_folders(filename):
    base_name = os.path.splitext(os.path.basename(filename))[0]
    base_folder = os.path.join(settings.MEDIA_ROOT, 'predictions', base_name)
    fluent_folder = os.path.join(base_folder, 'fluent')
    disfluent_folder = os.path.join(base_folder, 'disfluent')
    for folder in [base_folder, fluent_folder, disfluent_folder]:
        os.makedirs(folder, exist_ok=True)
    return base_folder, fluent_folder, disfluent_folder

def preprocess_and_split_audio(audio_path):
    try:
        print(f"Loading audio from: {audio_path}")  # Debug print
        audio_segment = AudioSegment.from_file(audio_path)
        duration = len(audio_segment)
        segments = []

        # Create temp directory if it doesn't exist
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        # Split into 3-second segments
        for start in range(0, duration, SEGMENT_LENGTH):
            end = min(start + SEGMENT_LENGTH, duration)
            if end - start >= MIN_SEGMENT_LENGTH:
                segment = audio_segment[start:end]
                # Save segment temporarily
                temp_path = os.path.join(temp_dir, f'segment_{start}_{end}.wav')
                segment.export(temp_path, format='wav')
                
                segments.append({
                    'path': temp_path,
                    'start_time': start,
                    'end_time': end
                })
                print(f"Created segment: {temp_path}")  # Debug print

        return segments
    except Exception as e:
        import traceback
        print(f"Error preprocessing audio: {e}")
        print(traceback.format_exc())
        return None

def analyze_audio_with_msclap(audio_path, clap_model):
    try:
        print(f"Analyzing segment: {audio_path}")  # Debug print
        classes = {
            'speech with stuttering characterized by repeated sounds or syllables, like "b-b-ball"': 'repetition',
            'speech with stuttering featuring prolonged sounds, such as "ssssun" or "mmmmmilk"': 'prolongation',
            'speech with stuttering marked by silent blocks or pauses before words, like " [pause] sun"': 'blocks',
            'speech with stuttering including frequent interjections like "um," "uh," or "you know"': 'fillers',
            'speech with stuttering involving phrase restarts or revisions, such as "I-I mean, we went"': 'restarts',
            'speech partially obscured by background chatter from multiple people talking': 'background_chatter',
            'speech drowned out by loud environmental noise like traffic, fans, or machinery': 'environmental_noise',
            'audio with no clear speech, only silence or faint ambient sounds': 'silent'
        }

        prompts = [f"The/audio contains: {key}" for key in classes.keys()]
        
        audio_emb = clap_model.get_audio_embeddings([audio_path], resample=True)
        text_emb = clap_model.get_text_embeddings(prompts)
        similarity = clap_model.compute_similarity(audio_emb, text_emb)
        
        similarity = F.softmax(similarity / 0.1, dim=1)
        values, indices = similarity[0].topk(3)
        
        return {
            'classification': list(classes.values())[indices[0].item()],
            'confidence': float(values[0].item() * 100),
            'details': [
                {
                    'class': list(classes.values())[indices[i].item()], 
                    'confidence': float(values[i].item() * 100)
                }
                for i in range(len(indices))
            ]
        }
    except Exception as e:
        import traceback
        print(f"MSCLAP analysis failed: {e}")
        print(traceback.format_exc())
        return None 