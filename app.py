from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
from gtts import gTTS
from PyDictionary import PyDictionary
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app)

# Configuration
app.config['UPLOAD_FOLDER'] = 'static/audio'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

dictionary = PyDictionary()

class PronunciationGuide:
    def __init__(self):
        self.history = []
        self.favorites = []

    def add_to_history(self, word):
        if word not in self.history:
            self.history.insert(0, word)
            self.history = self.history[:10]  # Keep only last 10

    def toggle_favorite(self, word):
        if word in self.favorites:
            self.favorites.remove(word)
            return False
        else:
            self.favorites.append(word)
            return True

pronunciation_data = PronunciationGuide()

@app.route('/pronounce', methods=['POST'])
def pronounce_word():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        word = data.get('word', '').strip().lower()
        if not word:
            return jsonify({'error': 'Word parameter missing'}), 400
        if not re.match(r'^[a-zA-Z]+$', word):
            return jsonify({'error': 'Only alphabetic characters allowed'}), 400
        
        pronunciation_data.add_to_history(word)
        
        # Generate audio
        audio_filename = f"{secure_filename(word)}.mp3"
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
        
        if not os.path.exists(audio_path):
            try:
                tts = gTTS(text=word, lang='en', slow=False)
                tts.save(audio_path)
            except Exception as e:
                return jsonify({'error': f"Audio generation failed: {str(e)}"}), 500
        
        return jsonify({
            'word': word,
            'audio_url': f'/static/audio/{audio_filename}',
            'pronunciation': get_pronunciation_guide(word),
            'synonyms': dictionary.synonym(word) or [],
            'difficulty': assess_difficulty(word),
            'examples': generate_examples(word),
            'is_favorite': word in pronunciation_data.favorites
        })
        
    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def get_pronunciation_guide(word):
    syllables = re.findall(r'[^aeiouy]*[aeiouy]+[^aeiouy]*', word, re.I)
    return '-'.join(syllables).lower()

def assess_difficulty(word):
    length = len(word)
    if length <= 4: return 'Easy'
    elif length <= 7: return 'Medium'
    else: return 'Hard'

def generate_examples(word):
    return [
        f"Please pronounce the word '{word}'",
        f"Can you use '{word}' in a sentence?",
        f"Let me hear you say '{word}' again"
    ]

@app.route('/history', methods=['GET'])
def get_history():
    return jsonify({'history': pronunciation_data.history})

@app.route('/favorites', methods=['GET', 'POST', 'DELETE'])
def manage_favorites():
    if request.method == 'POST':
        word = request.json.get('word', '').lower().strip()
        if word:
            is_favorite = pronunciation_data.toggle_favorite(word)
            return jsonify({'success': True, 'is_favorite': is_favorite})
        return jsonify({'error': 'Word missing'}), 400
    return jsonify({'favorites': pronunciation_data.favorites})

if __name__ == '__main__':
    os.makedirs('static/audio', exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)