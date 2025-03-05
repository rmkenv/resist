# app.py
import streamlit as st
import requests
import pandas as pd
import json
import os
from datetime import datetime
import google.generativeai as genai
import plotly.express as px
import plotly.graph_objects as go
import re
from io import StringIO
import time
import numpy as np

# Set page configuration
st.set_page_config(
    page_title="Congressional Finance & Project 2025 Tracker",
    page_icon="🏛️",
    layout="wide"
)

# API keys setup - in production, use Streamlit secrets
if 'FEC_API_KEY' in st.secrets:
    FEC_API_KEY = st.secrets["FEC_API_KEY"]
else:
    FEC_API_KEY = os.environ.get("FEC_API_KEY", "DEMO_KEY")  # Use DEMO_KEY for testing

if 'CONGRESS_API_KEY' in st.secrets:
    CONGRESS_API_KEY = st.secrets["CONGRESS_API_KEY"]
else:
    CONGRESS_API_KEY = os.environ.get("CONGRESS_API_KEY", "")  # You'll need to get this

if 'GEMINI_API_KEY' in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")  # You'll need to get this

# Configure Gemini AI if key is available
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Cache configuration
CACHE_TTL = 3600  # Cache time-to-live in seconds (1 hour)

# Define key Project 2025 policy areas and positions
PROJECT_2025_POLICIES = {
    "economy": [
        "Reducing federal regulations",
        "Tax cuts and reforms",
        "America First trade policies",
        "Reducing federal workforce",
        "Privatizing government functions",
        "Cutting non-defense spending"
    ],
    "immigration": [
        "Border wall construction",
        "Restricting asylum claims",
        "Ending catch-and-release policies",
        "Limiting legal immigration",
        "Mass deportations",
        "Ending birthright citizenship"
    ],
    "healthcare": [
        "Repealing parts of the ACA",
        "Price transparency",
        "Reducing FDA regulations",
        "Limiting federal healthcare spending",
        "Restricting abortion access",
        "Promoting health savings accounts"
    ],
    "education": [
        "School choice initiatives",
        "Limiting Department of Education authority",
        "Promoting patriotic education",
        "Restricting DEI programs",
        "Banning critical race theory",
        "Protecting parental rights"
    ],
    "energy": [
        "Expanding fossil fuel production",
        "Reducing environmental regulations",
        "Withdrawing from climate agreements",
        "Energy independence initiatives",
        "Opening federal lands to drilling",
        "Limiting renewable energy subsidies"
    ],
    "defense": [
        "Increasing military spending",
        "Reducing foreign military commitments",
        "Strengthening border security",
        "Space Force expansion",
        "Countering China",
        "Reducing NATO commitments"
    ],
    "judiciary": [
        "Appointing originalist judges",
        "Limiting administrative state authority",
        "Protecting religious liberty",
        "Second Amendment protections",
        "Restricting federal agency power",
        "Overturning Chevron deference"
    ],
    "elections": [
        "Voter ID requirements",
        "Limiting mail-in voting",
        "Purging voter rolls",
        "State legislature control of elections",
        "Challenging election results",
        "Restricting early voting"
    ]
}

# Project 2025 policy details with specific proposals
PROJECT_2025_DETAILS = {
    "economy": {
        "description": "Project 2025 advocates for deregulation, tax cuts, and reducing the size of government to promote economic growth.",
        "key_proposals": [
            "Eliminate two regulations for every new one created",
            "Make Trump tax cuts permanent",
            "Reduce non-defense discretionary spending by 10%",
            "Privatize government services",
            "Dismantle the Consumer Financial Protection Bureau",
            "Reduce federal workforce by 20%"
        ],
        "alignment_indicators": {
            "high": ["Voted for tax cuts", "Supported deregulation", "Opposed minimum wage increases"],
            "low": ["Supported increased regulations", "Voted for tax increases", "Supported expanded government programs"]
        }
    },
    "immigration": {
        "description": "Project 2025 calls for strict immigration enforcement, border security, and limiting both legal and illegal immigration.",
        "key_proposals": [
            "Complete the border wall",
            "End DACA and other immigration programs",
            "Implement mass deportations",
            "Restrict asylum claims",
            "Reduce legal immigration quotas",
            "Challenge birthright citizenship"
        ],
        "alignment_indicators": {
            "high": ["Supported border wall funding", "Opposed amnesty", "Voted for immigration restrictions"],
            "low": ["Supported path to citizenship", "Opposed border wall", "Voted for expanded immigration"]
        }
    },
    "healthcare": {
        "description": "Project 2025 seeks to dismantle the Affordable Care Act, reduce healthcare regulations, and limit federal healthcare spending.",
        "key_proposals": [
            "Repeal key provisions of the ACA",
            "Block grant Medicaid to states",
            "Expand health savings accounts",
            "Reduce FDA regulations",
            "Restrict abortion access",
            "Limit Medicare spending"
        ],
        "alignment_indicators": {
            "high": ["Voted to repeal ACA", "Supported abortion restrictions", "Opposed Medicare expansion"],
            "low": ["Defended ACA", "Supported abortion access", "Voted for Medicare expansion"]
        }
    },
    "education": {
        "description": "Project 2025 advocates for school choice, reducing federal education authority, and eliminating 'woke' curriculum.",
        "key_proposals": [
            "Eliminate Department of Education",
            "Expand school choice and vouchers",
            "Ban critical race theory in schools",
            "End Title IX protections for transgender students",
            "Eliminate federal student loan forgiveness",
            "Promote patriotic education"
        ],
        "alignment_indicators": {
            "high": ["Supported school choice", "Opposed student loan forgiveness", "Voted against DEI programs"],
            "low": ["Opposed school vouchers", "Supported student loan forgiveness", "Defended DEI initiatives"]
        }
    },
    "energy": {
        "description": "Project 2025 promotes fossil fuel production, reducing environmental regulations, and withdrawing from climate agreements.",
        "key_proposals": [
            "Withdraw from Paris Climate Agreement",
            "Expand oil and gas drilling on federal lands",
            "Eliminate EPA's authority to regulate greenhouse gases",
            "Revoke clean energy subsidies",
            "Fast-track pipeline approvals",
            "Eliminate fuel efficiency standards"
        ],
        "alignment_indicators": {
            "high": ["Supported fossil fuel expansion", "Opposed climate regulations", "Voted against renewable subsidies"],
            "low": ["Supported climate action", "Voted for environmental protections", "Advocated for renewable energy"]
        }
    },
    "defense": {
        "description": "Project 2025 calls for increased military spending, reduced foreign commitments, and confronting China.",
        "key_proposals": [
            "Increase defense budget by 5% annually",
            "Reduce NATO commitments",
            "Expand Space Force",
            "Withdraw from international organizations",
            "Confront China militarily",
            "End 'woke' military policies"
        ],
        "alignment_indicators": {
            "high": ["Supported defense increases", "Opposed international agreements", "Voted for military expansion"],
            "low": ["Supported defense cuts", "Advocated for international cooperation", "Opposed military buildups"]
        }
    },
    "judiciary": {
        "description": "Project 2025 seeks to appoint conservative judges, limit federal agency power, and protect religious liberty.",
        "key_proposals": [
            "Appoint originalist judges",
            "Overturn Chevron deference",
            "Expand religious liberty protections",
            "Strengthen Second Amendment rights",
            "Limit federal agency rulemaking",
            "Restrict abortion rights"
        ],
        "alignment_indicators": {
            "high": ["Supported conservative judges", "Voted for religious liberty protections", "Opposed gun control"],
            "low": ["Supported liberal judges", "Voted against religious exemptions", "Advocated for gun control"]
        }
    },
    "elections": {
        "description": "Project 2025 advocates for stricter voting requirements, state control of elections, and challenging election results.",
        "key_proposals": [
            "Implement nationwide voter ID",
            "Restrict mail-in voting",
            "Purge voter rolls regularly",
            "Give state legislatures more control over elections",
            "Challenge election results in court",
            "Limit early voting periods"
        ],
        "alignment_indicators": {
            "high": ["Supported voter ID laws", "Opposed mail-in voting", "Questioned election results"],
            "low": ["Opposed voter ID requirements", "Supported expanded voting access", "Defended election integrity"]
        }
    }
}

