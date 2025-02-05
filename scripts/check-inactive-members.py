#!/usr/bin/env python3
import requests
import csv

# Before running, need to download the CSV data from
# https://opentelemetry.devstats.cncf.io/d/9/developer-activity-counts-by-repository-group-table?orgId=1&var-period_name=Last%202%20years
# and store it in the scripts directory as activity.csv

# Replace with your GitHub organization name and personal access token
TOKEN = 'your-personal-access-token'

# GitHub API endpoint
API_URL = f'https://api.github.com/orgs/open-telemetry/members'

# Headers for authentication
HEADERS = {
    'Authorization': f'token {TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

def get_all_members(api_url):
    members = []
    while api_url:
        response = requests.get(api_url, headers=HEADERS)
        response_data = response.json()
        members.extend(response_data)
        api_url = None
        if 'Link' in response.headers:
            links = response.headers['Link'].split(', ')
            for link in links:
                if 'rel="next"' in link:
                    api_url = link[link.find('<') + 1:link.find('>')]
                    break
    return members

# Get the list of organization members
members = get_all_members(API_URL)
member_usernames = {member['login'] for member in members}
member_usernames_lower = {username.lower() for username in member_usernames}

# Read the activity.csv file
active_usernames = set()
with open('scripts/activity.csv', mode='r') as file:
    csv_reader = csv.reader(file)
    for row in csv_reader:
        active_usernames.add(row[1])

# Find members who are not in activity.csv (case insensitive comparison)
inactive_members_lower = member_usernames_lower - active_usernames

# Map back to original case-sensitive usernames
inactive_members = {username for username in member_usernames if username.lower() in inactive_members_lower}

# Sort the inactive members case insensitively
sorted_inactive_members = sorted(inactive_members, key=lambda s: s.lower())

print("Members not in activity.csv:")
for inactive_member in sorted_inactive_members:
    print(inactive_member)
