# SmartInfra Backend - Testing Documentation

## 📋 Overview
Comprehensive testing suite for SmartInfra Backend API including:
- ✅ Unit Tests
- ✅ API Tests  
- ✅ Integration Tests
- ✅ Load/Performance Tests

## 🚀 Setup

### 1. Install Testing Dependencies
```bash
pip install -r requirements-test.txt
```

### 2. Prepare Test Database
Tests use SQLite in-memory database, no setup needed.

## 🧪 Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test Types

**Unit Tests Only:**
```bash
pytest -m unit
```

**API Tests Only:**
```bash
pytest -m api
```

**Integration Tests Only:**
```bash
pytest -m integration
```

**Auth Tests Only:**
```bash
pytest -m auth
```

**Admin Tests Only:**
```bash
pytest -m admin
```

**Posts Tests Only:**
```bash
pytest -m posts
```

### Run Specific Test File
```bash
pytest tests/unit/test_models_user.py
pytest tests/api/test_auth_api.py
```

### Run with Coverage Report
```bash
pytest --cov=. --cov-report=html
```

Then open `htmlcov/index.html` in browser to see detailed coverage.

### Run with Verbose Output
```bash
pytest -v
```

### Run Specific Test Function
```bash
pytest tests/unit/test_models_user.py::TestUserModel::test_create_user
```

## 📊 Load Testing with Locust

### 1. Start Backend Server
```bash
python app.py
```

### 2. Run Locust
```bash
locust -f tests/load/locustfile.py --host=http://localhost:5000
```

### 3. Open Locust Web UI
Open browser: http://localhost:8089

### 4. Configure Test
- **Number of users**: 100 (adjust based on your needs)
- **Spawn rate**: 10 users/second
- Click "Start Swarming"

### 5. Monitor Results
Locust will show:
- Requests per second (RPS)
- Response times (min, max, avg, median)
- Failure rate
- Number of failures

## 📈 Test Coverage Goals
- **Overall Coverage**: >80%
- **Models**: >90%
- **Routes**: >75%
- **Utils**: >70%

## 🧾 Test Structure

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── unit/                    # Unit tests
│   ├── test_models_user.py
│   └── test_models_post.py
├── api/                     # API endpoint tests
│   ├── test_auth_api.py
│   ├── test_posts_api.py
│   ├── test_admin_api.py
│   └── test_reviews_api.py
├── integration/             # Integration tests
│   └── test_user_flows.py
└── load/                    # Load/performance tests
    └── locustfile.py
```

## 📝 Writing New Tests

### 1. Use Fixtures from conftest.py
```python
def test_example(client, sample_user, auth_headers):
    # Your test here
    pass
```

### 2. Add Test Markers
```python
@pytest.mark.unit
@pytest.mark.auth
def test_example():
    # Your test here
    pass
```

### 3. Follow Naming Convention
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

## 🔍 Continuous Integration (CI)

### GitHub Actions Example
Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run tests
      run: pytest --cov=. --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## 🎯 Best Practices

1. **Keep tests independent** - Each test should be able to run alone
2. **Use fixtures** - Reuse common test data and setup
3. **Test edge cases** - Not just happy paths
4. **Mock external services** - Don't rely on external APIs
5. **Keep tests fast** - Use in-memory database
6. **Write descriptive test names** - Make it clear what's being tested
7. **One assertion per test** - When possible

## 🐛 Troubleshooting

### Tests Fail Due to Database
- Ensure using SQLite in-memory database in TestConfig
- Check db.create_all() is called in fixtures

### Import Errors
- Make sure you're in the backend_sim directory
- Check Python path is set correctly

### Slow Tests
- Use markers to skip slow tests: `pytest -m "not slow"`
- Check if external services are being called

## 📚 Additional Resources
- [Pytest Documentation](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/en/2.3.x/testing/)
- [Locust Documentation](https://docs.locust.io/)
