import os
import pickle
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.sequence import pad_sequences

# Model ini dibuat dengan Keras 3 format (.keras), jadi load langsung dengan keras bawaan TF 2.16+
# JANGAN pakai tf_keras (legacy Keras 2) karena tidak kompatibel dengan format Keras 3
from keras.models import load_model
print("ℹ️ Using Keras 3 for model loading")

class SentimentAnalyzer:
    def __init__(self, model_path, tokenizer_path):
        self.model = None
        self.tokenizer = None
        self.model_path = model_path
        self.tokenizer_path = tokenizer_path
        self.max_len = 100 # Default assumption, will try to infer from model
        self.classes = ['negatif', 'positif'] # 0: Negatif, 1: Positif (usually)

        self._load_artifacts()

    def _load_artifacts(self):
        try:
            print(f"🔄 Loading Sentiment Model from {self.model_path}...")
            self.model = load_model(self.model_path)
            
            # Infer expected input length from model
            # Model input shape is usually (None, MAX_LEN)
            try:
                input_shape = self.model.input_shape
                if isinstance(input_shape, tuple) and input_shape[1] is not None:
                    self.max_len = input_shape[1]
                    print(f"ℹ️ Inferred MAX_LEN from model: {self.max_len}")
            except Exception as e:
                print(f"⚠️ Could not infer input shape: {e}. Using default MAX_LEN={self.max_len}")

            print(f"🔄 Loading Tokenizer from {self.tokenizer_path}...")
            with open(self.tokenizer_path, 'rb') as f:
                self.tokenizer = pickle.load(f)
            
            print("✅ Sentiment Analyzer Loaded Successfully")
        except Exception as e:
            print(f"❌ Failed to load Sentiment Analyzer: {e}")
            self.model = None

    def predict(self, text):
        if not self.model or not self.tokenizer:
            return None

        try:
            # 1. Tokenize & Sequence
            # tokenizer.texts_to_sequences expects a list of texts
            seq = self.tokenizer.texts_to_sequences([text])
            
            # 2. Pad
            padded = pad_sequences(seq, maxlen=self.max_len)
            
            # 3. Predict
            # Output is usually a probability (sigmoid -> 0..1) or softmax (2 classes)
            # Check output shape
            pred = self.model.predict(padded, verbose=0)
            
            # Assuming Binary Classification (Sigmoid) -> 1 neuron output 0..1
            # OR Categorical (Softmax) -> 2 neuron output [prob_neg, prob_pos]
            
            result_label = "unknown"
            
            if pred.shape[-1] == 1:
                # Binary: 0=Negatif, 1=Positif (Common convention)
                score = pred[0][0]
                result_label = 'positif' if score > 0.5 else 'negatif'
            else:
                # Multiclass / Categorical
                # Assuming index 0=Negatif, 1=Positif
                idx = np.argmax(pred[0])
                result_label = self.classes[idx] if idx < len(self.classes) else "unknown"

            return result_label

        except Exception as e:
            print(f"❌ Prediction Error: {e}")
            return None

# Singleton instance placeholder
analyzer = None

def init_analyzer(base_dir):
    global analyzer
    model_path = os.path.join(base_dir, 'sentiment_assets', 'bilstm_model.keras')
    token_path = os.path.join(base_dir, 'sentiment_assets', 'tokenizer_jaki.pkl')
    
    if os.path.exists(model_path) and os.path.exists(token_path):
        analyzer = SentimentAnalyzer(model_path, token_path)
        print(f"🔍 DEBUG: analyzer after assignment = {analyzer}, model = {analyzer.model if analyzer else 'N/A'}")
    else:
        print("⚠️ Sentiment assets not found. Skipper loading.")

def predict_sentiment(text):
    if analyzer:
        return analyzer.predict(text)
    return None
