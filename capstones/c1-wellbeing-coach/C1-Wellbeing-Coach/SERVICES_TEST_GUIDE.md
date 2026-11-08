# Service-Specific Test Suite Guide

## Overview

Each service has its own dedicated test file for easier segregation, maintenance, and future scaling. This modular approach makes it simple to:
- Test services in isolation
- Add new test cases without cluttering other files
- Understand service behavior at a glance
- Scale testing infrastructure independently per service

## Test File Organization

```
tests/unit/
├── test_models.py                   # Data models validation
└── services/                        # Service-specific tests
    ├── test_emotion_service.py      # 13 tests - Emotion detection
    ├── test_feedback_service.py     # 20 tests - Feedback handling
    ├── test_llm_service.py          # 31 tests - LLM API calls
    ├── test_memory_service.py       # 13 tests - Database (Memory)
    └── test_recommendation_service.py # 17 tests - Recommendations
```

**Total: 104 unit tests** covering all service layers

## Service Test Classes

### 1. **test_emotion_service.py** - EmotionService Tests
**Purpose**: Test emotion detection functionality

**Test Class**: `TestEmotionService` (13 tests)

**Key Test Cases**:
- ✅ Service initialization
- ✅ Detect emotion with mock data
- ✅ Empty text handling
- ✅ Long text handling
- ✅ Result field validation (emotion, confidence, intensity)
- ✅ Confidence range validation (0-1)
- ✅ Special characters in text
- ✅ Numeric content handling
- ✅ Multiple calls consistency
- ✅ LLM fallback testing
- ✅ Unicode text support
- ✅ Multiline text support
- ✅ Different texts with emotions

**Methods Tested**:
```python
def detect_emotion(text: str) -> dict
```

**Run Tests**:
```bash
pytest tests/unit/test_emotion_service.py -v
```

---

### 2. **test_feedback_service.py** - FeedBackService Tests
**Purpose**: Test feedback storage and retrieval functionality

**Test Class**: `TestFeedBackService` (20 tests)

**Key Test Cases**:
- ✅ Service initialization
- ✅ Store feedback (rating + comment)
- ✅ Store feedback (rating only)
- ✅ Store feedback (no comment)
- ✅ Valid rating range (1-5)
- ✅ Different interaction IDs
- ✅ Long comment handling
- ✅ Special characters in comment
- ✅ Empty comment handling
- ✅ Unicode comment support
- ✅ Get empty history
- ✅ Get history returns list
- ✅ Store and get sequence
- ✅ Numeric string IDs
- ✅ Consistent results
- ✅ Edge case ratings (0, 10+)
- ✅ Multiline comments
- ✅ Various interaction ID formats

**Methods Tested**:
```python
def store_feeback(interaction_id: str, rating: int, comment: str = None)
def get_history(interaction_id: str)
```

**Run Tests**:
```bash
pytest tests/unit/test_feedback_service.py -v
```

---

### 3. **test_recommendation_service.py** - RecommendationService Tests
**Purpose**: Test recommendation generation for different emotions

**Test Class**: `TestRecommendationService` (17 tests)

**Key Test Cases**:
- ✅ Service initialization
- ✅ Generate with mock data
- ✅ Result structure validation
- ✅ Different emotion types
- ✅ Minimal emotion data
- ✅ Missing emotion fields
- ✅ High intensity emotions
- ✅ Low confidence emotions
- ✅ Activity non-empty validation
- ✅ Message non-empty validation
- ✅ Multiple calls (consistency)
- ✅ Extra emotion fields (ignored)
- ✅ Input not modified
- ✅ Special emotion names
- ✅ LLM call verification
- ✅ Edge cases
- ✅ Field preservation

**Methods Tested**:
```python
def generate_recommendation(emotion_result: dict) -> dict
```

**Run Tests**:
```bash
pytest tests/unit/test_recommendation_service.py -v
```

---

### 4. **test_llm_service.py** - LLMService Tests
**Purpose**: Test LLM API interactions (Gemini and Gemma)

**Test Classes**: 
- `TestLLMService` (31 tests)

**Key Test Cases**:

**Gemini LLM Tests** (10 tests):
- ✅ Simple prompt
- ✅ Empty prompt
- ✅ Long prompt
- ✅ Special characters
- ✅ Unicode support
- ✅ Returns string
- ✅ Non-empty response
- ✅ Multiple calls
- ✅ Multiline prompt
- ✅ JSON-formatted prompt

**Gemma LLM Tests** (10 tests):
- ✅ Simple prompt
- ✅ Empty prompt
- ✅ Long prompt
- ✅ Special characters
- ✅ Unicode support
- ✅ Returns string
- ✅ Non-empty response
- ✅ Multiple calls
- ✅ Multiline prompt
- ✅ JSON-formatted prompt

**Comparative Tests** (2 tests):
- ✅ Both return strings
- ✅ Different prompts

**Edge Cases** (9 tests):
- ✅ Very long prompts (both)
- ✅ Whitespace-only prompts (both)
- ✅ Input preservation (both)
- ✅ Numbers and symbols (both)
- ✅ Consistency checks

