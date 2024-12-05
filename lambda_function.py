import json
import datetime
import requests

import os
from dotenv import load_dotenv
load_dotenv()

TEST_MODE = os.getenv("TEST_MODE") == "True"
SESSION_COOKIE = os.getenv("SESSION_COOKIE")
PRIVATE_LEADERBOARD_CODE = os.getenv("PRIVATE_LEADERBOARD_CODE")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

def parse_data(data):
    members = []
    
    # Filter data for fields needed to display leaderboard
    for member_data in data['members'].values():
        member = {
            'id': member_data['id'],
            'local_score': member_data['local_score'],
            'name': member_data['name'],
            'completion_day_level': {}
        }
        
        for day, data in member_data['completion_day_level'].items():
            member['completion_day_level'][int(day)] = len(data.keys())
        
        members.append(member)
    
    # Sort data by local score descending
    members.sort(key=lambda member: member['local_score'], reverse=True)
    return members

# AWS Lambda Function
def lambda_handler(event, context):
    # Get data depending on TEST_MODE
    data = {}
    if TEST_MODE or event.get('TEST_MODE', False):
        f = open('test_data.json', 'r')
        data = json.load(f)
        f.close()
    else:
        cookies = {
            'session': SESSION_COOKIE
        }
        r = requests.get(f'https://adventofcode.com/2024/leaderboard/private/view/{PRIVATE_LEADERBOARD_CODE}.json', cookies=cookies)
        data = r.json()

    # Parse data
    members = parse_data(data)
    # Calculate max member name length for padding
    max_member_len = max([len(member['name']) for member in members])

    # Keep track of message length for Discord's 2000 character limit
    DISCORD_CHARACTER_LIMIT = 2000
    message = ""

    # Start ANSI code block
    message += "```ansi\n"
    message += "[1;40m"

    day = datetime.date.today().day - 1

    # Write leaderboard header
    message += "[37m"
    message += f"{f'Leaderboard for Day {day}':^{35 + max_member_len}}"
    message += "\n"

    # Write days header
    message += "[0;40;30m"
    for _ in range(17):
        message += " "

    if day >= 10:
        message += "[32m"
    for i in range(10, 26):
        message += str(i // 10)

    for i in range(max_member_len + 2):
        message += " "
    message += "\n"

    message += "[30m"
    for _ in range(8):
        message += " "

    message += "[32m"
    for i in range(1, 26):
        message += str(i % 10)
        if i == day:
            message += "[30m"

    for i in range(max_member_len + 2):
        message += " "
    message += "\n"

    # Write member rankings
    for i, member in enumerate(members):
        # Write score
        member_text = ""
        member_text += "[37m"
        member_text += f"{(i + 1):>2}) "

        member_text += f"{member['local_score']:>3} "

        # Write stars
        prev_level = -1
        for i in range(1, day + 1):
            day_level = member['completion_day_level'].get(i, 0)
            if prev_level != day_level:
                match day_level:
                    case 0:
                        member_text += "[30m"
                    case 1:
                        member_text += "[36m"
                    case 2:
                        member_text += "[33m"
                prev_level = day_level
            member_text += "*"

        for i in range(day + 1, 28):
            member_text += " "

        # Write name
        member_text += "[37m"
        member_text += f"{member['name']:<{max_member_len}}"
        member_text += "\n"

        # Break if message length will exceed Discord's 2000 character limit
        if len(message) + len(member_text) > DISCORD_CHARACTER_LIMIT - 3:
            break
        message += member_text
    message += "```"
    
    # Send to webhook
    message_data = {
        'content': message,
        'username': 'Advent of Code Leaderboard'
    }
    requests.post(WEBHOOK_URL, json=message_data)