# Sample bill data for demonstration purposes
SAMPLE_BILLS = [
    {
        "bill_id": "hr1",
        "title": "For the People Act",
        "description": "Expands voting rights, changes campaign finance laws to reduce the influence of money in politics, limits partisan gerrymandering, and creates new ethics rules for federal officeholders.",
        "categories": ["elections"],
        "project2025_alignment": "opposed",
        "votes": {
            "democrat": {"yes": 220, "no": 0},
            "republican": {"yes": 0, "no": 210}
        }
    },
    {
        "bill_id": "hr2",
        "title": "American Energy Independence Act",
        "description": "Expands oil and gas drilling on federal lands, fast-tracks pipeline approvals, and reduces environmental regulations.",
        "categories": ["energy"],
        "project2025_alignment": "aligned",
        "votes": {
            "democrat": {"yes": 5, "no": 215},
            "republican": {"yes": 208, "no": 2}
        }
    },
    {
        "bill_id": "hr3",
        "title": "Border Security Enhancement Act",
        "description": "Provides funding for border wall construction, restricts asylum claims, and increases immigration enforcement.",
        "categories": ["immigration"],
        "project2025_alignment": "aligned",
        "votes": {
            "democrat": {"yes": 10, "no": 210},
            "republican": {"yes": 205, "no": 5}
        }
    },
    {
        "bill_id": "hr4",
        "title": "Affordable Care Act Enhancement",
        "description": "Expands ACA subsidies, adds new coverage requirements, and increases funding for Medicaid.",
        "categories": ["healthcare"],
        "project2025_alignment": "opposed",
        "votes": {
            "democrat": {"yes": 218, "no": 2},
            "republican": {"yes": 3, "no": 207}
        }
    },
    {
        "bill_id": "hr5",
        "title": "Educational Freedom and Choice Act",
        "description": "Creates a federal school voucher program, reduces Department of Education authority, and bans certain curriculum topics.",
        "categories": ["education"],
        "project2025_alignment": "aligned",
        "votes": {
            "democrat": {"yes": 0, "no": 220},
            "republican": {"yes": 210, "no": 0}
        }
    },
    {
        "bill_id": "hr6",
        "title": "Tax Cuts Extension Act",
        "description": "Makes the 2017 tax cuts permanent and adds new tax reductions for businesses.",
        "categories": ["economy"],
        "project2025_alignment": "aligned",
        "votes": {
            "democrat": {"yes": 8, "no": 212},
            "republican": {"yes": 210, "no": 0}
        }
    },
    {
        "bill_id": "hr7",
        "title": "National Defense Authorization Act",
        "description": "Increases military spending by 5%, expands Space Force, and adds new provisions for confronting China.",
        "categories": ["defense"],
        "project2025_alignment": "aligned",
        "votes": {
            "democrat": {"yes": 150, "no": 70},
            "republican": {"yes": 200, "no": 10}
        }
    },
    {
        "bill_id": "hr8",
        "title": "Judicial Reform Act",
        "description": "Limits federal agency rulemaking authority, expands religious liberty protections, and restricts court jurisdiction on certain issues.",
        "categories": ["judiciary"],
        "project2025_alignment": "aligned",
        "votes": {
            "democrat": {"yes": 0, "no": 220},
            "republican": {"yes": 210, "no": 0}
        }
    },
    {
        "bill_id": "hr9",
        "title": "Climate Action Now Act",
        "description": "Requires the U.S. to remain in the Paris Agreement and develop a plan to meet emissions targets.",
        "categories": ["energy"],
        "project2025_alignment": "opposed",
        "votes": {
            "democrat": {"yes": 220, "no": 0},
            "republican": {"yes": 3, "no": 207}
        }
    },
    {
        "bill_id": "hr10",
        "title": "Secure Elections Act",
        "description": "Requires voter ID, restricts mail-in voting, and gives state legislatures more control over elections.",
        "categories": ["elections"],
        "project2025_alignment": "aligned",
        "votes": {
            "democrat": {"yes": 0, "no": 220},
            "republican": {"yes": 210, "no": 0}
        }
    }
]

