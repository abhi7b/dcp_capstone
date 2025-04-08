"""
Founder Scorer Module

Calculates relevance scores for founders and executives based on
various factors including Duke affiliation, role, and activity.

Key Features:
- Multi-factor scoring
- Duke affiliation weighting
- Role-based scoring
- Activity analysis
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from ..utils.logger import scorer_logger as logger

class FounderScorer:
    """
    Service for calculating founder/person relevance scores based on 
    Duke affiliation, role importance, and Twitter urgency.
    
    Score = (0.5 * Duke Affiliation) + (0.3 * Role Importance) + (0.2 * Twitter Urgency)
    """
    
    def __init__(self):
        logger.info("FounderScorer initialized")
    
    def calculate_relevance_score(self, 
                                person_data: Dict[str, Any],
                                twitter_urgency_score: Optional[float] = None) -> float:
        """
        Calculate overall relevance score for a person.
        
        Args:
            person_data: Dictionary containing person information
            twitter_urgency_score: Optional Twitter activity score
            
        Returns:
            Normalized relevance score (0-100)
        """
        # Calculate component scores
        duke_score = self._calculate_duke_affiliation_score(person_data)
        role_score = self._calculate_role_importance(person_data)
        
        # Use provided Twitter urgency score or calculate from person data
        twitter_score = twitter_urgency_score if twitter_urgency_score is not None else self._calculate_twitter_score(person_data)
        
        # Apply weights and normalize
        final_score = int(
            (duke_score * 0.5) + 
            (role_score * 0.3) + 
            (twitter_score * 0.2)
        )
        
        # Ensure score is in range 1-100
        final_score = max(1, min(100, final_score))
        
        logger.info(
            f"Scores for {person_data.get('name', 'Unknown')}: "
            f"Duke={duke_score}, Role={role_score}, "
            f"Twitter={twitter_score}, Final={final_score}"
        )
        
        return final_score
    
    def _calculate_duke_affiliation_score(self, person_data: Dict[str, Any]) -> int:
        """
        Calculate Duke affiliation score component.
        
        Args:
            person_data: Dictionary containing person information
            
        Returns:
            Duke affiliation score (0-100)
        """
        try:
            # Get education history
            education = person_data.get("education", "")
            if not education:
                return 0
            
            # Convert string to list if needed
            if isinstance(education, str):
                education_list = [edu.strip() for edu in education.split(",")]
            else:
                education_list = education
            
            # Check for Duke mentions
            duke_score = 0
            for edu in education_list:
                edu_lower = str(edu).lower()
                if "duke" in edu_lower:
                    if any(term in edu_lower for term in ["mba", "master", "phd", "doctorate"]):
                        duke_score = max(duke_score, 95)  # Graduate degree
                    elif "undergraduate" in edu_lower or "bachelor" in edu_lower:
                        duke_score = max(duke_score, 90)  # Undergraduate degree
                    else:
                        duke_score = max(duke_score, 85)  # Unspecified degree
            
            return duke_score
        except Exception as e:
            logger.error(f"Error calculating Duke affiliation score: {str(e)}")
            return 0
    
    def _calculate_role_importance(self, person_data: Dict[str, Any]) -> int:
        """
        Calculate role importance score component.
        
        Args:
            person_data: Dictionary containing person information
            
        Returns:
            Role importance score (0-100)
        """
        title = person_data.get("title", "").lower()
        
        if any(role in title for role in ["founder", "co-founder"]):
            return 100
        elif "ceo" in title:
            return 95
        elif any(role in title for role in ["cto", "cfo", "coo"]):
            return 90
        elif "chief" in title:
            return 85
        elif "vp" in title:
            return 80
        elif "director" in title:
            return 75
        elif "manager" in title:
            return 70
        else:
            return 50  # Default for other roles
            
    def _calculate_twitter_score(self, person_data: Dict[str, Any]) -> int:
        """
        Calculate activity and engagement score component.
        
        Args:
            person_data: Dictionary containing person information
            
        Returns:
            Activity score (0-100)
        """
        # If twitter_urgency_score is available, use it directly
        twitter_urgency_score = person_data.get("twitter_urgency_score")
        if twitter_urgency_score is not None:
            return twitter_urgency_score
            
        # If no urgency score available, return middle score
        return 50

