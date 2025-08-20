# Humaein Screening — Case Study #2: Cross-Platform Action Agent

This repository contains an AI-powered automation agent that can execute natural language instructions across multiple web services with different UI structures.

## Features

- **Natural Language Processing**: Accepts human-readable instructions (e.g., "Send email to joe@example.com about meeting")
- **Cross-Platform Automation**: Works with Gmail and Outlook web interfaces
- **LLM Integration**: Uses OpenAI GPT or mock LLM for task interpretation and UI step generation
- **Browser Automation**: Built with Playwright for reliable web interaction
- **Modular Architecture**: Easy to extend with new service providers
- **FastAPI Endpoints**: REST API for integration with other systems

## Architecture

### Core Components

1. **LLMInterface**: Abstract interface for AI reasoning
   - `MockLLM`: Pattern-based instruction parsing for testing
   - `OpenAILLM`: Real GPT integration for complex reasoning

2. **WebServiceProvider**: Abstract base for different web services
   - `GmailProvider`: Gmail web interface automation
   - `OutlookProvider`: Outlook web interface automation

3. **GenericUIAgent**: Main orchestrator that:
   - Interprets natural language instructions
   - Generates UI interaction steps
   - Executes tasks across multiple providers
   - Handles authentication and error recovery

### Data Flow

```
Natural Language Instruction
           ↓
    LLM Interpretation
           ↓
    Task Object Creation
           ↓
    UI Step Generation
           ↓
    Cross-Provider Execution
           ↓
    Results Aggregation
```

## Quick Start

### Prerequisites

- Python 3.9+
- Playwright browsers installed

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Environment Variables (Optional)

```bash
# For OpenAI integration
export OPENAI_API_KEY="your-api-key-here"
```

### CLI Usage

```bash
# Basic usage with mock LLM
python agent.py "Send email to joe@example.com about meeting at 2pm"

# Use specific providers
python agent.py "Schedule meeting tomorrow" --providers gmail outlook

# Run with visible browser
python agent.py "Send email" --headless false

# Use real OpenAI LLM (requires API key)
python agent.py "Send email" --mock-llm false
```

### API Usage

```bash
# Start the API server
python agent_api.py

# Send instruction via HTTP
curl -X POST "http://localhost:8001/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Send email to joe@example.com about meeting",
    "providers": ["gmail", "outlook"],
    "use_mock_llm": true
  }'
```

## API Endpoints

### POST /execute
Execute a natural language instruction across multiple providers.

**Request Body:**
```json
{
  "instruction": "Send email to joe@example.com about meeting",
  "providers": ["gmail", "outlook"],
  "headless": true,
  "use_mock_llm": true
}
```

**Response:**
```json
{
  "task_interpretation": {
    "action": "send_email",
    "to": "joe@example.com",
    "subject": "meeting",
    "body": "Automated message from AI agent"
  },
  "results": [
    {
      "success": true,
      "message": "Successfully executed send_email in Gmail",
      "details": {"provider": "Gmail", "task": {...}}
    },
    {
      "success": true,
      "message": "Successfully executed send_email in Outlook",
      "details": {"provider": "Outlook", "task": {...}}
    }
  ]
}
```

### GET /providers
List available service providers.

### GET /health
Health check endpoint.

## Supported Tasks

### Email Operations
- Send emails with recipients, subjects, and body content
- Works with Gmail and Outlook web interfaces
- Automatic authentication handling

### Meeting Scheduling
- Create calendar events
- Set meeting titles and durations
- Cross-platform calendar integration

### Extensible Framework
- Easy to add new task types
- Simple provider registration
- Custom UI step generation

## Provider Configuration

### Adding New Providers

1. Create a new class inheriting from `WebServiceProvider`
2. Implement `authenticate()` and `execute_task()` methods
3. Register in `GenericUIAgent.__init__()`

Example:
```python
class SlackProvider(WebServiceProvider):
    def __init__(self):
        super().__init__("Slack", "https://slack.com")
    
    def authenticate(self, page: Page, credentials: Dict[str, str]) -> bool:
        # Implement Slack authentication
        pass
    
    def execute_task(self, page: Page, task: Dict[str, Any], ui_steps: List[Dict[str, Any]]) -> TaskResult:
        # Implement Slack task execution
        pass
```

## Error Handling

- **Authentication Failures**: Graceful fallback with detailed error messages
- **UI Changes**: Robust element selection with fallback strategies
- **Network Issues**: Retry logic and timeout handling
- **Malformed Instructions**: Clear error reporting and suggestions

## Security Considerations

- **Credentials**: Stored securely (demo uses mock credentials)
- **Headless Mode**: Default secure execution without visible browser
- **Input Validation**: Sanitized natural language processing
- **Rate Limiting**: Built-in delays between actions

## Testing

### Mock Mode
- Use `--mock-llm` flag for testing without API calls
- Pattern-based instruction parsing
- No external dependencies

### Real Mode
- Requires OpenAI API key
- Full LLM reasoning capabilities
- Real browser automation

## Performance

- **Parallel Execution**: Tasks run across providers simultaneously
- **Efficient Browser Management**: Single browser instance for multiple providers
- **Caching**: LLM responses cached for similar instructions
- **Resource Cleanup**: Automatic browser cleanup after execution

## Monitoring and Logging

- **Structured Logging**: JSON-formatted execution logs
- **Performance Metrics**: Execution time and success rates
- **Error Tracking**: Detailed error reporting with context
- **Health Monitoring**: API health check endpoints

## Future Enhancements

- **Vision-Based UI Analysis**: Screenshot analysis for dynamic UI understanding
- **RAG Integration**: Knowledge base for complex task reasoning
- **Multi-Modal Support**: Voice and image input processing
- **Workflow Orchestration**: Complex multi-step task sequences
- **Provider Marketplace**: Community-contributed service integrations

## Troubleshooting

### Common Issues

1. **Browser Not Starting**: Ensure Playwright browsers are installed
2. **Authentication Failures**: Check credentials and service availability
3. **UI Element Not Found**: DOM structure may have changed
4. **API Rate Limits**: Add delays between requests

### Debug Mode

```bash
# Run with visible browser and verbose logging
python agent.py "Send email" --headless false
export LOG_LEVEL=DEBUG
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests and documentation
5. Submit a pull request

## License

This project is part of the Humaein AI Full Stack Developer screening process.