# Sample member voting records for demonstration
SAMPLE_MEMBER_VOTES = {
    "R000600": {  # Sample Republican
        "hr1": "no",
        "hr2": "yes",
        "hr3": "yes",
        "hr4": "no",
        "hr5": "yes",
        "hr6": "yes",
        "hr7": "yes",
        "hr8": "yes",
        "hr9": "no",
        "hr10": "yes"
    },
    "D000622": {  # Sample Democrat
        "hr1": "yes",
        "hr2": "no",
        "hr3": "no",
        "hr4": "yes",
        "hr5": "no",
        "hr6": "no",
        "hr7": "yes",
        "hr8": "no",
        "hr9": "yes",
        "hr10": "no"
    },
    "R000605": {  # Moderate Republican
        "hr1": "no",
        "hr2": "yes",
        "hr3": "yes",
        "hr4": "yes",  # Crossed party lines
        "hr5": "no",   # Crossed party lines
        "hr6": "yes",
        "hr7": "yes",
        "hr8": "yes",
        "hr9": "yes",  # Crossed party lines
        "hr10": "no"   # Crossed party lines
    },
    "D000623": {  # Moderate Democrat
        "hr1": "yes",
        "hr2": "yes",  # Crossed party lines
        "hr3": "yes",  # Crossed party lines
        "hr4": "yes",
        "hr5": "no",
        "hr6": "no",
        "hr7": "yes",
        "hr8": "no",
        "hr9": "yes",
        "hr10": "no"
    }
}

# Sample member data for demonstration
SAMPLE_MEMBERS = {
    "R000600": {
        "name": "John Republican",
        "party": "REP",
        "state": "TX",
        "district": "1",
        "bioguide_id": "R000600",
        "fec_candidate_id": "H0TX01123"
    },
    "D000622": {
        "name": "Jane Democrat",
        "party": "DEM",
        "state": "CA",
        "district": "12",
        "bioguide_id": "D000622",
        "fec_candidate_id": "H0CA12456"
    },
    "R000605": {
        "name": "Robert Moderate-R",
        "party": "REP",
        "state": "ME",
        "district": "2",
        "bioguide_id": "R000605",
        "fec_candidate_id": "H0ME02789"
    },
    "D000623": {
        "name": "Sarah Moderate-D",
        "party": "DEM",
        "state": "AZ",
        "district": "1",
        "bioguide_id": "D000623",
        "fec_candidate_id": "H0AZ01012"
    }
}

# Sample contribution data for demonstration
SAMPLE_CONTRIBUTIONS = {
    "H0TX01123": [
        {"contributor_name": "Oil Industry PAC", "contribution_receipt_amount": 50000, "contribution_receipt_date": "2023-05-15", "contributor_employer": "Big Oil Corp"},
        {"contributor_name": "Defense Contractors Association", "contribution_receipt_amount": 35000, "contribution_receipt_date": "2023-06-22", "contributor_employer": "Defense Inc"},
        {"contributor_name": "Conservative Values PAC", "contribution_receipt_amount": 25000, "contribution_receipt_date": "2023-07-10", "contributor_employer": "Conservative Alliance"},
        {"contributor_name": "National Rifle Association", "contribution_receipt_amount": 20000, "contribution_receipt_date": "2023-08-05", "contributor_employer": "NRA"},
        {"contributor_name": "Small Business Coalition", "contribution_receipt_amount": 15000, "contribution_receipt_date": "2023-09-12", "contributor_employer": "Various Small Businesses"}
    ],
    "H0CA12456": [
        {"contributor_name": "Progressive Action Fund", "contribution_receipt_amount": 45000, "contribution_receipt_date": "2023-05-20", "contributor_employer": "Progressive Alliance"},
        {"contributor_name": "Teachers Union PAC", "contribution_receipt_amount": 30000, "contribution_receipt_date": "2023-06-15", "contributor_employer": "National Education Association"},
        {"contributor_name": "Environmental Defense Fund", "contribution_receipt_amount": 25000, "contribution_receipt_date": "2023-07-22", "contributor_employer": "Environmental Defense"},
        {"contributor_name": "Healthcare Workers Union", "contribution_receipt_amount": 20000, "contribution_receipt_date": "2023-08-10", "contributor_employer": "Healthcare United"},
        {"contributor_name": "Tech Industry Coalition", "contribution_receipt_amount": 15000, "contribution_receipt_date": "2023-09-05", "contributor_employer": "Various Tech Companies"}
    ],
    "H0ME02789": [
        {"contributor_name": "Moderate Republican PAC", "contribution_receipt_amount": 40000, "contribution_receipt_date": "2023-05-10", "contributor_employer": "Bipartisan Solutions"},
        {"contributor_name": "Healthcare Industry Group", "contribution_receipt_amount": 30000, "contribution_receipt_date": "2023-06-20", "contributor_employer": "Various Healthcare Companies"},
        {"contributor_name": "Energy Innovation Fund", "contribution_receipt_amount": 25000, "contribution_receipt_date": "2023-07-15", "contributor_employer": "Clean Energy Corp"},
        {"contributor_name": "Business Roundtable", "contribution_receipt_amount": 20000, "contribution_receipt_date": "2023-08-22", "contributor_employer": "Various Corporations"},
        {"contributor_name": "National Security Alliance", "contribution_receipt_amount": 15000, "contribution_receipt_date": "2023-09-10", "contributor_employer": "Defense Contractors"}
    ],
    "H0AZ01012": [
        {"contributor_name": "Moderate Democrats Coalition", "contribution_receipt_amount": 35000, "contribution_receipt_date": "2023-05-25", "contributor_employer": "Centrist Alliance"},
        {"contributor_name": "Rural Development Fund", "contribution_receipt_amount": 30000, "contribution_receipt_date": "2023-06-10", "contributor_employer": "Rural America Initiative"},
        {"contributor_name": "Border Security PAC", "contribution_receipt_amount": 25000, "contribution_receipt_date": "2023-07-20", "contributor_employer": "Border Solutions Group"},
        {"contributor_name": "Energy Workers Union", "contribution_receipt_amount": 20000, "contribution_receipt_date": "2023-08-15", "contributor_employer": "Energy Workers United"},
        {"contributor_name": "Small Business Association", "contribution_receipt_amount": 15000, "contribution_receipt_date": "2023-09-22", "contributor_employer": "Small Business Alliance"}
    ]
}

# Functions to fetch data from Congress.gov
@st.cache_data(ttl=CACHE_TTL)
def fetch_congressional_data(congress_number=118):
    """Fetch bill and voting data from Congress.gov"""
    # In a real implementation, you would call the Congress.gov API
    # For demonstration, we'll use sample data
    
    return {
        "bills": SAMPLE_BILLS,
        "status": "success"
    }

