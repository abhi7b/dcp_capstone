import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("scorer")

class Scorer:
    """
    Service for calculating relevance scores for companies and founders
    based on data extracted by the NLPProcessor.
    Duke affiliation status is determined by NLP and used to boost relevance scores.
    """
    
    def __init__(self):
        # High-value industries for scoring
        self.high_value_industries = [
            "ai", "artificial intelligence", "machine learning", "ml", 
            "biotech", "biotechnology", "healthcare", "health", "medical", 
            "fintech", "financial technology", "finance",
            "saas", "software", "cloud", "data", "analytics",
            "cybersecurity", "security", "crypto", "blockchain",
            "climate", "renewable", "clean energy"
        ]
        
        # Funding stages with weights (higher is better for early-stage)
        self.funding_stage_weights = {
            "pre-seed": 1.0,
            "seed": 0.9,
            "series a": 0.8,
            "series b": 0.5,
            "series c": 0.3,
            "growth": 0.2,
            "ipo": 0.1,
            "public": 0.1,
            "bootstrapped": 0.8  # Bootstrapped can be attractive too
        }
        
        logger.info("Scorer initialized")
    
    def calculate_company_relevance_score(self, company_data: Dict[str, Any], processed_people: List[Dict[str, Any]]) -> int:
        """
        Calculates a single relevance score for a company based on its attributes and Duke affiliation.
        
        Args:
            company_data: NLP extracted data for the company.
            processed_people: List of processed people data with duke_affiliation_status.
            
        Returns:
            An integer relevance score (0-100).
        """
        # 1. Duke Affiliation Component (highest weight: 50%)
        DUKE_WEIGHT = 0.5
        
        # Check if any associated person has confirmed Duke affiliation
        has_confirmed_duke = any(p.get("duke_affiliation_status") == "confirmed" for p in processed_people)
        has_review_duke = any(p.get("duke_affiliation_status") == "please review" for p in processed_people)
        
        # Calculate affiliation component
        if has_confirmed_duke:
            # Additional bonus if multiple people are Duke affiliated
            confirmed_count = sum(1 for p in processed_people if p.get("duke_affiliation_status") == "confirmed")
            base_duke_score = 100  # Full score for having confirmed Duke affiliation
            if confirmed_count > 1:
                # Small bonus for multiple affiliates (but cap at 100)
                duke_component = min(100, base_duke_score + (confirmed_count - 1) * 5)
            else:
                duke_component = base_duke_score
        elif has_review_duke:
            duke_component = 40  # Moderate score for "please review" status
        else:
            duke_component = 0   # No Duke affiliation points
        
        # 2. Business Potential Component (30%)
        BUSINESS_WEIGHT = 0.3
        
        # Funding stage score
        stage_score = 0
        funding_stage = (company_data.get("funding_stage") or "").lower()
        if "seed" in funding_stage: 
            stage_score = 90
        elif "series a" in funding_stage: 
            stage_score = 100
        elif "pre-seed" in funding_stage: 
            stage_score = 80
        elif "series" in funding_stage:  # Other series rounds
            stage_score = 70
        elif funding_stage:  # Any other named stage
            stage_score = 50
        else:
            stage_score = 30  # Unknown stage
        
        # Activity/growth signals
        activity_score = 0
        
        # Look for growth indicators in summary
        summary = (company_data.get("summary") or "").lower()
        twitter_summary = (company_data.get("twitter_summary") or "").lower()
        combined_text = f"{summary} {twitter_summary}"
        
        growth_indicators = ["hiring", "growing", "launch", "new product", "expansion", "funding", "raised", "investment"]
        matches = sum(1 for indicator in growth_indicators if indicator in combined_text)
        activity_score = min(50, matches * 10)  # Cap at 50 points
        
        business_component = (stage_score + activity_score) / 2  # Average the two scores
        
        # 3. Industry Component (20%)
        INDUSTRY_WEIGHT = 0.2
        
        # Industry score
        industry_score = 40  # Base score
        industry = (company_data.get("industry") or "").lower()
        
        # Check high-value industries
        if any(ind in industry for ind in self.high_value_industries):
            industry_score = 90
        
        # Combine all components with weights
        final_score = (
            DUKE_WEIGHT * duke_component +
            BUSINESS_WEIGHT * business_component +
            INDUSTRY_WEIGHT * industry_score
        )
        
        # Round to integer and ensure in range 0-100
        result = max(0, min(100, int(round(final_score))))
        
        logger.info(f"Company '{company_data.get('name')}' relevance score: {result} (Duke: {duke_component}, Business: {business_component}, Industry: {industry_score})")
        return result
    
    def calculate_person_relevance_score(self, person_data: Dict[str, Any]) -> int:
        """
        Calculates a single relevance score for a person based on their attributes and Duke affiliation.
        
        Args:
            person_data: NLP extracted data for the person, including duke_affiliation_status.
            
        Returns:
            An integer relevance score (0-100).
        """
        # 1. Duke Affiliation Component (highest weight: 60%)
        DUKE_WEIGHT = 0.6
        
        # Read duke_affiliation_status directly from person_data (determined by NLP)
        affiliation_status = person_data.get("duke_affiliation_status", "no")
        
        if affiliation_status == "confirmed":
            duke_component = 100  # Full score for confirmed affiliation
        elif affiliation_status == "please review":
            duke_component = 40   # Moderate score for "please review" status
        else:
            duke_component = 0    # No Duke affiliation points
        
        # 2. Role/Experience Component (25%)
        ROLE_WEIGHT = 0.25
        
        # Role score based on title
        role_score = 0
        title = (person_data.get("title") or "").lower()
        
        if any(role in title for role in ["founder", "ceo", "cto", "president", "chief"]):
            role_score = 100  # Top leadership roles
        elif any(role in title for role in ["vp", "executive", "director", "head"]):
            role_score = 80   # Senior management
        elif any(role in title for role in ["manager", "lead", "principal"]):
            role_score = 60   # Mid-level roles
        elif title:  # Any other role
            role_score = 40
        
        # Add points for previous experience
        previous_companies = person_data.get("previous_companies", [])
        experience_bonus = min(20, len(previous_companies) * 5)  # 5 points per previous company, max 20
        
        role_component = min(100, role_score + experience_bonus)
        
        # 3. Education Component (15% - beyond Duke affiliation)
        EDUCATION_WEIGHT = 0.15
        
        # Education quality score
        education_score = 50  # Base score
        education = person_data.get("education", [])
        
        # Look for prestigious schools
        prestigious_schools = ["harvard", "stanford", "mit", "yale", "princeton", "oxford", "cambridge", "caltech", "berkeley"]
        prestigious_degrees = ["phd", "mba", "md", "jd"]
        
        if any(any(school in (edu.get("school") or "").lower() for school in prestigious_schools) for edu in education):
            education_score += 30
        
        if any(any(degree in (edu.get("degree") or "").lower() for degree in prestigious_degrees) for edu in education):
            education_score += 20
        
        education_component = min(100, education_score)
        
        # Combine all components with weights
        final_score = (
            DUKE_WEIGHT * duke_component +
            ROLE_WEIGHT * role_component +
            EDUCATION_WEIGHT * education_component
        )
        
        # Round to integer and ensure in range 0-100
        result = max(0, min(100, int(round(final_score))))
        
        logger.info(f"Person '{person_data.get('name')}' relevance score: {result} (Duke: {duke_component}, Role: {role_component}, Education: {education_component})")
        return result 