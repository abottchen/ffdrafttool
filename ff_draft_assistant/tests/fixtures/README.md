# Test Fixtures

This directory contains real data snapshots used for integration testing.

## Purpose

Using real data fixtures ensures our tests work with actual data structures rather than just mock data. This approach helps catch bugs like field name mismatches that could pass unit tests but fail in production.

## Files

- `real_draft_data_snapshot.json` - A snapshot of actual draft data from Google Sheets
- `__init__.py` - Utilities for loading and working with fixture data

## Usage

```python
from tests.fixtures import load_real_draft_data, get_sample_drafted_players

# Load full real draft data
real_data = load_real_draft_data()

# Get sample drafted players for testing
drafted_players = get_sample_drafted_players(count=5)

# Get a sample draft state with real structure
draft_state = get_real_draft_state_sample()
```

## Benefits of Real Data Fixtures

1. **Field Name Accuracy**: Ensures tests use the same field names as production data
2. **Data Structure Validation**: Verifies code works with actual nested structures
3. **Edge Case Discovery**: Real data often contains edge cases not thought of in mock data
4. **Integration Confidence**: Provides confidence that code will work with real APIs
5. **Regression Prevention**: Catches breaking changes when data structure evolves

## Best Practices

1. **Keep Fixtures Fresh**: Update snapshots periodically to reflect current data
2. **Sanitize Sensitive Data**: Remove any personal or sensitive information
3. **Document Structure Changes**: Update tests when data structure changes
4. **Mix Mock and Real**: Use real fixtures for integration tests, mocks for unit tests
5. **Version Snapshots**: Consider dating snapshots or keeping multiple versions

## Updating Fixtures

To capture a new snapshot of real data:

```python
import asyncio
import json
from src.tools.mcp_tools import read_draft_progress

async def update_snapshot():
    result = await read_draft_progress(
        sheet_id='your_sheet_id',
        force_refresh=True
    )
    
    with open('tests/fixtures/real_draft_data_snapshot.json', 'w') as f:
        json.dump(result, f, indent=2)

asyncio.run(update_snapshot())
```

## Testing Strategy

- **Unit Tests**: Use focused mock data for testing specific functions
- **Integration Tests**: Use real data fixtures to test component interactions
- **Contract Tests**: Verify that real data matches expected schema/structure