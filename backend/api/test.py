"""
Test API module for the DCP AI Scouting Platform.

This module provides test endpoints for the API, which can be used to verify
that the API is working correctly and to test various components.
"""
import logging
import sys
import os
from pathlib import Path


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database.db import get_db
from db.database.models import Company, Founder
from sqlalchemy import select
from typing import Dict, Any, List
from backend.config.logs import LogManager

# Set up logging
LogManager.setup_logging()
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.get("/ping")
async def ping() -> Dict[str, str]:
    """
    Simple ping endpoint to verify the API is running.
    
    Returns:
        Dict[str, str]: A simple response with a message
    """
    return {"message": "pong"}

@router.get("/db-check")
async def db_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Check if the database connection is working.
    
    Args:
        db: Database session
        
    Returns:
        Dict[str, Any]: Database status information
    """
    try:
        # Try to query the database
        company_query = select(Company).limit(1)
        founder_query = select(Founder).limit(1)
        
        company_result = await db.execute(company_query)
        founder_result = await db.execute(founder_query)
        
        company = company_result.scalar_one_or_none()
        founder = founder_result.scalar_one_or_none()
        
        return {
            "status": "connected",
            "company_found": company is not None,
            "founder_found": founder is not None
        }
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )

@router.get("/error-test")
async def error_test() -> Dict[str, str]:
    """
    Test endpoint that always raises an error.
    
    This is useful for testing error handling.
    
    Raises:
        HTTPException: Always raises a 500 error
    """
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="This is a test error"
    )

@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Get basic statistics about the database.
    
    Args:
        db: Database session
        
    Returns:
        Dict[str, Any]: Statistics about the database
    """
    try:
        # Count companies
        company_query = select(Company)
        company_result = await db.execute(company_query)
        companies = company_result.scalars().all()
        
        # Count founders
        founder_query = select(Founder)
        founder_result = await db.execute(founder_query)
        founders = founder_result.scalars().all()
        
        # Count Duke-affiliated companies
        duke_company_query = select(Company).where(Company.duke_affiliated == True)
        duke_company_result = await db.execute(duke_company_query)
        duke_companies = duke_company_result.scalars().all()
        
        # Count Duke-affiliated founders
        duke_founder_query = select(Founder).where(Founder.duke_affiliated == True)
        duke_founder_result = await db.execute(duke_founder_query)
        duke_founders = duke_founder_result.scalars().all()
        
        return {
            "total_companies": len(companies),
            "total_founders": len(founders),
            "duke_affiliated_companies": len(duke_companies),
            "duke_affiliated_founders": len(duke_founders),
            "duke_company_percentage": round(len(duke_companies) / len(companies) * 100, 2) if companies else 0,
            "duke_founder_percentage": round(len(duke_founders) / len(founders) * 100, 2) if founders else 0
        }
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve stats: {str(e)}"
        ) 