@st.cache_data(ttl=CACHE_TTL)
def fetch_member_data(member_id=None, state=None, party=None):
    """Fetch member data from Congress.gov"""
    # In a real implementation, you would call the Congress.gov API
    # For demonstration, we'll use sample data
    
    if member_id and member_id in SAMPLE_MEMBERS:
        return {
            "results": [SAMPLE_MEMBERS[member_id]],
            "status": "success"
        }
    
    results = []
    for id, member in SAMPLE_MEMBERS.items():
        if (not state or member["state"] == state) and (not party or member["party"] == party):
            results.append(member)
    
    return {
        "results": results,
        "status": "success"
    }

@st.cache_data(ttl=CACHE_TTL)
def fetch_member_votes(member_id):
    """Fetch voting record for a specific member"""
    # In a real implementation, you would call the Congress.gov API
    # For demonstration, we'll use sample data
    
    if member_id in SAMPLE_MEMBER_VOTES:
        return {
            "votes": SAMPLE_MEMBER_VOTES[member_id],
            "status": "success"
        }
    else:
        return {
            "votes": {},
            "status": "error",
            "message": "Member not found"
        }

# Functions to fetch data from FEC API
@st.cache_data(ttl=CACHE_TTL)
def fetch_candidate_data(name=None, state=None, party=None):
    """Fetch candidate data from FEC API"""
    # In a real implementation, you would call the FEC API
    # For demonstration, we'll convert our sample data to FEC format
    
    results = []
    for id, member in SAMPLE_MEMBERS.items():
        if (not name or name.lower() in member["name"].lower()) and \
           (not state or member["state"] == state) and \
           (not party or member["party"] == party):
            results.append({
                "name": member["name"],
                "party": member["party"],
                "state": member["state"],
                "office_full": f"House (District {member['district']})",
                "candidate_id": member["fec_candidate_id"],
                "bioguide_id": member["bioguide_id"]
            })
    
    return {
        "results": results,
        "status": "success"
    }

@st.cache_data(ttl=CACHE_TTL)
def fetch_candidate_contributions(candidate_id):
    """Fetch contribution data for a specific candidate"""
    # In a real implementation, you would call the FEC API
    # For demonstration, we'll use sample data
    
    if candidate_id in SAMPLE_CONTRIBUTIONS:
        return {
            "results": SAMPLE_CONTRIBUTIONS[candidate_id],
            "status": "success"
        }
    else:
        return {
            "results": [],
            "status": "error",
            "message": "Candidate not found"
        }

# Data analysis functions
def analyze_voting_pattern(member_id, bills_data):
    """Analyze voting patterns for a specific member of Congress"""
    # Get member votes
    member_votes_data = fetch_member_votes(member_id)
    
    if member_votes_data["status"] != "success":
        return {
            "status": "error",
            "message": member_votes_data.get("message", "Failed to fetch voting data")
        }
    
    member_votes = member_votes_data["votes"]
    bills = bills_data["bills"]
    
    # Initialize counters
    total_votes = 0
    project2025_aligned_votes = 0
    project2025_opposed_votes = 0
    
    # Initialize category counters
    categories = PROJECT_2025_POLICIES.keys()
    votes_by_category = {category: {"aligned": 0, "opposed": 0, "total": 0} for category in categories}
    
    # Analyze each bill vote
    for bill in bills:
        bill_id = bill["bill_id"]
        if bill_id in member_votes:
            total_votes += 1
            vote = member_votes[bill_id]
            alignment = bill["project2025_alignment"]
            
            # Check if vote aligns with Project 2025
            is_aligned = (alignment == "aligned" and vote == "yes") or (alignment == "opposed" and vote == "no")
            
            if is_aligned:
                project2025_aligned_votes += 1
            else:
                project2025_opposed_votes += 1
            
            # Update category counters
            for category in bill["categories"]:
                if category in votes_by_category:
                    votes_by_category[category]["total"] += 1
                    if is_aligned:
                        votes_by_category[category]["aligned"] += 1
                    else:
                        votes_by_category[category]["opposed"] += 1
    
    # Calculate alignment percentages
    overall_alignment = (project2025_aligned_votes / total_votes * 100) if total_votes > 0 else 0
    
    category_alignment = {}
    for category, counts in votes_by_category.items():
        if counts["total"] > 0:
            category_alignment[category] = counts["aligned"] / counts["total"] * 100
        else:
            category_alignment[category] = 0
    
    return {
        "status": "success",
        "total_votes": total_votes,
        "project2025_aligned_votes": project2025_aligned_votes,
        "project2025_opposed_votes": project2025_opposed_votes,
        "overall_alignment": overall_alignment,
        "votes_by_category": votes_by_category,
        "category_alignment": category_alignment
    }

def match_contributions_to_votes(candidate_id, member_id, bills_data):
    """Match campaign contributions to voting records"""
    # Get contribution data
    contributions_data = fetch_candidate_contributions(candidate_id)
    
    if contributions_data["status"] != "success":
        return {
            "status": "error",
            "message": "Failed to fetch contribution data"
        }
    
    # Get voting pattern
    voting_pattern = analyze_voting_pattern(member_id, bills_data)
    
    if voting_pattern["status"] != "success":
        return {
            "status": "error",
            "message": "Failed to analyze voting pattern"
        }
    
    # In a real implementation, this would involve complex analysis
    # For demonstration, we'll create a simplified correlation
    
    contributions = contributions_data["results"]
    
    # Map contributors to likely policy interests
    contributor_interests = {}
    for contribution in contributions:
        contributor = contribution["contributor_name"]
        employer = contribution["contributor_employer"]
        amount = contribution["contribution_receipt_amount"]
        
        # Simple keyword matching (would be more sophisticated in practice)
        interests = []
        
        if any(word in contributor.lower() or word in employer.lower() 
               for word in ["oil", "gas", "coal", "energy", "petroleum"]):
            interests.append("energy")
        
        if any(word in contributor.lower() or word in employer.lower() 
               for word in ["bank", "invest", "financ", "capital", "fund"]):
            interests.append("economy")
        
        if any(word in contributor.lower() or word in employer.lower() 
               for word in ["defense", "military", "security", "weapon"]):
            interests.append("defense")
        
        if any(word in contributor.lower() or word in employer.lower() 
               for word in ["health", "pharma", "medical", "hospital"]):
            interests.append("healthcare")
        
        if any(word in contributor.lower() or word in employer.lower() 
               for word in ["school", "education", "teacher", "university"]):
            interests.append("education")
        
        if any(word in contributor.lower() or word in employer.lower() 
               for word in ["immigration", "border", "patrol"]):
            interests.append("immigration")
        
        if any(word in contributor.lower() or word in employer.lower() 
               for word in ["court", "judicial", "legal", "law", "attorney"]):
            interests.append("judiciary")
        
        if any(word in contributor.lower() or word in employer.lower() 
               for word in ["election", "vote", "ballot", "campaign"]):
            interests.append("elections")
        
        # If no specific interests found, mark as "general"
        if not interests:
            interests.append("general")
        
        # Add to contributor interests
        contributor_interests[contributor] = {
            "interests": interests,
            "amount": amount
        }
    
    # Calculate alignment between contributions and votes
    interest_alignment = {}
    for category in PROJECT_2025_POLICIES.keys():
        # Get category alignment from voting pattern
        category_align_pct = voting_pattern["category_alignment"].get(category, 0)
        
        # Sum contributions in this category
        category_contributions = sum(
            contrib["amount"] for contrib, data in contributor_interests.items()
            if category in data["interests"]
        )
        
        interest_alignment[category] = {
            "alignment_percentage": category_align_pct,
            "total_contributions": category_contributions,
            "contributors": [
                {"name": contrib, "amount": data["amount"]}
                for contrib, data in contributor_interests.items()
                if category in data["interests"]
            ]
        }
    
    # Calculate overall correlation
    total_aligned_contributions = sum(
        data["total_contributions"] * data["alignment_percentage"] / 100
        for category, data in interest_alignment.items()
    )
    
    total_contributions = sum(
        data["total_contributions"]
        for category, data in interest_alignment.items()
    )
    
    overall_correlation = (total_aligned_contributions / total_contributions * 100) if total_contributions > 0 else 0
    
    return {
        "status": "success",
        "interest_alignment": interest_alignment,
        "overall_correlation": overall_correlation,
        "contributor_interests": contributor_interests
    }

