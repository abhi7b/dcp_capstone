import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..utils.logger import scorer_logger

class FounderScorer:
    """
    Service for calculating founder/person relevance scores based on 
    Duke affiliation, startup experience, and content relevance.
    
    All scores are normalized to a 1-100 scale.
    
    Final Score Formula:
    Total Score = (0.5 * Duke Affiliation) + (0.3 * Startup Experience) + (0.2 * Content Relevance)
    
    Where:
    - Duke Affiliation (1-100): Based on education history and degree type
    - Startup Experience (1-100): Based on founder/executive roles and company stages
    - Content Relevance (1-100): Based on Twitter activity and recent news
    """
    
    def __init__(self):
        # Duke Education Scores (1-100)
        self.DUKE_SCORES = {
            "mba": 100,        # MBA from Duke (Fuqua)
            "graduate": 95,    # Other Duke graduate degree
            "undergrad": 90,   # Duke undergraduate
            "certificate": 80, # Duke certificate/non-degree
            "attended": 70,    # Attended Duke but unclear completion
            "unknown": 1       # Default minimum score
        }
        
        # Role Scores (1-100)
        self.ROLE_SCORES = {
            "founder": 100,
            "co-founder": 100,
            "ceo": 95,
            "cto": 90,
            "cfo": 90,
            "coo": 90,
            "chief": 85,
            "vp": 80,
            "director": 75,
            "manager": 70,
            "other": 1
        }
        
        # Company Stage Scores (1-100)
        self.STAGE_SCORES = {
            "pre-seed": 90,
            "seed": 100,
            "series a": 95,
            "series b": 80,
            "series c": 70,
            "late stage": 60,
            "public": 50,
            "other": 1
        }
        
        scorer_logger.info("FounderScorer initialized with normalized 1-100 scale weights")
    
    def _normalize_score(self, score: float, min_val: float = 1) -> int:
        """Normalize score to 1-100 integer range"""
        if score <= 0:
            return min_val
        return max(min_val, min(100, round(score)))
    
    def _calculate_duke_affiliation_score(self, person_data: Dict[str, Any]) -> int:
        """
        Calculate Duke affiliation score (1-100) based on education history
        
        Scoring logic:
        1. Highest score based on degree type if found
        2. Default to minimum score if no Duke education found
        """
        if person_data.get("duke_affiliation_status") != "confirmed":
            return 1
            
        max_score = 1
        education = person_data.get("education", [])
        
        for edu in education:
            school = edu.get("school", "").lower()
            degree = edu.get("degree", "").lower()
            
            if "duke" in school:
                if "mba" in degree or "fuqua" in school:
                    score = self.DUKE_SCORES["mba"]
                elif any(term in degree for term in ["phd", "master", "ms", "ma"]):
                    score = self.DUKE_SCORES["graduate"]
                elif any(term in degree for term in ["bs", "ba", "bachelor"]):
                    score = self.DUKE_SCORES["undergrad"]
                elif "certificate" in degree:
                    score = self.DUKE_SCORES["certificate"]
                else:
                    score = self.DUKE_SCORES["attended"]
                    
                max_score = max(max_score, score)
        
        return self._normalize_score(max_score)
    
    def _calculate_startup_experience(self, person_data: Dict[str, Any]) -> int:
        """
        Calculate startup experience score (1-100)
        
        Components:
        - Role score (60%): Based on highest-ranking role
        - Company stage score (40%): Based on company funding stage
        """
        # Calculate role score
        current_role = person_data.get("title", "").lower()
        role_score = 1
        
        for role, score in self.ROLE_SCORES.items():
            if role in current_role:
                role_score = max(role_score, score)
                
        # Calculate company stage score
        current_company = person_data.get("current_company", "").lower()
        stage_score = 1
        
        for stage, score in self.STAGE_SCORES.items():
            if stage in current_company:
                stage_score = max(stage_score, score)
        
        # Combine scores with weights
        final_score = (role_score * 0.6) + (stage_score * 0.4)
        return self._normalize_score(final_score)
    
    def _calculate_content_relevance(self, person_data: Dict[str, Any]) -> int:
        """
        Calculate content relevance score (1-100) based on recent activity
        
        Components:
        - Twitter urgency (70%): Based on tweet analysis
        - Recent activity (30%): Based on news and updates
        """
        base_score = 1
        
        # Check Twitter activity if available
        twitter_summary = person_data.get("twitter_summary", {})
        if twitter_summary and not twitter_summary.get("twitter_unavailable", True):
            urgency_score = twitter_summary.get("urgency_score", 0)
            base_score += urgency_score * 0.7
        
        # Check recent activity (funding, new role, etc.)
        if person_data.get("current_company"):
            base_score += 100 * 0.3  # Active in a company
        
        return self._normalize_score(base_score)
    
    def calculate_person_relevance_score(self, person_data: Dict[str, Any]) -> int:
        """
        Calculate final person relevance score (1-100)
        
        Formula:
        Score = (0.5 * Duke Affiliation) + (0.3 * Startup Experience) + (0.2 * Content Relevance)
        """
        # Calculate component scores
        duke_score = self._calculate_duke_affiliation_score(person_data)
        startup_score = self._calculate_startup_experience(person_data)
        content_score = self._calculate_content_relevance(person_data)
        
        # Apply weights and normalize
        final_score = self._normalize_score(
            (duke_score * 0.5) +
            (startup_score * 0.3) +
            (content_score * 0.2)
        )
        
        scorer_logger.info(
            f"Scores for {person_data.get('name', 'Unknown')}: "
            f"Duke={duke_score}, Startup={startup_score}, "
            f"Content={content_score}, Final={final_score}"
        )
        
        return final_score

# Simple test case
if __name__ == "__main__":
    # Test person data
    test_person = {
        "name": "John Smith",
        "title": "Co-Founder & CEO",
        "education": [
            {
                "school": "Duke University",
                "degree": "MBA",
                "years": "2018-2020"
            }
        ],
        "duke_affiliation_status": "confirmed",
        "current_company": "AI Startup (Series A)",
        "twitter_summary": {
            "urgency_score": 85,
            "twitter_unavailable": False
        }
    }
    
    # Run test
    scorer = FounderScorer()
    score = scorer.calculate_person_relevance_score(test_person)
    
    print("\nTest Results:")
    print(f"Person: {test_person['name']}")
    print(f"Role: {test_person['title']}")
    print(f"Education: {test_person['education'][0]['school']} - {test_person['education'][0]['degree']}")
    print(f"Current Company: {test_person['current_company']}")
    print(f"Final Score: {score}")
