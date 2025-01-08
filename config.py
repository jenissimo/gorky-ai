# config.py

import os

# LLM API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'your-openai-api-key')
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', 'your-claude-api-key')
OLLAMA_API_KEY = os.getenv('OLLAMA_API_KEY', 'your-ollama-api-key')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'your-deepseek-api-key')

# Database configuration
DATABASE = 'book_generator.db'

# Default settings
DEFAULT_BOOK_SIZE = 'medium'  # options: short_story, small_book, large_book

# Prompts directory
PROMPTS_DIR = 'prompts'

# Logging configuration
LOG_FILE = 'book_generator.log'

# Editor iterations
MAX_EDIT_ITERATIONS = 1
