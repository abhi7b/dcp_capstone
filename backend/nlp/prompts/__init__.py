"""
Prompts package for the DCP AI Scouting Platform.

This package contains the prompts used for NLP analysis with OpenAI.
"""

from backend.nlp.prompts.company_prompts import (
    COMPANY_SYSTEM_PROMPT,
    COMPANY_USER_PROMPT
)

from backend.nlp.prompts.founder_prompts import (
    FOUNDER_SYSTEM_PROMPT,
    FOUNDER_USER_PROMPT
)

from backend.nlp.prompts.twitter_prompts import (
    TWITTER_SYSTEM_PROMPT,
    TWITTER_USER_PROMPT
)

__all__ = [
    # Company prompts
    "COMPANY_SYSTEM_PROMPT",
    "COMPANY_USER_PROMPT",
    
    # Founder prompts
    "FOUNDER_SYSTEM_PROMPT",
    "FOUNDER_USER_PROMPT",
    
    # Twitter prompts
    "TWITTER_SYSTEM_PROMPT",
    "TWITTER_USER_PROMPT"
] 