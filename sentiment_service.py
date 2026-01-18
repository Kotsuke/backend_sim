import os
import pickle

class SentimentAnalyzer:
    """
    Sentiment Analyzer menggunakan model scikit-learn (.pkl)
    Model ini sudah termasuk vectorizer/pipeline di dalamnya.
    """
    def __init__(self, model_path):
        self.model = None
        self.model_path = model_path
        self.classes = ['negatif', 'positif']  # Mapping index ke label

        self._load_model()

    def _load_model(self):
        try:
            print(f"🔄 Loading Sentiment Model from {self.model_path}...")
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            print("✅ Sentiment Analyzer Loaded Successfully")
            
            # Debug: Print model info
            print(f"ℹ️ Model type: {type(self.model)}")
            
        except Exception as e:
            print(f"❌ Failed to load Sentiment Analyzer: {e}")
            self.model = None

    def predict(self, text):
        """
        Predict sentiment dari text.
        
        Args:
            text: String komentar/review yang akan dianalisis
            
        Returns:
            'positif' atau 'negatif' atau None jika gagal
        """
        if not self.model:
            return None

        try:
            # Scikit-learn model biasanya expect list/array
            # Pipeline sudah include vectorization
            if hasattr(self.model, 'predict'):
                # Model langsung predict
                pred = self.model.predict([text])
                
                # Cek tipe hasil prediksi
                if isinstance(pred[0], str):
                    # Model sudah return label string
                    return pred[0].lower()
                elif isinstance(pred[0], (int, float)):
                    # Model return index/number
                    idx = int(pred[0])
                    if idx < len(self.classes):
                        return self.classes[idx]
                    else:
                        return 'positif' if idx == 1 else 'negatif'
            
            # Jika model punya method khusus
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba([text])
                idx = proba[0].argmax()
                return self.classes[idx] if idx < len(self.classes) else 'unknown'

            return None

        except Exception as e:
            print(f"❌ Prediction Error: {e}")
            return None


# Singleton instance placeholder
analyzer = None

def init_analyzer(base_dir):
    """
    Inisialisasi sentiment analyzer dengan model sentiment_model_sim.pkl
    
    Args:
        base_dir: Base directory dimana model berada
    """
    global analyzer
    model_path = os.path.join(base_dir, 'sentiment_model_sim.pkl')
    
    if os.path.exists(model_path):
        analyzer = SentimentAnalyzer(model_path)
        print(f"🔍 DEBUG: analyzer loaded = {analyzer is not None}, model = {analyzer.model is not None if analyzer else 'N/A'}")
    else:
        print(f"⚠️ Sentiment model not found at: {model_path}")
        print("⚠️ Sentiment analysis will be disabled.")

def predict_sentiment(text):
    """
    Fungsi wrapper untuk prediksi sentiment.
    
    Args:
        text: Text yang akan dianalisis
        
    Returns:
        'positif', 'negatif', atau None
    """
    if analyzer:
        return analyzer.predict(text)
    return None
