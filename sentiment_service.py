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
        self.classes = None  # Akan di-detect dari model

        self._load_model()

    def _load_model(self):
        try:
            print(f"🔄 Loading Sentiment Model from {self.model_path}...")
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            print("✅ Sentiment Analyzer Loaded Successfully")
            
            # Debug: Print model info
            print(f"ℹ️ Model type: {type(self.model)}")
            
            # =============================================
            # AUTO-DETECT CLASS MAPPING DARI MODEL
            # =============================================
            # Scikit-learn menyimpan label classes di atribut 'classes_'
            # Ini penting agar urutan mapping sesuai dengan saat training!
            
            self._detect_classes()
            
        except Exception as e:
            print(f"❌ Failed to load Sentiment Analyzer: {e}")
            self.model = None

    def _detect_classes(self):
        """
        Mendeteksi urutan class dari model.
        Scikit-learn classifier menyimpan di model.classes_
        Pipeline menyimpan di step terakhir (classifier).
        """
        if not self.model:
            return
            
        classes_found = None
        
        # Cek 1: Model langsung punya classes_
        if hasattr(self.model, 'classes_'):
            classes_found = self.model.classes_
            print(f"✅ Classes detected from model.classes_: {classes_found}")
        
        # Cek 2: Model adalah Pipeline, cek step terakhir
        elif hasattr(self.model, 'named_steps'):
            # Pipeline object
            for step_name in reversed(list(self.model.named_steps.keys())):
                step = self.model.named_steps[step_name]
                if hasattr(step, 'classes_'):
                    classes_found = step.classes_
                    print(f"✅ Classes detected from pipeline step '{step_name}': {classes_found}")
                    break
        
        # Cek 3: Model adalah Pipeline (list of tuples)
        elif hasattr(self.model, 'steps'):
            for step_name, step in reversed(self.model.steps):
                if hasattr(step, 'classes_'):
                    classes_found = step.classes_
                    print(f"✅ Classes detected from pipeline step '{step_name}': {classes_found}")
                    break
        
        # Set classes berdasarkan hasil deteksi
        if classes_found is not None:
            # Convert ke list of strings (lowercase)
            self.classes = [str(c).lower() for c in classes_found]
            print(f"📋 Final class mapping: {self.classes}")
            print(f"   Index 0 = '{self.classes[0]}'")
            print(f"   Index 1 = '{self.classes[1]}'")
        else:
            # Fallback: Gunakan default (PERINGATAN!)
            print("⚠️ WARNING: Could not detect classes from model!")
            print("⚠️ Using default mapping: [0='negatif', 1='positif']")
            print("⚠️ PASTIKAN ini sesuai dengan urutan saat training!")
            self.classes = ['negatif', 'positif']

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
                    if self.classes and idx < len(self.classes):
                        return self.classes[idx]
                    else:
                        # Ultimate fallback
                        return 'positif' if idx == 1 else 'negatif'
            
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
