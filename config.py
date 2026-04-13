"""
Configuration file for AI CRO Personalizer.
Set environment variables or update these defaults.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# AI Provider Configuration
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")  # "openai" or "gemini"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")

# Request Configuration
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "2"))

# Personalization Configuration
MAX_ELEMENTS_TO_MODIFY = int(os.getenv("MAX_ELEMENTS_TO_MODIFY", "5"))
PERSONALIZATION_DEPTH = os.getenv("PERSONALIZATION_DEPTH", "moderate")  # minimal, moderate, aggressive

# Output Configuration
PREVIEW_MODE = os.getenv("PREVIEW_MODE", "true").lower() == "true"
CACHE_PERSONALIZED_PAGES = os.getenv("CACHE_PERSONALIZED_PAGES", "true").lower() == "true"

# Error Handling Strategy
# How to handle hallucinations: "strict" (reject), "moderate" (warn), "permissive" (accept)
HALLUCINATION_DETECTION = os.getenv("HALLUCINATION_DETECTION", "moderate")
VALIDATE_HTML_OUTPUT = os.getenv("VALIDATE_HTML_OUTPUT", "true").lower() == "true"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
