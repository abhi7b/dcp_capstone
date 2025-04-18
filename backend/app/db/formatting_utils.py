"""
Utility functions for formatting data before database insertion.
"""
from typing import List, Dict, Any, Optional

def format_education(edu_list: List[Dict[str, Any]]) -> Optional[str]:
    """Formats education list into a simplified string."""
    if not edu_list or not isinstance(edu_list, list):
        return None
    
    formatted_entries = []
    for entry in edu_list:
        if isinstance(entry, dict):
            # Order: school, degree, field, year
            values = [str(entry.get(key, '')) for key in ['school', 'degree', 'field', 'year'] if entry.get(key)]
            if values:
                formatted_entries.append(", ".join(values))
                
    return "; ".join(formatted_entries) if formatted_entries else None

def format_previous_companies(comp_list: List[str]) -> Optional[str]:
    """Formats previous companies list into a comma-separated string."""
    if not comp_list or not isinstance(comp_list, list):
        return None
    # Filter out any non-string or empty items just in case
    valid_comps = [str(comp) for comp in comp_list if isinstance(comp, str) and comp]
    return ", ".join(valid_comps) if valid_comps else None

def format_source_links(links_list: List[Dict[str, Any]]) -> Optional[str]:
    """Formats source links list into a simplified string 'Title (URL)' separated by semicolons."""
    if not links_list or not isinstance(links_list, list):
        return None
    
    formatted_entries = []
    for entry in links_list:
        if isinstance(entry, dict):
            title = entry.get('title')
            url = entry.get('url')
            if title and url:
                formatted_entries.append(f"{title} ({url})")
            elif title:
                formatted_entries.append(title)
            elif url:
                 formatted_entries.append(url)
                 
    return "; ".join(formatted_entries) if formatted_entries else None 