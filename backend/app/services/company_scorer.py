import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..utils.logger import scorer_logger

logger = logging.getLogger("scorer")

class Scorer:
    """
    Service for calculating company and person relevance scores based on 
    Duke affiliation, startup potential, and content relevance.
    
    All scores are normalized to a 1-100 scale.
    
    Final Score Formula:
    Total Score = (0.4 * Duke Affiliation) + (0.4 * Startup Potential) + (0.2 * Content Relevance)
    
    Where:
    - Duke Affiliation (1-100): Based on role importance and number of Duke affiliates
    - Startup Potential (1-100): Weighted combination of stage, industry, and company age
    - Content Relevance (1-100): Based on Twitter activity and recent funding
    """
    
    def __init__(self):
        # Duke Affiliation Base Scores (1-100)
        self.FOUNDER_WEIGHT = (90, 100)  # range for founder/co-founder
        self.CSUITE_WEIGHT = (80, 89)    # range for C-suite executives
        self.EXEC_WEIGHT = (85, 95)      # range for multiple executives
        self.EMPLOYEE_WEIGHT = (60, 75)   # range for general employees
        self.NO_AFFILIATION = 0          # no Duke connection
        
        # Startup Stage Scores (1-100)
        self.STARTUP_STAGES = {
            "pre-seed": 90,
            "seed": 100,
            "series a": 95,
            "series b": 70,
            "series c": 50,
            "late stage": 30,
            "public": 10,  # Changed from 0 to maintain 1-100 scale
            "unknown": 1   # Default minimum score
        }
        
        # Industry Scores (1-100)
        self.HIGH_VALUE_INDUSTRIES = {
            "ai": 100,
            "artificial intelligence": 100,
            "machine learning": 95,
            "biotech": 90,
            "healthcare": 85,
            "fintech": 85,
            "enterprise software": 80,
            "cybersecurity": 80,
            "clean tech": 75,
            "edtech": 70,
            "other": 1  # Default minimum score
        }
        
        scorer_logger.info("Scorer initialized with normalized 1-100 scale weights")
    
    def _normalize_score(self, score: float, min_val: float = 1) -> int:
        """Normalize score to 1-100 integer range"""
        if score <= 0:
            return min_val
        return max(min_val, min(100, round(score)))
    
    def _calculate_duke_affiliation_score(self, people: List[Dict[str, Any]]) -> int:
        """
        Calculate Duke affiliation score (1-100) based on people's roles and statuses
        
        Scoring logic:
        1. Base score from highest-ranking Duke affiliate
        2. +5 bonus for multiple Duke affiliates
        3. Minimum score of 1 if no affiliations
        """
        if not people:
            return 1
            
        max_score = 0
        confirmed_count = 0
        
        for person in people:
            if person.get("duke_affiliation_status") != "confirmed":
                continue
                
            confirmed_count += 1
            title = person.get("title", "").lower()
            
            # Determine base score based on role
            if any(role in title for role in ["founder", "co-founder", "cofounder"]):
                score = self.FOUNDER_WEIGHT[0]
            elif any(role in title for role in ["ceo", "cto", "cfo", "coo", "chief"]):
                score = self.CSUITE_WEIGHT[0]
            elif any(role in title for role in ["vp", "vice president", "director"]):
                score = self.EXEC_WEIGHT[0]
            else:
                score = self.EMPLOYEE_WEIGHT[0]
            
            # Boost score if multiple confirmed Duke affiliations
            if confirmed_count > 1:
                score = min(score + 5, 100)
            
            max_score = max(max_score, score)
        
        return self._normalize_score(max_score)
    
    def _calculate_startup_potential(self, company_data: Dict[str, Any]) -> int:
        """
        Calculate startup potential score (1-100)
        
        Components:
        - Stage score (40%): Based on funding stage
        - Industry score (40%): Based on sector/technology
        - Age score (20%): Preference for younger companies
        """
        # Stage score (1-100)
        stage = company_data.get("funding_stage", "").lower()
        stage_score = 1  # Default minimum
        for key, value in self.STARTUP_STAGES.items():
            if key in stage:
                stage_score = value
                break
        
        # Industry score (1-100)
        industry = company_data.get("industry", "").lower()
        industry_score = self.HIGH_VALUE_INDUSTRIES.get("other", 1)  # Default minimum
        for key, value in self.HIGH_VALUE_INDUSTRIES.items():
            if key in industry:
                industry_score = value
                break
        
        # Age score (1-100)
        founded_str = company_data.get("founded")
        age_score = 100  # Default to maximum if no date
        if founded_str:
            try:
                if len(founded_str) == 4:  # Just year
                    founded_year = int(founded_str)
                else:  # Full date
                    founded_year = datetime.strptime(founded_str, "%Y-%m-%d").year
                
                years_old = datetime.now().year - founded_year
                if years_old <= 2:
                    age_score = 100
                elif years_old <= 5:
                    age_score = 80
                elif years_old <= 10:
                    age_score = 60
                else:
                    age_score = 40
            except (ValueError, TypeError):
                scorer_logger.warning(f"Could not parse founded date: {founded_str}")
        
        # Combine scores with weights
        final_score = (
            (stage_score * 0.4) +
            (industry_score * 0.4) +
            (age_score * 0.2)
        )
        
        return self._normalize_score(final_score)
    
    def _calculate_content_relevance(self, company_data: Dict[str, Any]) -> int:
        """
        Calculate content relevance score (1-100) based on recent activity
        
        Components:
        - Twitter urgency (60%): Based on tweet analysis
        - Funding activity (40%): Recent funding events
        """
        base_score = 1  # Minimum score
        
        # Check Twitter activity if available
        twitter_summary = company_data.get("twitter_summary", {})
        if twitter_summary and not twitter_summary.get("twitter_unavailable", True):
            urgency_score = twitter_summary.get("urgency_score", 0)
            base_score += urgency_score * 0.6  # Twitter activity weight
        
        # Check recent funding activity
        funding_stage = company_data.get("funding_stage", "").lower()
        if "raising" in funding_stage or "announced" in funding_stage:
            base_score += 100 * 0.4  # Recent funding weight
        
        return self._normalize_score(base_score)
    
    def calculate_company_relevance_score(self, 
                                        company_data: Dict[str, Any],
                                        processed_people: List[Dict[str, Any]]) -> int:
        """
        Calculate final company relevance score (1-100)
        
        Formula:
        Score = (0.4 * Duke Affiliation) + (0.4 * Startup Potential) + (0.2 * Content Relevance)
        """
        # Calculate component scores
        duke_score = self._calculate_duke_affiliation_score(processed_people)
        startup_score = self._calculate_startup_potential(company_data)
        content_score = self._calculate_content_relevance(company_data)
        
        # Apply weights and normalize
        final_score = self._normalize_score(
            (duke_score * 0.4) +
            (startup_score * 0.4) +
            (content_score * 0.2)
        )
        
        scorer_logger.info(
            f"Scores for {company_data.get('name', 'Unknown')}: "
            f"Duke={duke_score}, Startup={startup_score}, "
            f"Content={content_score}, Final={final_score}"
        )
        
        return final_score

# Simple test case
if __name__ == "__main__":
    # Test company data
    test_company = {
        "name": "Acme AI",
        "industry": "artificial intelligence",
        "funding_stage": "Series A",
        "founded": "2022",
        "twitter_summary": {
            "urgency_score": 85,
            "twitter_unavailable": False
        }
    }
    
    # Test people data
    test_people = [
        {
            "name": "John Smith",
            "title": "Co-Founder & CEO",
            "duke_affiliation_status": "confirmed"
        },
        {
            "name": "Jane Doe",
            "title": "CTO",
            "duke_affiliation_status": "confirmed"
        }
    ]
    
    # Run test
    scorer = Scorer()
    score = scorer.calculate_company_relevance_score(test_company, test_people)
    
    print("\nTest Results:")
    print(f"Company: {test_company['name']}")
    print(f"Industry: {test_company['industry']}")
    print(f"Stage: {test_company['funding_stage']}")
    print(f"Founded: {test_company['founded']}")
    print(f"Duke-affiliated people: {len([p for p in test_people if p['duke_affiliation_status'] == 'confirmed'])}")
    print(f"Final Score: {score}") 