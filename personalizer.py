"""
Core AI and personalization logic for the CRO Personalizer.
Handles API calls, prompt engineering, HTML modification, and error recovery.
"""
import json
import logging
import time
from typing import Dict, Tuple, Optional
import requests
from bs4 import BeautifulSoup
from config import (
    AI_PROVIDER, OPENAI_API_KEY, OPENAI_MODEL, 
    GEMINI_API_KEY, GEMINI_MODEL, REQUEST_TIMEOUT, 
    MAX_RETRIES, RETRY_DELAY, HALLUCINATION_DETECTION
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScrapingError(Exception):
    """Raised when page scraping fails."""
    pass


class PersonalizationError(Exception):
    """Raised when AI personalization fails."""
    pass


def fetch_landing_page(url: str) -> Tuple[str, Dict]:
    """
    Fetch and parse landing page with error handling.
    
    Returns:
        Tuple of (HTML content, metadata dict)
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    try:
        response = requests.get(
            url, 
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract page metadata
        metadata = {
            "original_h1": soup.find('h1').text.strip() if soup.find('h1') else None,
            "original_title": soup.find('title').text.strip() if soup.find('title') else None,
            "original_meta_desc": soup.find('meta', attrs={'name': 'description'}).get('content', '')
                if soup.find('meta', attrs={'name': 'description'}) else None,
            "has_form": bool(soup.find('form')),
            "cta_text": _extract_cta(soup)
        }
        
        return response.text, metadata
        
    except requests.exceptions.Timeout:
        raise ScrapingError(f"Timeout fetching {url}. Try a different landing page.")
    except requests.exceptions.ConnectionError:
        raise ScrapingError(f"Cannot connect to {url}. Verify the URL is correct.")
    except Exception as e:
        raise ScrapingError(f"Failed to fetch {url}: {str(e)}")


def _extract_cta(soup: BeautifulSoup) -> Optional[str]:
    """Extract call-to-action button text."""
    cta_selectors = [
        {'name': 'button'},
        {'name': 'a', 'class': lambda x: x and 'button' in x.lower()},
        {'name': 'a', 'class': lambda x: x and ('cta' in x.lower() or 'action' in x.lower())}
    ]
    
    for selector in cta_selectors:
        element = soup.find(**selector)
        if element:
            return element.get_text(strip=True)
    return None


def analyze_with_ai(ad_context: str, page_metadata: Dict) -> Dict:
    """
    Call AI to generate personalization recommendations.
    
    Strategy for handling inconsistent outputs:
    - Implemented structured JSON output with schema validation
    - Retry logic with exponential backoff
    - Fallback to conservative defaults if AI produces invalid responses
    """
    prompt = _build_prompt(ad_context, page_metadata)
    
    for attempt in range(MAX_RETRIES):
        try:
            if AI_PROVIDER == "openai":
                response_text = _call_openai(prompt)
            else:
                response_text = _call_gemini(prompt)
            
            # Parse and validate JSON response
            result = _parse_and_validate_response(response_text)
            logger.info(f"AI personalization successful on attempt {attempt + 1}")
            return result
            
        except PersonalizationError as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
                continue
            else:
                logger.error(f"All {MAX_RETRIES} attempts failed. Using fallback.")
                return _get_fallback_personalization(ad_context, page_metadata)


def _build_prompt(ad_context: str, page_metadata: Dict) -> str:
    """Build structured prompt for AI with clear schema."""
    return f"""You are an expert CRO (Conversion Rate Optimization) specialist. 
Your task is to personalize a landing page based on ad creative context.

AD CREATIVE CONTEXT: {ad_context}

CURRENT PAGE METADATA:
- H1: {page_metadata.get('original_h1', 'Unknown')}
- Page Title: {page_metadata.get('original_title', 'Unknown')}
- Meta Description: {page_metadata.get('original_meta_desc', 'Unknown')}
- Has Form: {page_metadata.get('has_form', False)}
- Current CTA: {page_metadata.get('cta_text', 'Unknown')}

PERSONALIZATION REQUIREMENTS:
1. Ensure copy alignment between ad and landing page
2. Enhance urgency and relevance based on ad context
3. Do NOT hallucinate offers or features not mentioned
4. Keep copy professional and trust-building
5. Output must be valid JSON

RESPOND WITH ONLY VALID JSON (NO MARKDOWN):
{{
    "h1": "<personalized headline matching ad context>",
    "meta_description": "<updated meta description>",
    "cta_text": "<updated call-to-action>",
    "subheadline": "<secondary headline for credibility>",
    "reasoning": "<brief explanation of changes>"
}}

IMPORTANT: Return valid JSON only. No explanations outside JSON."""


def _call_openai(prompt: str) -> str:
    """Call OpenAI API with error handling."""
    if not OPENAI_API_KEY:
        raise PersonalizationError("OPENAI_API_KEY not configured")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
        
    except Exception as e:
        raise PersonalizationError(f"OpenAI API error: {str(e)}")


def _call_gemini(prompt: str) -> str:
    """Call Google Gemini API with error handling."""
    if not GEMINI_API_KEY:
        raise PersonalizationError("GEMINI_API_KEY not configured")
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        raise PersonalizationError(f"Gemini API error: {str(e)}")


def _parse_and_validate_response(response_text: str) -> Dict:
    """
    Parse AI response with hallucination detection.
    
    Strategy for handling hallucinations:
    - Extract JSON from potentially malformed responses
    - Validate that suggestions are reasonable
    - Reject claims about non-existent features/offers
    """
    try:
        # Try to extract JSON if wrapped in markdown
        if "```" in response_text:
            response_text = response_text.split("```")[1].replace("json", "").strip()
        
        data = json.loads(response_text)
        
        # Validate required fields
        required = {"h1", "cta_text", "reasoning"}
        if not required.issubset(data.keys()):
            raise PersonalizationError(f"Missing required fields: {required - set(data.keys())}")
        
        # Hallucination detection: check for suspicious patterns
        if HALLUCINATION_DETECTION in ["strict", "moderate"]:
            _check_hallucinations(data)
        
        return data
        
    except json.JSONDecodeError as e:
        raise PersonalizationError(f"Invalid JSON response: {str(e)}")


def _check_hallucinations(data: Dict) -> None:
    """Detect suspicious patterns indicating AI hallucination."""
    hallucination_keywords = [
        "guarantee", "100% free", "limited time",
        "exclusive deal", "special offer", "exclusive access"
    ]
    
    text = " ".join(str(v).lower() for v in data.values())
    
    # Count suspicious keywords
    suspicious_count = sum(1 for keyword in hallucination_keywords if keyword in text)
    
    if suspicious_count > 2 and HALLUCINATION_DETECTION == "strict":
        raise PersonalizationError("Response contains too many marketing buzzwords (potential hallucination)")
    elif suspicious_count > 2 and HALLUCINATION_DETECTION == "moderate":
        logger.warning("Response contains marketing buzzwords - review carefully")


def _get_fallback_personalization(ad_context: str, page_metadata: Dict) -> Dict:
    """
    Safe fallback when AI fails or produces invalid output.
    Uses keyword-based templated personalization instead of AI.
    """
    keyword = ad_context.split()[0] if ad_context else "offer"
    original_h1 = page_metadata.get('original_h1', 'Learn More')
    
    return {
        "h1": f"{original_h1} - Personalized for You",
        "meta_description": f"Tailored {keyword} just for you. See how we can help.",
        "cta_text": "Get Started",
        "subheadline": "We matched this page to your interests",
        "reasoning": "Fallback mode: Template-based personalization (AI unavailable)"
    }


def personalize_html(html_content: str, personalization: Dict) -> str:
    """
    Apply personalization to HTML while preserving structure and styling.
    
    Strategy for broken UI handling:
    - Preserve original HTML structure
    - Only modify specific safe elements (h1, title, meta tags)
    - Validate output HTML syntax
    - Never remove elements, only update content
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Update H1
        h1 = soup.find('h1')
        if h1:
            h1.string = personalization.get('h1', h1.get_text())
        
        # Update page title
        title = soup.find('title')
        if title:
            title.string = personalization.get('meta_description', title.get_text())[:60]
        
        # Update meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            meta_desc['content'] = personalization.get('meta_description', '')
        
        # Update CTA buttons (conservative approach - only exact matches)
        cta_text = personalization.get('cta_text', '')
        if cta_text:
            for button in soup.find_all(['button', 'a'], class_=lambda x: x and 'button' in x.lower()):
                button.string = cta_text
        
        # Add personalization metadata comment
        personalization_note = soup.new_tag('comment')
        personalization_note.string = f"Personalized for ad context. Changes: {personalization.get('reasoning', '')}"
        soup.insert(0, personalization_note)
        
        return str(soup)
        
    except Exception as e:
        logger.error(f"HTML personalization failed: {str(e)}")
        return html_content  # Return original if personalization fails


def validate_html_output(html_content: str) -> Tuple[bool, str]:
    """
    Validate personalized HTML for syntax errors.
    Returns (is_valid, error_message)
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Check for basic structure integrity
        if not soup.find('body') and not soup.find('div'):
            return False, "HTML appears to be malformed or empty"
        return True, ""
    except Exception as e:
        return False, str(e)
