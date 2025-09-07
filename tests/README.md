# Tests

This directory contains test scripts for LocalCaption.

## Test Files

- **`test_app.py`** - Main test suite for all components
- **`test_asr.py`** - ASR engine specific tests
- **`test_windows.py`** - Windows-specific debugging tests

## Running Tests

```bash
# Run all tests
python tests/test_app.py

# Run ASR tests only
python tests/test_asr.py

# Run Windows debug tests
python tests/test_windows.py
```

## Test Coverage

- ✅ Module imports
- ✅ Audio capture functionality
- ✅ ASR engine initialization
- ✅ Export utilities
- ✅ Performance monitoring
- ✅ Windows-specific components
