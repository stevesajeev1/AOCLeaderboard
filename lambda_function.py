import json
import datetime
import requests

from PIL import Image, ImageDraw, ImageFont
import io

from discord import SyncWebhook, File

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
    # Total Length: max_member_len + 35

    width = 36 + max_member_len
    height = 2 + len(members)
    FONT_WIDTH = 8
    FONT_HEIGHT = 20
    
    # Colors
    BG = (15, 15, 35)
    WHITE = (204, 204, 204)
    GREEN = (0, 153, 0)
    GREY = (51, 51, 51)
    GOLD = (255, 255, 102)
    SILVER = (153, 153, 204)
    
    image = Image.new('RGB', (width * FONT_WIDTH, height * FONT_HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('SourceCodePro-Regular.ttf', 14)
    
    day = datetime.date.today().day - 1
    
    line = 0
    # Write leaderboard header
    leaderboard_header = f"Leaderboard for Day {day}"
    draw.text(((width - len(leaderboard_header)) * FONT_WIDTH / 2, line * FONT_HEIGHT), leaderboard_header, WHITE, font)
    line += 1
    
    # Write days header
    days_header_color = GREEN
    for i in range(1, 26):
        if i >= 10:
            draw.text(((8 + i) * FONT_WIDTH, line * FONT_HEIGHT), str(i // 10), days_header_color, font)
        draw.text(((8 + i) * FONT_WIDTH, (line + 1) * FONT_HEIGHT), str(i % 10), days_header_color, font)
        if i == day:
            days_header_color = GREY
    line += 2

    # Write member rankings
    for i, member in enumerate(members):
        # Write rank and score
        member_score = f"{(i + 1):>2}) {member['local_score']:>3}"
        draw.text((FONT_WIDTH, line * FONT_HEIGHT), member_score, WHITE, font)
        
        # Write stars
        offset = 0
        prev_level = -1
        star_color = None
        star_text = ""
        for i in range(1, day + 1):
            day_level = member['completion_day_level'].get(i, 0)
            if prev_level != day_level:
                if prev_level != -1:
                    draw.text(((9 + offset) * FONT_WIDTH, line * FONT_HEIGHT), star_text, star_color, font)
                    offset += len(star_text)
                    star_text = ""
                    pass
                match day_level:
                    case 0:
                        star_color = GREY
                    case 1:
                        star_color = SILVER
                    case 2:
                        star_color = GOLD
                prev_level = day_level
            star_text += "*"
        draw.text(((9 + offset) * FONT_WIDTH, line * FONT_HEIGHT), star_text, star_color, font)
        
        # Write name
        draw.text((35 * FONT_WIDTH, line * FONT_HEIGHT), member['name'], WHITE, font)
        
        line += 1
    
    # Send to webhook
    wh = SyncWebhook.from_url(WEBHOOK_URL)
    with io.BytesIO() as image_binary:
        image.save(image_binary, 'PNG')
        image_binary.seek(0)
        wh.send(username='Advent of Code Leaderboard', file=File(fp=image_binary, filename='leaderboard.png'))

lambda_handler(None, None)