**Functions Tested**:
```python
def call_gemini_llm(prompt: str) -> str
def call_gemma_llm(prompt: str) -> str
```

**Run Tests**:
```bash
pytest tests/unit/test_llm_service.py -v
pytest tests/unit/test_llm_service.py::TestLLMService::test_call_gemini_llm_with_simple_prompt -v
```

---

## Test Coverage Summary

| Service | Test File | Tests | Coverage Areas |
|---------|-----------|-------|-----------------|
| EmotionService | test_emotion_service.py | 13 | Emotion detection, confidence validation, text handling |
| FeedBackService | test_feedback_service.py | 20 | Storage, retrieval, ratings, comments, edge cases |
| RecommendationService | test_recommendation_service.py | 17 | Recommendation generation, emotion processing, LLM calls |
| LLMService | test_llm_service.py | 31 | Gemini API, Gemma API, prompt handling, edge cases |
| MemoryService | test_services.py | 13 | Database ops, feedback updates, history retrieval |
| Models | test_models.py | 10 | Data validation, optional fields, type checking |

**Total: 104 unit tests**

## Running Tests

### Run all tests
```bash
pytest tests/unit
```

### Run specific service tests
```bash
# Emotion Service
pytest tests/unit/services/test_emotion_service.py -v

# Feedback Service
pytest tests/unit/services/test_feedback_service.py -v

# Recommendation Service
pytest tests/unit/services/test_recommendation_service.py -v

# Memory Service (renamed from test_services)
pytest tests/unit/services/test_memory_service.py -v

# LLM Service
pytest tests/unit/services/test_llm_service.py -v
```

### Run specific test class
```bash
pytest tests/unit/services/test_emotion_service.py::TestEmotionService -v
```

### Run specific test method
```bash
pytest tests/unit/services/test_emotion_service.py::TestEmotionService::test_detect_emotion_with_mock_data -v
```

### Run with coverage
```bash
pytest tests/unit --cov=app.services --cov-report=html
```

## Adding New Test Cases

Each test file follows this structure:

```python
"""Unit tests for [ServiceName]."""

import pytest
from app.services.[service_module] import [ServiceClass]


class Test[ServiceName]:
    """Tests for [ServiceName] - [description]."""
    
    def test_service_initialization(self):
        """Test service initializes successfully."""
        service = [ServiceClass]()
        assert service is not None
    
    def test_feature_basic(self):
        """Test basic feature."""
        # Arrange
        service = [ServiceClass]()
        
        # Act
        result = service.method_name(args)
        
        # Assert
        assert result is not None
    
    # More tests...
```

## Best Practices

1. **One Service = One Test File**
   - Each service gets its own dedicated test file
   - Easier to navigate and maintain
   - Clear separation of concerns

2. **Test Naming Convention**
   - File: `test_[service_name].py`
   - Class: `Test[ServiceName]`
   - Method: `test_[feature]_[scenario]`

3. **Test Organization**
   - Arrange-Act-Assert pattern
   - Clear docstrings explaining what's tested
   - Group related tests

4. **Input Validation Tests**
   - Empty inputs
   - Invalid types
   - Edge cases (0, negatives, very large)
   - Special characters, unicode
   - Null/None values

5. **Behavior Tests**
   - Success paths
   - Error handling
   - Multiple calls consistency
   - State preservation

6. **Mock Data**
   - Use mocks for external dependencies (LLM APIs)
   - Test with both mock and real scenarios
   - Patch environment variables for testing

## Scaling Notes

When adding new services:

1. **Create new test file**: `tests/unit/services/test_[service_name].py`
2. **Create test class**: `Test[ServiceName]`
3. **Add test methods** for each public method
4. **Consider edge cases**: Empty, null, large, special chars
5. **Add fixtures** if needed in `conftest.py`
6. **Update this guide** with new service information

## Example: Adding Tests for a New Service

```python
# tests/unit/services/test_new_service.py
"""Unit tests for NewService."""

import pytest
from app.services.new_service import NewService


class TestNewService:
    """Tests for NewService - [description]."""
    
    def test_initialization(self):
        """Test NewService initializes."""
        service = NewService()
        assert service is not None
    
    def test_main_functionality(self):
        """Test main functionality."""
        service = NewService()
        result = service.do_something("input")
        assert result is not None
    
    # Add more tests...
```

Then run: `pytest tests/unit/services/test_new_service.py -v`

## Updated Folder Structure

The hierarchical folder structure keeps service tests organized:

```
tests/unit/
├── __init__.py
├── test_models.py                   # Data models validation (10 tests)
├── services/                        # Service-specific tests
│   ├── __init__.py
│   ├── test_emotion_service.py      # 13 tests - Emotion detection
│   ├── test_feedback_service.py     # 20 tests - Feedback handling
│   ├── test_llm_service.py          # 31 tests - LLM API calls
│   ├── test_memory_service.py       # 13 tests - Database operations (renamed)
│   └── test_recommendation_service.py # 17 tests - Recommendations
```

This hierarchical parent/child structure makes it easy to test, maintain, and scale each service independently!
