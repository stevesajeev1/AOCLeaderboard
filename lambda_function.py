import json
from datetime import datetime
import requests

from PIL import Image, ImageDraw, ImageFont
import io

from discord import SyncWebhook, File

import os
from dotenv import load_dotenv
load_dotenv()

# Load environment variables
TEST_MODE = os.getenv("TEST_MODE") == "True"
SESSION_COOKIE = os.getenv("SESSION_COOKIE")
PRIVATE_LEADERBOARD_CODE = os.getenv("PRIVATE_LEADERBOARD_CODE")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Setup image parameters
FONT_WIDTH = 8
FONT_HEIGHT = 20

# Colors
BG = (15, 15, 35)
WHITE = (204, 204, 204)
GREEN = (0, 153, 0)
GREY = (51, 51, 51)
GOLD = (255, 255, 102)
SILVER = (153, 153, 204)

# Get current day
DAY = datetime.today().day - 1

def parse_data(data):
    """Parses JSON API data, filtering for relevant fields"""
    members = []
    
    # Filter data for fields needed to display leaderboard
    for member_data in data['members'].values():
        member = {
            'local_score': member_data['local_score'],
            'name': member_data['name'],
            'completion_day_level': {},
            'day_level_time': (
                member_data['completion_day_level'].get(str(DAY), {}).get('1', {}).get('get_star_ts'),
                member_data['completion_day_level'].get(str(DAY), {}).get('2', {}).get('get_star_ts'),
            )
        }
        
        for day, data in member_data['completion_day_level'].items():
            member['completion_day_level'][int(day)] = len(data.keys())
        
        members.append(member)

    return members

