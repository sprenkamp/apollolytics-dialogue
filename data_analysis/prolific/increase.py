#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_URL = "https://api.prolific.com/api/v1/studies"
STUDY_ID = "6876522ea4279ef40ea3bd86" #critical 
API_TOKEN = os.getenv("PROLIFIC_API_KEY")
MAX_CAP = int(os.getenv("PROLIFIC_MAX_CAP", "5"))  # absolute ceiling
INCREMENT = int(os.getenv("PROLIFIC_INCREMENT", "1"))

HEADERS = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json"
}

def get_study():
    resp = requests.get(f"{API_URL}/{STUDY_ID}/", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

def get_submissions():
    """Get all submissions for the study"""
    resp = requests.get(f"{API_URL}/{STUDY_ID}/submissions/", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

def patch_study(new_cap):
    data = {"total_available_places": new_cap}
    resp = requests.patch(f"{API_URL}/{STUDY_ID}/", json=data, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()

def main():
    study = get_study()
    current = study["total_available_places"]
    
    # Get submissions to count completed participants
    submissions_data = get_submissions()
    submissions = submissions_data.get("results", [])
    
    # Count approved AND awaiting review submissions (both are completed)
    completed = len([s for s in submissions if s.get("status") in ["APPROVED", "AWAITING REVIEW"]])
    
    # Print submission statuses for debugging
    statuses = {}
    for sub in submissions:
        status = sub.get("status", "UNKNOWN")
        statuses[status] = statuses.get(status, 0) + 1
    
    print(f"Study Status Summary:")
    print(f"  Current cap: {current}")
    print(f"  Completed participants: {completed}")
    print(f"  Max cap: {MAX_CAP}")
    print(f"  Increment: {INCREMENT}")
    print(f"  Submission breakdown: {statuses}")


    
    if completed >= current and current < MAX_CAP:
        new_cap = min(current + INCREMENT, MAX_CAP)
        print(f"\n✅ Increasing cap from {current} to {new_cap}")
        patch_study(new_cap)
    else:
        print(f"\n❌ No increase needed: {completed} completed < {current} current cap")

if __name__ == "__main__":
    main()
