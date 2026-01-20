import pytest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os

# Ensure we can import from backend_sim
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from sentiment_service import SentimentAnalyzer, predict_sentiment, init_analyzer

class TestSentimentAnalyzer:
    
    @patch('sentiment_service.joblib')
    def test_load_model_joblib_success(self, mock_joblib):
        """Test loading model with joblib successfully"""
        # Setup mock
        mock_model = MagicMock()
        mock_model.classes_ = ['negatif', 'positif']
        mock_joblib.load.return_value = mock_model
        
        # Initialize analyzer
        with patch('sentiment_service.HAS_JOBLIB', True):
            analyzer = SentimentAnalyzer('fake_model.pkl')
            
            assert analyzer.model == mock_model
            assert analyzer.classes == ['negatif', 'positif']
            mock_joblib.load.assert_called_once_with('fake_model.pkl')

    @patch('sentiment_service.pickle')
    def test_load_model_pickle_fallback(self, mock_pickle):
        """Test fallback to pickle when joblib is missing or fails"""
        # Setup mock
        mock_model = MagicMock()
        mock_model.classes_ = ['negatif', 'positif']
        mock_pickle.load.return_value = mock_model
        
        # Test 1: HAS_JOBLIB is False
        with patch('sentiment_service.HAS_JOBLIB', False):
            with patch('builtins.open', mock_open(read_data=b'data')):
                analyzer = SentimentAnalyzer('fake_model.pkl')
                
                assert analyzer.model == mock_model
                
        # Test 2: HAS_JOBLIB is True but fails
        with patch('sentiment_service.HAS_JOBLIB', True):
            with patch('sentiment_service.joblib.load', side_effect=Exception("Joblib fail")):
                with patch('builtins.open', mock_open(read_data=b'data')):
                    analyzer = SentimentAnalyzer('fake_model.pkl')
                    assert analyzer.model == mock_model

    @patch('sentiment_service.SentimentAnalyzer._load_model')
    def test_detect_classes_pipeline(self, mock_load):
        """Test detecting classes from a Pipeline object"""
        # Create pipeline-like mock
        mock_pipeline = MagicMock()
        # MagicMock creates all attributes by default, so we must delete classes_
        # to ensure it falls through to the pipeline check
        del mock_pipeline.classes_ 
        
        # Mock steps dict
        mock_step = MagicMock()
        mock_step.classes_ = ['bad', 'good']
        mock_pipeline.named_steps = {'classifier': mock_step}
        
        analyzer = SentimentAnalyzer('dummy')
        analyzer.model = mock_pipeline
        analyzer._detect_classes()
        
        assert analyzer.classes == ['bad', 'good']

    def test_detect_classes_fallback(self):
        """Test fallback classes when detection fails"""
        mock_model = MagicMock()
        # Ensure no classes_ attribute
        del mock_model.classes_ 
        
        analyzer = SentimentAnalyzer('dummy')
        analyzer.model = mock_model
        analyzer._detect_classes()
        
        assert analyzer.classes == ['negatif', 'positif']

    def test_predict_string_label(self):
        """Test prediction that returns a string label"""
        mock_model = MagicMock()
        mock_model.predict.return_value = ['Positif'] # Capitalized
        
        analyzer = SentimentAnalyzer('dummy')
        analyzer.model = mock_model
        analyzer.classes = ['negatif', 'positif']
        
        result = analyzer.predict("Great app")
        assert result == 'positif' # Should be lowercased

    def test_predict_index_label(self):
        """Test prediction that returns an index"""
        mock_model = MagicMock()
        mock_model.predict.return_value = [1] 
        
        analyzer = SentimentAnalyzer('dummy')
        analyzer.model = mock_model
        analyzer.classes = ['negatif', 'positif']
        
        result = analyzer.predict("Great app")
        assert result == 'positif'
        
        # Test index 0
        mock_model.predict.return_value = [0]
        result = analyzer.predict("Bad app")
        assert result == 'negatif'

    def test_predict_error_handling(self):
        """Test error handling during prediction"""
        mock_model = MagicMock()
        mock_model.predict.side_effect = Exception("Prediction failed")
        
        analyzer = SentimentAnalyzer('dummy')
        analyzer.model = mock_model
        
        result = analyzer.predict("Crash it")
        assert result is None

    def test_predict_no_model(self):
        """Test prediction when model is not loaded"""
        analyzer = SentimentAnalyzer('dummy')
        # intentionally init failed
        analyzer.model = None
        
        result = analyzer.predict("test")
        assert result is None

    @patch('sentiment_service.analyzer')
    def test_global_predict_function(self, mock_analyzer):
        """Test the global wrapper function"""
        mock_analyzer.predict.return_value = 'positif'
        
        # We need to patch the module-level variable in the module itself
        with patch('sentiment_service.analyzer', mock_analyzer):
            result = predict_sentiment("text")
            assert result == 'positif'
            mock_analyzer.predict.assert_called_with("text")

    def test_init_analyzer_global(self):
        """Test global initialization function"""
        with patch('os.path.exists', return_value=True):
             with patch('sentiment_service.SentimentAnalyzer') as MockAnalyzer:
                 init_analyzer('/tmp')
                 MockAnalyzer.assert_called_once()

    def test_init_analyzer_not_found(self):
        """Test global initialization function when file missing"""
        with patch('os.path.exists', return_value=False):
             with patch('sentiment_service.SentimentAnalyzer') as MockAnalyzer:
                 init_analyzer('/tmp')
                 MockAnalyzer.assert_not_called()

    def test_predict_index_fallback(self):
        """Test prediction index fallback when classes not detected"""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0]
        
        analyzer = SentimentAnalyzer('dummy')
        analyzer.model = mock_model
        analyzer.classes = None # Force no classes
        
        # Should correspond to 0 -> negative (default logic: 1=positif else negatif)
        result = analyzer.predict("test")
        assert result == 'negatif'
        
        mock_model.predict.return_value = [1]
        result = analyzer.predict("test")
        assert result == 'positif'

    def test_detect_classes_list_steps(self):
        """Test detecting classes from pipeline with 'steps' list (not named_steps)"""
        mock_pipeline = MagicMock()
        del mock_pipeline.classes_ # ensure fallthrough
        del mock_pipeline.named_steps # ensure fallthrough
        
        mock_step = MagicMock()
        mock_step.classes_ = ['one', 'two']
        # steps is list of (name, step) tuples
        mock_pipeline.steps = [('classifier', mock_step)]
        
        analyzer = SentimentAnalyzer('dummy')
        analyzer.model = mock_pipeline
        analyzer._detect_classes()
        
        assert analyzer.classes == ['one', 'two']

    @patch('sentiment_service.pickle')
    def test_load_pickle_encodings(self, mock_pickle):
        """Test various pickle encoding fallbacks"""
        mock_model = MagicMock()
        
        # Case 1: Standard fails, latin1 succeeds
        # side_effect: first call raises, second returns mock_model
        mock_pickle.load.side_effect = [Exception("Fail std"), mock_model]
        
        with patch('sentiment_service.HAS_JOBLIB', False):
            with patch('builtins.open', mock_open(read_data=b'data')):
                analyzer = SentimentAnalyzer('path')
                assert analyzer.model == mock_model
                assert mock_pickle.load.call_count == 2
                
        # Case 2: Standard fails, latin1 fails, bytes succeeds
        mock_pickle.reset_mock()
        mock_pickle.load.side_effect = [Exception("Fail std"), Exception("Fail latin1"), mock_model]
        
        with patch('sentiment_service.HAS_JOBLIB', False):
            with patch('builtins.open', mock_open(read_data=b'data')):
                analyzer = SentimentAnalyzer('path')
                assert analyzer.model == mock_model
                assert mock_pickle.load.call_count == 3

    def test_detect_classes_no_model(self):
        """Test detect classes returns early if no model"""
        analyzer = SentimentAnalyzer('dummy')
        analyzer.model = None
        analyzer._detect_classes()
        assert analyzer.classes is None

    @patch('sentiment_service.SentimentAnalyzer._load_with_pickle')
    def test_load_model_exception_handling(self, mock_pickle_load):
        """Test exception handling in _load_model"""
        # Force exception during load
        mock_pickle_load.side_effect = Exception("Crash")
        
        with patch('sentiment_service.HAS_JOBLIB', False):
             analyzer = SentimentAnalyzer('dummy')
             assert analyzer.model is None

    def test_predict_model_no_predict_method(self):
        """Test predict when model object has no predict method"""
        mock_model = MagicMock()
        del mock_model.predict # Ensure no predict method
        
        analyzer = SentimentAnalyzer('dummy')
        analyzer.model = mock_model
        
        result = analyzer.predict("test")
        assert result is None

    def test_global_predict_no_analyzer(self):
        """Test global predict function when analyzer is not initialized"""
        # We need to ensure the global 'analyzer' is None
        with patch('sentiment_service.analyzer', None):
            result = predict_sentiment("test")
            assert result is None