def calculate_project2025_alignment(member_id, bills_data):
    """Calculate alignment with Project 2025 positions"""
    # Get voting pattern analysis
    voting_pattern = analyze_voting_pattern(member_id, bills_data)
    
    if voting_pattern["status"] != "success":
        return {
            "status": "error",
            "message": "Failed to analyze voting pattern"
        }
    
    # For a real implementation with Gemini AI, you would use this prompt:
    # prompt = f"""
    # Analyze the following voting record for member of Congress {member_id} 
    # and determine their alignment with Project 2025 policy positions:
    # 
    # Voting record:
    # {json.dumps(voting_pattern, indent=2)}
    # 
    # Project 2025 key policy positions:
    # {json.dumps(PROJECT_2025_DETAILS, indent=2)}
    # 
    # Provide a detailed analysis of how this member's voting record aligns with Project 2025 
    # policy positions across each category. Calculate an overall alignment score from 0-100 
    # where 100 is perfect alignment with Project 2025 positions.
    # """
    
    # For demonstration, we'll use the voting pattern analysis directly
    
    # Get member data for context
    member_data = fetch_member_data(member_id)
    if member_data["status"] != "success" or not member_data["results"]:
        member_info = {"name": "Unknown", "party": "Unknown", "state": "Unknown"}
    else:
        member_info = member_data["results"][0]
    
    # Get overall alignment score
    overall_score = voting_pattern["overall_alignment"]
    
    # Get category scores
    category_scores = voting_pattern["category_alignment"]
    
    # Generate analysis text based on scores
    analysis = f"## Project 2025 Alignment Analysis for {member_info['name']}\n\n"
    analysis += f"### Overall Alignment: {overall_score:.1f}%\n\n"
    
    # Add party context
    if member_info["party"] == "REP":
        if overall_score > 75:
            analysis += "This Republican representative shows strong alignment with Project 2025 policies, "
            analysis += "voting consistently in favor of bills that align with the project's conservative agenda.\n\n"
        elif overall_score > 50:
            analysis += "This Republican representative shows moderate alignment with Project 2025 policies, "
            analysis += "supporting many but not all initiatives that align with the project's agenda.\n\n"
        else:
            analysis += "Despite being a Republican, this representative shows limited alignment with Project 2025 policies, "
            analysis += "often voting against bills that would advance the project's conservative agenda.\n\n"
    elif member_info["party"] == "DEM":
        if overall_score < 25:
            analysis += "This Democratic representative shows strong opposition to Project 2025 policies, "
            analysis += "consistently voting against bills that align with the project's conservative agenda.\n\n"
        elif overall_score < 50:
            analysis += "This Democratic representative shows moderate opposition to Project 2025 policies, "
            analysis += "though occasionally supporting some initiatives that align with the project's agenda.\n\n"
        else:
            analysis += "Despite being a Democrat, this representative shows surprising alignment with Project 2025 policies, "
            analysis += "often voting for bills that would advance the project's conservative agenda.\n\n"
    
    # Add category-specific analysis
    analysis += "### Policy Area Analysis\n\n"
    
    for category, score in category_scores.items():
        if category in PROJECT_2025_DETAILS:
            details = PROJECT_2025_DETAILS[category]
            analysis += f"#### {category.capitalize()}: {score:.1f}%\n\n"
            
            # Add category description
            analysis += f"{details['description']}\n\n"
            
            # Add alignment assessment
            if score > 75:
                analysis += "**Strong alignment**: "
                indicators = details["alignment_indicators"]["high"]
                if indicators:
                    analysis += f"The representative has {indicators[0].lower()}"
                    if len(indicators) > 1:
                        analysis += f" and {indicators[1].lower()}"
                    analysis += ".\n\n"
            elif score > 50:
                analysis += "**Moderate alignment**: "
                analysis += "The representative has shown mixed support for Project 2025 positions in this area.\n\n"
            elif score > 25:
                analysis += "**Limited alignment**: "
                analysis += "The representative has occasionally supported Project 2025 positions but generally opposes them.\n\n"
            else:
                analysis += "**Strong opposition**: "
                indicators = details["alignment_indicators"]["low"]
                if indicators:
                    analysis += f"The representative has {indicators[0].lower()}"
                    if len(indicators) > 1:
                        analysis += f" and {indicators[1].lower()}"
                    analysis += ".\n\n"
            
            # Add key proposals
            analysis += "**Key Project 2025 proposals in this area:**\n"
            for proposal in details["key_proposals"][:3]:  # Show top 3 proposals
                analysis += f"- {proposal}\n"
            analysis += "\n"
    
    # Add conclusion
    analysis += "### Conclusion\n\n"
    if overall_score > 75:
        analysis += f"Representative {member_info['name']} demonstrates strong alignment with Project 2025 policy positions "
        analysis += "across most policy areas, particularly in "
        # Find top 2 aligned categories
        top_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)[:2]
        analysis += f"{top_categories[0][0]} ({top_categories[0][1]:.1f}%) and {top_categories[1][0]} ({top_categories[1][1]:.1f}%)."
    elif overall_score > 50:
        analysis += f"Representative {member_info['name']} demonstrates moderate alignment with Project 2025 policy positions, "
        analysis += "with stronger support in some areas than others. "
        # Find top aligned category
        top_category = max(category_scores.items(), key=lambda x: x[1])
        analysis += f"Their strongest alignment is in {top_category[0]} ({top_category[1]:.1f}%)."
    elif overall_score > 25:
        analysis += f"Representative {member_info['name']} demonstrates limited alignment with Project 2025 policy positions, "
        analysis += "opposing most but not all of the project's agenda. "
        # Find top aligned category
        top_category = max(category_scores.items(), key=lambda x: x[1])
        analysis += f"Their only notable alignment is in {top_category[0]} ({top_category[1]:.1f}%)."
    else:
        analysis += f"Representative {member_info['name']} demonstrates strong opposition to Project 2025 policy positions "
        analysis += "across virtually all policy areas. "
        # Find most opposed categories
        bottom_categories = sorted(category_scores.items(), key=lambda x: x[1])[:2]
        analysis += f"Their opposition is strongest in {bottom_categories[0][0]} ({bottom_categories[0][1]:.1f}%) and {bottom_categories[1][0]} ({bottom_categories[1][1]:.1f}%)."
    
    return {
        "status": "success",
        "overall_score": overall_score,
        "category_scores": category_scores,
        "analysis": analysis
    }

