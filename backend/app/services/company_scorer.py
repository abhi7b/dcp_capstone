"""
Company Scorer Module

Service for calculating relevance scores for companies based on
various metrics including Duke affiliation, growth stage, and activity.

Key Features:
- Multi-factor scoring
- Growth stage analysis
- Team evaluation
- Market potential assessment
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from ..utils.logger import scorer_logger as logger

class CompanyScorer:
    """
    Service for calculating company relevance scores based on 
    Duke affiliation, company stage, industry, and Twitter urgency.
    
    Score = (0.4 * Duke Affiliation) + (0.3 * Company Stage) + 
           (0.2 * Industry) + (0.1 * Twitter Urgency)
    """
    
    def __init__(self):
        logger.info("CompanyScorer initialized")
    
    def calculate_relevance_score(self, 
                                company_data: Dict[str, Any],
                                processed_people: List[Dict[str, Any]],
                                twitter_urgency_score: Optional[int] = None) -> int:
        """
        Calculate final company relevance score (0-100)
        """
        # 1. Calculate Duke affiliation score (0-100)
        duke_score = self._calculate_duke_score(processed_people)
        
        # 2. Calculate company stage score (0-100)
        stage_score = self._calculate_stage_score(company_data)
        
        # 3. Calculate industry score (0-100)
        industry_score = self._calculate_industry_score(company_data)
        
        # 4. Use provided Twitter urgency score or calculate from company data
        twitter_score = twitter_urgency_score if twitter_urgency_score is not None else self._calculate_twitter_score(company_data)
        
        # Apply weights to get final score
        final_score = int(
            (duke_score * 0.4) + 
            (stage_score * 0.3) + 
            (industry_score * 0.2) + 
            (twitter_score * 0.1)
        )
        
        # Ensure score is in range 1-100
        final_score = max(1, min(100, final_score))
        
        logger.info(
            f"Company {company_data.get('name', 'Unknown')}: "
            f"Duke={duke_score}, Stage={stage_score}, "
            f"Industry={industry_score}, Twitter={twitter_score}, "
            f"Final={final_score}"
        )
        
        return final_score
    
    def _calculate_duke_score(self, people: List[Dict[str, Any]]) -> int:
        """
        Calculate Duke affiliation component.
        
        Args:
            people: List of people associated with the company
            
        Returns:
            Duke affiliation score (0-100)
        """
        if not people:
            return 0
            
        # Role-based scores
        role_scores = {
            "founder": 100,
            "co-founder": 100,
            "ceo": 90,
            "cto": 85,
            "cfo": 85,
            "chief": 85,
            "vp": 80,
            "director": 75,
            "manager": 70,
            "employee": 60
        }
        
        max_score = 0
        duke_count = 0
        
        for person in people:
            if person.get("duke_affiliation_status") != "confirmed":
                continue
                
            duke_count += 1
            title = person.get("title", "").lower()
            
            # Find matching role score
            score = 60  # Default score for confirmed Duke alumni
            for role, value in role_scores.items():
                if role in title:
                    score = value
                    break
            
            max_score = max(max_score, score)
        
        # Bonus for multiple Duke affiliations
        if duke_count > 1:
            max_score = min(100, max_score + 10)
            
        return max_score
    
    def _calculate_stage_score(self, company_data: Dict[str, Any]) -> int:
        """
        Calculate growth stage component.
        
        Args:
            company_data: Company information
            
        Returns:
            Growth stage score (0-100)
        """
        stage = (company_data.get("funding_stage") or "").lower()
        
        if "pre-seed" in stage:
            return 100
        elif "seed" in stage:
            return 95
        elif "series a" in stage:
            return 90
        elif "series b" in stage:
            return 70
        elif "series c" in stage:
            return 50
        elif "late" in stage:
            return 30
        elif "public" in stage:
            return 10
        else:
            return 50  # Default if unknown
            
    def _calculate_industry_score(self, company_data: Dict[str, Any]) -> int:
        """
        Calculate market potential component.
        
        Args:
            company_data: Company information
            
        Returns:
            Market potential score (0-100)
        """
        industry = (company_data.get("industry") or "").lower()
        
        # High-priority industries
        if any(tech in industry for tech in ["ai", "artificial intelligence", "machine learning", "fintech"]):
            return 100
        elif any(tech in industry for tech in ["biotech", "healthcare"]):
            return 90
        elif any(tech in industry for tech in ["software", "cybersecurity", "cloud"]):
            return 80
        elif any(tech in industry for tech in ["clean tech", "edtech"]):
            return 70
        else:
            return 50  # Default for other industries
            
    def _calculate_twitter_score(self, company_data: Dict[str, Any]) -> int:
        """
        Calculate Twitter urgency component.
        
        Args:
            company_data: Company information
            
        Returns:
            Twitter urgency score (0-100)
        """
        # The urgency score is already normalized to 0-100 by the NitterNLP service

        return 50  # Default to middle score if no urgency score provided