def generate_overall_leaderboard(members):
    """Generates image for the overall leaderboard"""
    # Sort members by local score
    members = sorted(members, key=lambda member: member['local_score'], reverse=True)

    # Calculate max member name length for padding
    max_member_len = max([len(member['name']) for member in members])

    width = 36 + max_member_len
    height = 2 + len(members)
    
    image = Image.new('RGB', (width * FONT_WIDTH, height * FONT_HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('SourceCodePro-Regular.ttf', 14)
    
    line = 0
    # Write leaderboard header
    leaderboard_header = f"Overall Leaderboard"
    draw.text(((width - len(leaderboard_header)) * FONT_WIDTH / 2, line * FONT_HEIGHT), leaderboard_header, WHITE, font)
    line += 1
    
    # Write days header
    days_header_color = GREEN
    for i in range(1, 26):
        if i >= 10:
            draw.text(((8 + i) * FONT_WIDTH, line * FONT_HEIGHT), str(i // 10), days_header_color, font)
        draw.text(((8 + i) * FONT_WIDTH, (line + 1) * FONT_HEIGHT), str(i % 10), days_header_color, font)
        if i == DAY:
            days_header_color = GREY
    line += 2

    # Write member rankings
    for i, member in enumerate(members):
        # Write rank and score
        member_score = f"{(i + 1):>2}) {member['local_score']:>4}"
        draw.text((FONT_WIDTH, line * FONT_HEIGHT), member_score, WHITE, font)
        
        # Write stars
        offset = 0
        prev_level = -1
        star_color = None
        star_text = ""
        for i in range(1, DAY + 1):
            day_level = member['completion_day_level'].get(i, 0)
            if prev_level != day_level:
                if prev_level != -1:
                    draw.text(((10 + offset) * FONT_WIDTH, line * FONT_HEIGHT), star_text, star_color, font)
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
        draw.text(((10 + offset) * FONT_WIDTH, line * FONT_HEIGHT), star_text, star_color, font)
        
        # Write name
        draw.text((35 * FONT_WIDTH, line * FONT_HEIGHT), member['name'], WHITE, font)
        
        line += 1
    
    return image

def generate_day_leaderboard(members):
    """Generates image for the daily leaderboard"""
    def sort(member):
        """Ranking is based on time to solve Part 2 then Part 1"""
        max_timestamp = float("inf")
        score = [max_timestamp, max_timestamp]
        if member['day_level_time'][1] is not None:
            score[0] = member['day_level_time'][1]
        if member['day_level_time'][0] is not None:
            score[1] = member['day_level_time'][0]
        return score
    
    def parse_timestamps(timestamps):
        """Generates time strings from timestamps"""
        def format_td(timedelta):
            """Formats timedelta"""
            hours, remainder = divmod(timedelta.total_seconds(), 60*60)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours - 5):02}:{int(minutes):02}:{int(seconds):02}"

        midnight = datetime.now().replace(day=DAY, hour=0, minute=0, second=0, microsecond=0)
        
        time_1 = "N/A"
        if timestamps[0] is not None:
            td = datetime.fromtimestamp(timestamps[0]) - midnight
            time_1 = format_td(td)
        
        time_2 = "N/A"
        if timestamps[1] is not None:
            td = datetime.fromtimestamp(timestamps[1]) - midnight
            time_2 = format_td(td)
            
        return f"{time_1:>8}   {time_2:>8}"

    # Sort members by time taken to solve day problem
    members = sorted(members, key=sort)
    # Filter members to only those that have attempted
    members = list(filter(lambda member: member['day_level_time'] != (None, None), members))
    
    # No solutions :(
    if len(members) == 0:
        image = Image.new('RGB', (51 * FONT_WIDTH, 4 * FONT_HEIGHT), BG)
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('SourceCodePro-Regular.ttf', 14)
        
        leaderboard_header = f"Leaderboard for Day {DAY}"
        draw.text(((51 - len(leaderboard_header)) * FONT_WIDTH / 2, 0), leaderboard_header, WHITE, font)
        
        text = f"No one solved Day {DAY} :("
        draw.text(((51 - len(text)) * FONT_WIDTH / 2, 2 * FONT_HEIGHT), text, WHITE, font)
        
        return image
    
    # Calculate max member name length for padding
    max_member_len = max([len(member['name']) for member in members])
    
    width = 32 + max_member_len
    height = 3 + len(members)
    
    image = Image.new('RGB', (width * FONT_WIDTH, height * FONT_HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('SourceCodePro-Regular.ttf', 14)
    
    line = 0
    # Write leaderboard header
    leaderboard_header = f"Leaderboard for Day {DAY}"
    draw.text(((width - len(leaderboard_header)) * FONT_WIDTH / 2, line * FONT_HEIGHT), leaderboard_header, WHITE, font)
    line += 1
    
    # Write time header
    draw.text((8 * FONT_WIDTH, line * FONT_HEIGHT), "-Part 1-", SILVER, font)
    draw.text((19 * FONT_WIDTH, line * FONT_HEIGHT), "-Part 2-", GOLD, font)
    line += 1
    
    draw.text((12 * FONT_WIDTH, line * FONT_HEIGHT), "Time", SILVER, font)
    draw.text((23 * FONT_WIDTH, line * FONT_HEIGHT), "Time", GOLD, font)
    line += 1

    # Write member rankings
    for i, member in enumerate(members):
        # Write rank
        rank = f"{(i + 1):>2})"
        draw.text((FONT_WIDTH, line * FONT_HEIGHT), rank, WHITE, font)
        
        # Write times
        times = parse_timestamps(member['day_level_time'])
        draw.text((8 * FONT_WIDTH, line * FONT_HEIGHT), times, WHITE, font)
        
        # Write name
        draw.text((31 * FONT_WIDTH, line * FONT_HEIGHT), member['name'], WHITE, font)
        
        line += 1
    
    return image

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

    # Generate day leaderboard
    day_leaderboard = generate_day_leaderboard(members)
    
    # Generate overall leaderboard
    overall_leaderboard = generate_overall_leaderboard(members)
    
    # Send to webhook
    wh = SyncWebhook.from_url(WEBHOOK_URL)

    with io.BytesIO() as day_image_binary:
        day_leaderboard.save(day_image_binary, 'PNG')
        day_image_binary.seek(0)
        wh.send(username='Advent of Code Leaderboard', file=File(fp=day_image_binary, filename=f'day{DAY}_leaderboard.png'))
    
    with io.BytesIO() as overall_image_binary:
        overall_leaderboard.save(overall_image_binary, 'PNG')
        overall_image_binary.seek(0)
        wh.send(username='Advent of Code Leaderboard', file=File(fp=overall_image_binary, filename=f'day{DAY}_overall.png'))