def categorize_bill_by_project2025(bill_data):
    """Categorize a bill according to Project 2025 policy areas"""
    # This would analyze bill text and metadata to determine which
    # Project 2025 policy areas it relates to
    
    # For demonstration, we'll use the categories already assigned in our sample data
    return bill_data.get("categories", [])

def map_donor_interests_to_project2025(donor_data):
    """Map donor industries and interests to Project 2025 policy areas"""
    # This would analyze donor information to determine which
    # Project 2025 policy areas align with their interests
    
    contributor = donor_data.get("contributor_name", "")
    employer = donor_data.get("contributor_employer", "")
    
    interests = []
    
    # Simple keyword matching (would be more sophisticated in practice)
    if any(word in contributor.lower() or word in employer.lower() 
           for word in ["oil", "gas", "coal", "energy", "petroleum"]):
        interests.append("energy")
    
    if any(word in contributor.lower() or word in employer.lower() 
           for word in ["bank", "invest", "financ", "capital", "fund"]):
        interests.append("economy")
    
    if any(word in contributor.lower() or word in employer.lower() 
           for word in ["defense", "military", "security", "weapon"]):
        interests.append("defense")
    
    if any(word in contributor.lower() or word in employer.lower() 
           for word in ["health", "pharma", "medical", "hospital"]):
        interests.append("healthcare")
    
    if any(word in contributor.lower() or word in employer.lower() 
           for word in ["school", "education", "teacher", "university"]):
        interests.append("education")
    
    if any(word in contributor.lower() or word in employer.lower() 
           for word in ["immigration", "border", "patrol"]):
        interests.append("immigration")
    
    if any(word in contributor.lower() or word in employer.lower() 
           for word in ["court", "judicial", "legal", "law", "attorney"]):
        interests.append("judiciary")
    
    if any(word in contributor.lower() or word in employer.lower() 
           for word in ["election", "vote", "ballot", "campaign"]):
        interests.append("elections")
    
    # If no specific interests found, mark as "general"
    if not interests:
        interests.append("general")
    
    return interests

