import pytest
from unittest.mock import MagicMock
import sys
import os

# Ensure we can import from backend_sim
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from utils.ai_helper import analyze_severity

class TestAIHelper:
    
    def test_analyze_severity_no_results(self):
        """Test with empty results"""
        results = []
        status, count = analyze_severity(results, 100, 100)
        assert status == "AMAN"
        assert count == 0

    def test_analyze_severity_no_boxes(self):
        """Test with valid header but no boxes found"""
        mock_result = MagicMock()
        mock_result.boxes = []
        results = [mock_result]
        
        status, count = analyze_severity(results, 100, 100)
        assert status == "AMAN"
        assert count == 0

    def test_analyze_severity_low_confidence_filtered(self):
        """Test that low confidence boxes are filtered out"""
        mock_box = MagicMock()
        mock_box.conf = [0.1] # Less than 0.4
        
        mock_result = MagicMock()
        mock_result.boxes = [mock_box]
        results = [mock_result]
        
        status, count = analyze_severity(results, 100, 100)
        assert status == "AMAN"
        assert count == 0

    def test_analyze_severity_serious_area(self):
        """Test that large area triggers SERIUS status"""
        mock_box = MagicMock()
        mock_box.conf = [0.9]
        # xywh: [x, y, w, h]
        # Image area 100x100 = 10000
        # Box area need > 3.5% = 350
        # Let's make box 20x20 = 400
        mock_box.xywh = [[50, 50, 20, 20]] 
        
        mock_result = MagicMock()
        mock_result.boxes = [mock_box]
        results = [mock_result]
        
        status, count = analyze_severity(results, 100, 100)
        assert status == "SERIUS"
        assert count == 1

    def test_analyze_severity_many_potholes(self):
        """Test that many small potholes trigger SERIUS status"""
        # 5 small potholes
        boxes = []
        for _ in range(5):
            mock_box = MagicMock()
            mock_box.conf = [0.9]
            # Small area: 10x10 = 100 (1%)
            mock_box.xywh = [[50, 50, 10, 10]]
            boxes.append(mock_box)
            
        mock_result = MagicMock()
        mock_result.boxes = boxes
        results = [mock_result]
        
        status, count = analyze_severity(results, 100, 100)
        assert status == "SERIUS"
        assert count == 5

    def test_analyze_severity_not_serious(self):
        """Test small count and small area -> TIDAK_SERIUS"""
        mock_box = MagicMock()
        mock_box.conf = [0.9]
        # Small area: 10x10 = 100 (1%)
        mock_box.xywh = [[50, 50, 10, 10]]
        
        mock_result = MagicMock()
        mock_result.boxes = [mock_box]
        results = [mock_result]
        
        status, count = analyze_severity(results, 100, 100)
        assert status == "TIDAK_SERIUS"
        assert count == 1
