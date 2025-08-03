# Fantasy Football Draft Assistant MCP Server

This is the source code for the Fantasy Football Draft Assistant MCP server.

## Development Commands

Run tests:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=src --cov-report=term-missing
```

Lint code:
```bash
ruff check src/ tests/
```

Format code:
```bash
black src/ tests/
```

Start MCP server:
```bash
python run_server.py
```

## Project Structure

- `src/` - Source code for the MCP server
- `tests/` - Test suite organized by component
- `config.json.example` - Configuration template
- `run_server.py` - Server entry point

## Key Files

- `src/server.py` - Main MCP server implementation
- `src/tools/mcp_tools.py` - Core MCP tool implementations
- `src/config.py` - Configuration management
- `src/services/` - Business logic services
- `src/models/` - Data models

## Development Guidelines

- Follow existing code patterns and conventions
- Add tests for new functionality in the appropriate test subdirectory
- Update configuration in `config.json`, not hardcoded values
- Use the caching system for external API calls
- Keep MCP responses under token limits for performance

## Testing

Tests are organized to mirror the source structure:
- `tests/models/` - Data model tests
- `tests/services/` - Service layer tests  
- `tests/tools/` - MCP tool tests

Run specific test groups:
```bash
pytest tests/models/
pytest tests/services/
pytest tests/tools/
```