# AI Model Status Check

## Current Configuration

The AI model service supports two providers:
1. **OpenAI** (GPT-4o) - via `OPENAI_API_KEY`
2. **Anthropic** (Claude 3.7 Sonnet) - via `ANTHROPIC_API_KEY`

## How It Works

The AI service (`backend/services/ai_report.py`) will:
1. **Check for API keys** from environment variables
2. **Use Anthropic if available** (priority)
3. **Fall back to OpenAI** if Anthropic is not available
4. **Use template reports** if neither API key is configured

## Current Status

Based on the code analysis:

### ✅ **Code is Working**
- AI service is properly implemented
- Error handling and retry logic are in place
- Fallback to template reports works correctly

### ⚠️ **Configuration Status Unknown**
To check if API keys are configured, you need to:

1. **Check environment variables:**
   ```bash
   echo $OPENAI_API_KEY
   echo $ANTHROPIC_API_KEY
   ```

2. **Or check your `.env` file** (if using one):
   ```bash
   cat .env | grep -E "(OPENAI_API_KEY|ANTHROPIC_API_KEY)"
   ```

3. **Check backend logs** when generating reports:
   - If you see: `"No AI API keys configured, using template report"` → AI is NOT active
   - If you see: `"Anthropic API failed"` or `"OpenAI API failed"` → AI is configured but having issues
   - If you see API usage logs → AI is working

## How to Enable AI Model

### Option 1: Set Environment Variables
```bash
export OPENAI_API_KEY="your-openai-api-key"
# OR
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

### Option 2: Create `.env` File
Create a `.env` file in the project root:
```env
OPENAI_API_KEY=your-openai-api-key
# OR
ANTHROPIC_API_KEY=your-anthropic-api-key
```

### Option 3: Docker Environment
If using Docker, add to `docker-compose.yml`:
```yaml
environment:
  - OPENAI_API_KEY=${OPENAI_API_KEY}
  # OR
  - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

## Testing AI Model

Run the diagnostic script:
```bash
cd backend
python3 test_ai_model.py
```

This will:
- Check if API keys are configured
- Test API connectivity
- Show a preview of the AI response

## What Happens Without API Keys?

If no API keys are configured:
- ✅ System still works
- ✅ Reports are generated using templates
- ⚠️ Reports are less detailed (no AI analysis)
- ⚠️ No stakeholder-specific customization
- ⚠️ No advanced insights or recommendations

## API Usage & Costs

The service tracks API usage and costs:
- **OpenAI GPT-4o**: ~$2.50/$10 per 1M tokens (input/output)
- **Anthropic Claude**: ~$3/$15 per 1M tokens (input/output)

Check usage stats via the API or logs.

## Troubleshooting

### AI Not Working?
1. **Check API keys are set**: `echo $OPENAI_API_KEY`
2. **Check API key validity**: Keys must be valid and have credits
3. **Check network connectivity**: Service needs internet access
4. **Check logs**: Look for error messages in backend logs
5. **Check rate limits**: APIs have rate limits that may cause failures

### Common Errors
- `"No AI API keys configured"` → Set environment variables
- `"Invalid API key"` → Check API key is correct
- `"Rate limit exceeded"` → Wait or upgrade API plan
- `"Network error"` → Check internet connection

## Next Steps

1. **Verify configuration**: Check if API keys are set
2. **Test connectivity**: Run the diagnostic script
3. **Check logs**: Look for AI-related messages in backend logs
4. **Enable if needed**: Set API keys to activate AI features