# Streamlit UI
def main():
    st.title("Congressional Finance & Project 2025 Alignment Tracker")
    
    # Add information about Project 2025
    with st.expander("About Project 2025"):
        st.write("""
        Project 2025 is a conservative policy blueprint developed by The Heritage Foundation 
        and its partners. It outlines a comprehensive agenda for the executive branch, 
        focusing on dismantling what it calls the "administrative state" and implementing 
        conservative policies across government agencies.
        
        This application analyzes how congressional voting records align with Project 2025 
        policy positions and connects this information with campaign finance data to identify 
        potential correlations between donor interests and policy alignment.
        """)
    
    # Add information about the data sources
    with st.expander("About the Data"):
        st.write("""
        This application uses data from:
        
        1. **Congress.gov** - For bill information and voting records
        2. **Federal Election Commission (FEC)** - For campaign finance data
        
        The alignment analysis is performed by comparing voting records with Project 2025 policy positions.
        
        Note: For demonstration purposes, this version uses sample data. A production version would 
        connect to the actual APIs and use real-time data.
        """)
    
    # Sidebar for search
    st.sidebar.header("Search Politicians")
    search_name = st.sidebar.text_input("Name")
    search_state = st.sidebar.selectbox(
        "State", 
        ["", "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", 
         "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", 
         "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", 
         "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", 
         "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]
    )
    search_party = st.sidebar.selectbox("Party", ["", "DEM", "REP", "IND", "LIB", "GRE"])
    
    # Add Project 2025 policy area filter
    st.sidebar.header("Filter by Policy Area")
    selected_policy_area = st.sidebar.selectbox(
        "Project 2025 Policy Area",
        ["All"] + list(PROJECT_2025_POLICIES.keys())
    )
    
    # Add alignment score filter
    st.sidebar.header("Filter by Alignment Score")
    min_alignment = st.sidebar.slider("Minimum Alignment Score", 0, 100, 0)
    max_alignment = st.sidebar.slider("Maximum Alignment Score", 0, 100, 100)
    
    if st.sidebar.button("Search"):
        with st.spinner("Searching for politicians..."):
            candidates = fetch_candidate_data(search_name, search_state, search_party)
            
            if candidates and candidates.get("results"):
                st.subheader("Search Results")
                
                # Get congressional data for alignment analysis
                bills_data = fetch_congressional_data()
                
                # Calculate alignment scores for all candidates
                candidates_with_scores = []
                for candidate in candidates.get("results"):
                    # Map FEC candidate_id to congressional member_id (bioguide_id)
                    member_id = candidate.get("bioguide_id")
                    
                    # Calculate alignment score
                    alignment = calculate_project2025_alignment(member_id, bills_data)
                    
                    if alignment["status"] == "success":
                        overall_score = alignment["overall_score"]
                        category_scores = alignment["category_scores"]
                        
                        # Apply filters
                        include_candidate = True
                        
                        # Apply alignment score filter
                        if overall_score < min_alignment or overall_score > max_alignment:
                            include_candidate = False
                        
                        # Apply policy area filter
                        if selected_policy_area != "All" and selected_policy_area in category_scores:
                            category_score = category_scores[selected_policy_area]
                            if category_score < min_alignment or category_score > max_alignment:
                                include_candidate = False
                        
                        if include_candidate:
                            candidates_with_scores.append({
                                "Name": candidate.get("name"),
                                "Party": candidate.get("party"),
                                "State": candidate.get("state"),
                                "Office": candidate.get("office_full"),
                                "Overall Alignment": f"{overall_score:.1f}%",
                                "ID": candidate.get("candidate_id"),
                                "bioguide_id": member_id,
                                "alignment_data": alignment
                            })
                
                if candidates_with_scores:
                    # Display candidates in a table
                    candidates_df = pd.DataFrame(candidates_with_scores)
                    display_cols = ["Name", "Party", "State", "Office", "Overall Alignment"]
                    st.dataframe(candidates_df[display_cols])
                    
                    # Allow user to select a candidate for detailed analysis
                    selected_candidate = st.selectbox(
                        "Select a candidate for detailed analysis",
                        candidates_df["Name"].tolist()
                    )
                    
                    if selected_candidate:
                        selected_row = candidates_df[candidates_df["Name"] == selected_candidate].iloc[0]
                        candidate_id = selected_row["ID"]
                        member_id = selected_row["bioguide_id"]
                        alignment_data = selected_row["alignment_data"]
                        
                        # Display tabs for different analyses
                        tab1, tab2, tab3, tab4 = st.tabs([
                            "Project 2025 Alignment", 
                            "Voting Record", 
                            "Campaign Finance", 
                            "Finance-Voting Correlation"
                        ])
                        
                        with tab1:
                            st.header("Project 2025 Alignment Analysis")
                            
                            # Display overall score with gauge chart
                            overall_score = alignment_data["overall_score"]
                            
                            # Create three columns
                            col1, col2, col3 = st.columns([1, 2, 1])
                            
                            with col1:
                                # Display overall score as a metric
                                st.metric(
                                    "Overall Alignment Score", 
                                    f"{overall_score:.1f}%",
                                    delta=None
                                )
                            
                            with col2:
                                # Create a gauge chart for overall score
                                fig = go.Figure(go.Indicator(
                                    mode="gauge+number",
                                    value=overall_score,
                                    domain={'x': [0, 1], 'y': [0, 1]},
                                    title={'text': "Project 2025 Alignment"},
                                    gauge={
                                        'axis': {'range': [0, 100]},
                                        'bar': {'color': "darkblue"},
                                        'steps': [
                                            {'range': [0, 25], 'color': "lightblue"},
                                            {'range': [25, 50], 'color': "cyan"},
                                            {'range': [50, 75], 'color': "royalblue"},
                                            {'range': [75, 100], 'color': "darkblue"}
                                        ],
                                        'threshold': {
                                            'line': {'color': "red", 'width': 4},
                                            'thickness': 0.75,
                                            'value': overall_score
                                        }
                                    }
                                ))
                                
                                fig.update_layout(
                                    height=250,
                                    margin=dict(l=20, r=20, t=50, b=20),
                                )
                                
                                st.plotly_chart(fig, use_container_width=True)
                            
                            with col3:
                                # Add interpretation
                                if overall_score > 75:
                                    st.info("Strong alignment with Project 2025")
                                elif overall_score > 50:
                                    st.info("Moderate alignment with Project 2025")
                                elif overall_score > 25:
                                    st.info("Limited alignment with Project 2025")
                                else:
                                    st.info("Strong opposition to Project 2025")
                            
                            # Display category scores with radar chart
                            st.subheader("Alignment by Policy Area")
                            
                            # Prepare data for radar chart
                            categories = list(alignment_data["category_scores"].keys())
                            scores = list(alignment_data["category_scores"].values())
                            
                            # Create radar chart
                            fig = go.Figure()
                            
                            fig.add_trace(go.Scatterpolar(
                                r=scores,
                                theta=categories,
                                fill='toself',
                                name='Alignment Score'
                            ))
                            
                            fig.update_layout(
                                polar=dict(
                                    radialaxis=dict(
                                        visible=True,
                                        range=[0, 100]
                                    )
                                ),
                                showlegend=False
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Display detailed analysis
                            st.subheader("Detailed Analysis")
                            st.markdown(alignment_data["analysis"])
                        
                        with tab2:
                            st.header("Voting Record")
                            
                            # Get member votes
                            member_votes_data = fetch_member_votes(member_id)
                            
                            if member_votes_data["status"] == "success":
                                member_votes = member_votes_data["votes"]
                                
                                # Get bills data
                                bills = fetch_congressional_data()["bills"]
                                
                                # Create a dataframe of votes
                                votes_data = []
                                for bill in bills:
                                    bill_id = bill["bill_id"]
                                    if bill_id in member_votes:
                                        vote = member_votes[bill_id]
                                        
                                        # Determine if vote aligns with Project 2025
                                        alignment = bill["project2025_alignment"]
                                        is_aligned = (alignment == "aligned" and vote == "yes") or (alignment == "opposed" and vote == "no")
                                        
                                        votes_data.append({
                                            "Bill ID": bill_id.upper(),
                                            "Title": bill["title"],
                                            "Categories": ", ".join(bill["categories"]),
                                            "Project 2025": alignment.capitalize(),
                                            "Vote": vote.upper(),
                                            "Aligned": "Yes" if is_aligned else "No"
                                        })
                                
                                votes_df = pd.DataFrame(votes_data)
                                
                                # Add filter for policy area
                                vote_policy_filter = st.selectbox(
                                    "Filter by Policy Area",
                                    ["All"] + list(PROJECT_2025_POLICIES.keys()),
                                    key="vote_policy_filter"
                                )
                                
                                if vote_policy_filter != "All":
                                    votes_df = votes_df[votes_df["Categories"].str.contains(vote_policy_filter)]
                                
                                # Display votes
                                st.dataframe(votes_df, use_container_width=True)
                                
                                # Display vote summary
                                st.subheader("Voting Summary")
                                
                                # Calculate summary statistics
                                total_votes = len(votes_df)
                                aligned_votes = len(votes_df[votes_df["Aligned"] == "Yes"])
                                alignment_pct = (aligned_votes / total_votes * 100) if total_votes > 0 else 0
                                
                                # Create summary metrics
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Total Votes", total_votes)
                                with col2:
                                    st.metric("Aligned with Project 2025", aligned_votes)
                                with col3:
                                    st.metric("Alignment Percentage", f"{alignment_pct:.1f}%")
                                
                                # Create a pie chart of aligned vs. non-aligned votes
                                fig = px.pie(
                                    values=[aligned_votes, total_votes - aligned_votes],
                                    names=["Aligned with Project 2025", "Not Aligned"],
                                    title="Vote Alignment with Project 2025"
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.warning("No voting record available for this member")
                        
                        with tab3:
                            st.header("Campaign Finance")
                            with st.spinner("Loading contribution data..."):
                                contributions = fetch_candidate_contributions(candidate_id)
                                if contributions and contributions.get("results"):
                                    contrib_df = pd.DataFrame([
                                        {
                                            "Contributor": c.get("contributor_name"),
                                            "Amount": c.get("contribution_receipt_amount"),
                                            "Date": c.get("contribution_receipt_date"),
                                            "Employer": c.get("contributor_employer")
                                        }
                                        for c in contributions.get("results")
                                    ])
                                    
                                    # Display contributions
                                    st.dataframe(contrib_df)
                                    
                                    # Show visualizations
                                    st.subheader("Top Contributors")
                                    top_contrib = contrib_df.groupby("Contributor")["Amount"].sum().reset_index().sort_values("Amount", ascending=False).head(10)
                                    
                                    fig = px.bar(
                                        top_contrib,
                                        x="Contributor",
                                        y="Amount",
                                        title="Top 10 Contributors"
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                    
                                    # Map contributions to Project 2025 policy areas
                                    st.subheader("Contributions by Policy Area")
                                    
                                    # Analyze each contribution for policy interests
                                    policy_contributions = {policy: 0 for policy in PROJECT_2025_POLICIES.keys()}
                                    policy_contributions["other"] = 0
                                    
                                    for _, contrib in contrib_df.iterrows():
                                        interests = map_donor_interests_to_project2025(contrib)
                                        amount = contrib["Amount"]
                                        
                                        if interests:
                                            # Distribute amount equally among interests
                                            amount_per_interest = amount / len(interests)
                                            for interest in interests:
                                                if interest in policy_contributions:
                                                    policy_contributions[interest] += amount_per_interest
                                                else:
                                                    policy_contributions["other"] += amount_per_interest
                                        else:
                                            policy_contributions["other"] += amount
                                    
                                    # Create dataframe for visualization
                                    policy_contrib_df = pd.DataFrame({
                                        "Policy Area": list(policy_contributions.keys()),
                                        "Amount": list(policy_contributions.values())
                                    })
                                    
                                    # Sort by amount
                                    policy_contrib_df = policy_contrib_df.sort_values("Amount", ascending=False)
                                    
                                    # Create bar chart
                                    fig = px.bar(
                                        policy_contrib_df,
                                        x="Policy Area",
                                        y="Amount",
                                        title="Contributions by Project 2025 Policy Area"
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.warning("No contribution data available")
                        
                        with tab4:
                            st.header("Finance-Voting Correlation")
                            
                            # Analyze correlation between contributions and voting patterns
                            with st.spinner("Analyzing correlation..."):
                                correlation = match_contributions_to_votes(candidate_id, member_id, fetch_congressional_data())
                                
                                if correlation["status"] == "success":
                                    # Display overall correlation
                                    st.metric(
                                        "Overall Donor-Voting Correlation", 
                                        f"{correlation['overall_correlation']:.1f}%",
                                        help="Higher percentage indicates stronger alignment between donor interests and voting patterns"
                                    )
                                    
                                    # Display correlation by policy area
                                    st.subheader("Correlation by Policy Area")
                                    
                                    # Prepare data for visualization
                                    policy_data = []
                                    for policy, data in correlation["interest_alignment"].items():
                                        if data["total_contributions"] > 0:
                                            policy_data.append({
                                                "Policy Area": policy.capitalize(),
                                                "Alignment": data["alignment_percentage"],
                                                "Contributions": data["total_contributions"],
                                                "Size": np.log1p(data["total_contributions"])  # Log scale for better visualization
                                            })
                                    
                                    policy_corr_df = pd.DataFrame(policy_data)
                                    
                                    if not policy_corr_df.empty:
                                        # Create bubble chart
                                        fig = px.scatter(
                                            policy_corr_df,
                                            x="Contributions",
                                            y="Alignment",
                                            size="Size",
                                            color="Policy Area",
                                            hover_name="Policy Area",
                                            size_max=60,
                                            title="Contribution Amount vs. Voting Alignment by Policy Area"
                                        )
                                        
                                        fig.update_layout(
                                            xaxis_title="Contribution Amount ($)",
                                            yaxis_title="Voting Alignment with Project 2025 (%)"
                                        )
                                        
                                        st.plotly_chart(fig, use_container_width=True)
                                        
                                        # Display detailed breakdown
                                        st.subheader("Detailed Breakdown by Policy Area")
                                        
                                        for policy, data in correlation["interest_alignment"].items():
                                            if data["total_contributions"] > 0:
                                                with st.expander(f"{policy.capitalize()} - ${data['total_contributions']:,.2f} - {data['alignment_percentage']:.1f}% Alignment"):
                                                    st.write(f"**Voting Alignment:** {data['alignment_percentage']:.1f}%")
                                                    st.write(f"**Total Contributions:** ${data['total_contributions']:,.2f}")
                                                    
                                                    if data["contributors"]:
                                                        st.write("**Top Contributors:**")
                                                        contrib_df = pd.DataFrame(data["contributors"]).sort_values("amount", ascending=False)
                                                        st.dataframe(contrib_df)
                                    else:
                                        st.info("No policy-specific contribution data available for analysis")
                                else:
                                    st.warning("Unable to analyze correlation between contributions and voting patterns")
                else:
                    st.warning("No candidates found matching your search and filter criteria")
            else:
                st.warning("No candidates found matching your search criteria")
    
    # Display Project 2025 policy information
    st.sidebar.markdown("---")
    st.sidebar.header("Project 2025 Policy Areas")
    
    policy_expander = st.sidebar.expander("View Policy Areas")
    with policy_expander:
        for policy, details in PROJECT_2025_DETAILS.items():
            st.markdown(f"**{policy.capitalize()}**")
            st.write(details["description"])
            st.markdown("---")

if __name__ == "__main__":
    main()
