#!/usr/bin/env python3

import asyncio
import datetime
import discord
import logging
import random
import re
import schedule
import sys
import threading
import traceback
import yaml

logger = logging.getLogger('MARVIN')
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

file_handler = logging.FileHandler(filename='marvin.log', encoding='UTF-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass

stdout_logger = logger.getChild('STDOUT')
sl = StreamToLogger(stdout_logger, logging.INFO)
sys.stdout = sl

stderr_logger = logger.getChild('STDERR')
sl = StreamToLogger(stderr_logger, logging.ERROR)
sys.stderr = sl

food = {
    "Downtown": [
        "Las Velas",
        "DiBella's",
        "The Yard",
        "The Simple Greek",
        "Sienna Mercato",
        "Primanti\'s",
    ],
    "North Shore": [
        "Burgatory",
    ],
    "Oakland": [
        "Chipotle",
        "Fuel and Fuddle",
        "Primanti\'s",
        "CHiKN",
        "Stack'd",
        "Oishii",
        "Pie Express",
        "Mad Mex",
        "Pad Thai Noodle",
    ],
    "Shadyside/East Liberty/Squirrel Hill": [
        "Mad Mex",
        "Noodlehead",
        "Choolah",
        "Uncle Sam\'s",
    ],
    "The Strip": [
        "Gaucho",
        "Smallman Galley",
        "Roland's",
        "Kaya",
        "Bella Notte",
        "Pennsylvania Market",
        "Pho Van",
        "Cinderlands",
    ],
    "Southside": ["Hofbrauhaus"],
    "Station Square": ["Hard Rock Cafe"],
}


def get_rando_place():
    tuples = sum(([(area_places[0], place) for place in area_places[1]]
              for area_places in food.items()), [])
    area, place = random.choice(tuples)
    return area, place


async def reminder_loop(client):
    await client.wait_until_ready()
    while not client.is_closed():
        schedule.run_pending()
        await asyncio.sleep(30)

MESSAGE_CACHE_LENGTH_SECONDS = 5*60
deleted_message_cache = []
def clean_message_cache():
    deleted_message_cache.sort(key=lambda msg: msg.created_at)
    for i in reversed(range(len(deleted_message_cache))):
        msg = deleted_message_cache[i]
        logger.info(f'Checking message {msg}')
        if msg.created_at \
                < datetime.datetime.now() \
                - datetime.timedelta(seconds=MESSAGE_CACHE_LENGTH_SECONDS):
            logger.info('Deleting')
            del deleted_message_cache[i]


class Marvin(discord.Client):
    async def on_ready(self):
        logger.info('Starting...')
        self.channel_map = {}
        for guild in self.guilds:
            if guild.id != 586416345294569474:
                logger.info('Adding guild %s with id %s', guild, guild.id)
                for channel in guild.channels:
                    logger.info('Adding channel %s with id %s', channel, channel.id)
                    self.channel_map[channel.name] = channel
            else:
                logger.info('Adding debug guild %s', guild)
                for channel in guild.channels:
                    if channel.name == 'general':
                        logger.info('Adding debug channel %s with id %s', channel, channel.id)
                        self.debug_channel = channel

        self.reminder_lock = threading.Lock()
        self.last_reminder = datetime.datetime.fromtimestamp(0)

        schedule.every().monday.at('17:00').do(
                lambda : client.loop.create_task(
                    client.post_primantis_reminder()))
        logger.info('Done startup')

    async def on_message_delete(self, message):
        logger.info('Got deleted message %s', repr(message))
        deleted_message_cache.append(message)
        clean_message_cache()

    async def on_message_edit(self, before, after):
        logger.info('Got edited message %s', repr(after))
        if before.content == after.content:
            logger.info('Message not changed')
        else:
            logger.info('Content changed from {} to {}'.format(
                before.content, after.content))
            deleted_message_cache.append(before)
            clean_message_cache()


    async def on_message(self, message):
        if message.author.name == 'Marvin' and message.author.bot:
            logger.info('Got message from self: %s', repr(message))
        else:
            logger.info('Got message %s with contents %s', repr(message), repr(message.content))

        if message.content == '👀':
            logger.info('Matched :eyes:')
            clean_message_cache()
            for msg in deleted_message_cache:
                if msg.channel == message.channel:
                    await message.channel.send('{} said: {}'.format(
                        msg.author.nick if msg.author.nick else msg.author.name,
                        msg.content))

        if re.match(r'^how make', message.content.lower()):
            logger.info('Matched \'how make\'')
            await message.channel.send('You wouldn\'t understand.')

        if re.search(r'any\s+ideas', message.content.lower()):
            logger.info('Matched \'any ideas\'')
            await message.channel.send(
                    'I have a million ideas. They all point to certain death.')

        if re.match(r'^where get food', message.content.lower()):
            logger.info('Matched \'where get\'')
            match_area = re.match(r'^where get food in (.*)', message.content.lower())
            if match_area:
                target_area = match_area[1]
                if target_area not in map(str.lower, food.keys()):
                    await message.channel.send(f'{target_area} isn\'t a place')
                    return
                area, place = get_rando_place()
                while area.lower() != target_area:
                    area, place = get_rando_place()
            else:
                area, place = get_rando_place()
            await message.channel.send(f'You could go to {place} in {area}')

        if re.match(r'^marvin\s+log$', message.content.lower()) and message.author.id == config['admin']:
            logger.info('Matched \'logs\'')
            with open('marvin.log', encoding='utf-8') as f:
                log_text = f.read()

            # Only send last 1900 characters, don't want to overflow message
            # size
            await message.channel.send(log_text[-1900:])

    async def post_primantis_reminder(self):
        with self.reminder_lock:
            if (datetime.datetime.now() - self.last_reminder) > datetime.timedelta(hours=1):
                logger.info('Posting Primanti\'s reminder')
                await self.channel_map['アニメ_execs'].send('It\'s Primanti\'s Monday.')
                area, place = get_rando_place()
                await self.channel_map['アニメ_execs'].send(f'You could go to {place} in {area}.')
                self.last_reminder = datetime.datetime.now()


if __name__ == '__main__':
    with open('config.yaml') as f:
        config = yaml.safe_load(f)

    client = Marvin()
    client.loop.create_task(reminder_loop(client))
    client.run(config['token'])
