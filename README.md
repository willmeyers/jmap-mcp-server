# JMAP-MCP Server

A Python-based server that bridges the Model Context Protocol (MCP) with JMAP (JSON Mail Access Protocol), enabling basic email operations through MCP clients.

I built this for personal use, but others are welcome to try it out.

## Setup

*Ensure you have [uv](https://github.com/astral-sh/uv) and a valid API token for your JMAP server.*

### 1. Setup the Repo

Clone the repo and run

```bash
uv pip install pyproject.toml
```

### 2. Add the MCP server config to your client.

```json
{
	"mcpServers": {
		"emails": {
			"env": {
				"JMAP_API_TOKEN": "your-api-token"
			},
			"command": "uv",
			"args": [
				"--directory",
				"/absolute/path/to/.../jmap-mcp",
				"uv",
				"run",
				"jmap-mcp-server"
			]
		}
	}
}
```

## Debugging

Errors happen. You can configure your MCP to write to a debug log to help resolve issues.

```json
{
	"mcpServers": {
		"emails": {
			"env": {
				"JMAP_API_TOKEN": "your-api-token",
				"LOG_LEVEL": "DEBUG",
				"LOG_FILE": "/path/to/log/jmap-mcp-debug.log"
			},
			"command": "uv",
			"args": [
				"--directory",
				"/absolute/path/to/.../jmap-mcp",
				"uv",
				"run",
				"jmap-mcp-server",
			]
		}
	}
}
```

## Testing

The project includes tests with support for both unit tests and integration tests.

### Unit Tests
Run unit tests that use mocked responses:
```bash
# Using pytest directly
pytest tests/ -m "not integration"

# Using the test runner script
python run_tests.py unit
```
