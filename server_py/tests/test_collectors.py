import pytest
from unittest.mock import MagicMock
import pandas as pd
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.calendar_collector import CalendarCollector

class TestCalendarCollector:
    def setup_method(self):
        self.collector = CalendarCollector(data_dir="test_data")

    def test_parse_importance(self):
        # Test Chinese
        assert self.collector._parse_importance("高") == 3
        assert self.collector._parse_importance("中") == 2
        assert self.collector._parse_importance("低") == 1
        
        # Test English
        assert self.collector._parse_importance("High Importance") == 3
        assert self.collector._parse_importance("Medium") == 2
        assert self.collector._parse_importance("Low") == 1
        
        # Test Stars
        assert self.collector._parse_importance("⭐⭐⭐") == 3
        assert self.collector._parse_importance("★★") == 2
        
        # Test Numbers
        assert self.collector._parse_importance(3) == 3
        assert self.collector._parse_importance("3") == 3
        
        # Test None/Empty
        assert self.collector._parse_importance(None) == 0
        assert self.collector._parse_importance("") == 0

    def test_process_df_baidu(self):
        # Mock DataFrame for Baidu
        data = {
            '时间': ['10:00', '11:00'],
            '地区': ['中国', '美国'],
            '事件': ['GDP公布', 'CPI公布'],
            '重要性': ['高', '中'],
            '前值': ['5.0%', '2.0%'],
            '预测值': ['5.2%', '2.1%'],
            '公布值': ['5.3%', ''],
        }
        df = pd.DataFrame(data)
        
        events = self.collector._process_df(df, "Baidu")
        
        assert len(events) == 2
        assert events[0]['importance'] == 3
        assert events[0]['event'] == 'GDP公布'
        assert events[1]['importance'] == 2
        assert events[1]['country'] == '美国'

    def test_process_df_english_columns(self):
        # Mock DataFrame with English columns (e.g. from Jin10 sometimes)
        data = {
            'time': ['10:00'],
            'country': ['USA'],
            'event': ['Non-Farm Payrolls'],
            'importance': ['High'],
            'previous': ['100K'],
            'consensus': ['150K'],
            'actual': ['160K'],
        }
        df = pd.DataFrame(data)
        
        events = self.collector._process_df(df, "EnglishSource")
        
        assert len(events) == 1
        assert events[0]['importance'] == 3
        assert events[0]['event'] == 'Non-Farm Payrolls'
