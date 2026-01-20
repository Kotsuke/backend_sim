import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure we can import from backend_sim
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from routes.admin import check_and_migrate_db

class TestDBMigration:
    
    @patch('routes.admin.db')
    @patch('sqlalchemy.inspect')
    def test_migrate_created_at(self, mock_inspect, mock_db):
        """Test adding created_at column to users"""
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector
        mock_inspector.get_table_names.return_value = ['users']
        
        # 'created_at' is missing
        mock_inspector.get_columns.return_value = [{'name': 'id'}, {'name': 'username'}]
        
        mock_app = MagicMock()
        with mock_app.app_context():
             check_and_migrate_db(mock_app)
             
        # Check that execute was called with ALERT TABLE
        # Note: db.session.execute is called
        call_args_list = mock_db.session.execute.call_args_list
        found = False
        for call_args in call_args_list:
            sql = str(call_args[0][0])
            if "ALTER TABLE users ADD COLUMN created_at" in sql:
                found = True
                break
        assert found

    @patch('routes.admin.db')
    @patch('sqlalchemy.inspect')
    def test_migrate_sentiment(self, mock_inspect, mock_db):
        """Test adding sentiment column to reviews"""
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector
        mock_inspector.get_table_names.return_value = ['users', 'reviews']
        
        # users ok
        mock_inspector.get_columns.side_effect = [
            [{'name': 'created_at'}], # users
            [{'name': 'id'}, {'name': 'rating'}] # reviews (missing sentiment)
        ]
        
        mock_app = MagicMock()
        with mock_app.app_context():
             check_and_migrate_db(mock_app)
             
        # Check that execute was called
        call_args_list = mock_db.session.execute.call_args_list
        found = False
        for call_args in call_args_list:
            sql = str(call_args[0][0])
            if "ALTER TABLE reviews ADD COLUMN sentiment" in sql:
                found = True
                break
        assert found

    @patch('routes.admin.db')
    @patch('sqlalchemy.inspect')
    def test_migrate_posts_columns(self, mock_inspect, mock_db):
        """Test adding columns to posts"""
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector
        mock_inspector.get_table_names.return_value = ['users', 'reviews', 'posts']
        
        # users, reviews ok
        # posts missing status, province, city, district
        mock_inspector.get_columns.side_effect = [
            [{'name': 'created_at'}], # users
            [{'name': 'sentiment'}], # reviews
            [{'name': 'id'}] # posts (missing everything)
        ]
        
        mock_app = MagicMock()
        with mock_app.app_context():
             check_and_migrate_db(mock_app)
             
        # Check that execute was called for all
        executed_sqls = []
        for call_args in mock_db.session.execute.call_args_list:
            executed_sqls.append(str(call_args[0][0]))
            
        assert any("ADD COLUMN status" in sql for sql in executed_sqls)
        assert any("ADD COLUMN province" in sql for sql in executed_sqls)
        assert any("ADD COLUMN city" in sql for sql in executed_sqls)
        assert any("ADD COLUMN district" in sql for sql in executed_sqls)

    @patch('routes.admin.db')
    @patch('sqlalchemy.inspect')
    def test_migrate_exception(self, mock_inspect, mock_db):
        """Test exception handling during migration"""
        mock_inspector = MagicMock()
        mock_inspect.return_value = mock_inspector
        mock_inspector.get_table_names.return_value = ['users']
        mock_inspector.get_columns.return_value = [{'name': 'id'}]
        
        # Force exception
        mock_db.session.execute.side_effect = Exception("DB Error")
        
        mock_app = MagicMock()
        # Should not raise
        with mock_app.app_context():
             check_and_migrate_db(mock_app)
