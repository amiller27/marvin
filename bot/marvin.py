import asyncio
import discord
import logging
import random
import re
import schedule
import yaml

logger = logging.getLogger('marvin')
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

file_handler = logging.FileHandler(filename='marvin.log', encoding='UTF-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

food = {
    "Downtown": [
        "Las Velas",
        "DiBella's",
        "The Yard",
        "The Simple Greek",
        "Sienna Mercato",
        "Ptimanti"
    ],
    "North Shore": [
        "Burgatory",
    ],
    "Oakland": [
        "Chipotle",
        "Fuel and Fuddle"
        "Primanti",
        "CHiKN",
        "Stack'd",
        "Oishii",
        "Pie Express",
        "Mad Mex",
    ],
    "Shadyside": ["Mad Mex", "Noodlehead", "Choolah", "Uncle Sams"],
    "The Strip": [
        "Gaucho",
        "Smallman Galley",
        "Roland's",
        "Kaya",
        "Bella Notte",
        "Pennsylvania Market",
        "Pho Van",
        "Cinderlands"
    ],
    "Southside": ["Hofbrauhaus"],
    "Station Square": ["Hard Rock Cafe"],
}


def get_rando_place():
    area, places = random.choice(list(food.items()))
    place = random.choice(places)
    return area, place


async def reminder_loop(client):
    await client.wait_until_ready()
    while not client.is_closed():
        schedule.run_pending()
        await asyncio.sleep(30)


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

        schedule.every().monday.at('16:00').do(
                lambda : client.loop.create_task(
                    client.post_primantis_reminder()))
        logger.info('Done startup')

    async def on_message(self, message):
        logger.info('Got message %s', repr(message))

        if re.match(r'^how make', message.content.lower()):
            logger.info('Matched \'how make\'')
            await message.channel.send('You wouldn\'t understand.')

        if re.search(r'any\s+ideas', message.content.lower()):
            logger.info('Matched \'any ideas\'')
            await message.channel.send(
                    'I have a million ideas. They all point to certain death.')

        if re.match(r'^where get food', message.content.lower()):
            logger.info('Matched \'where get\'')
            area, place = get_rando_place()
            await message.channel.send(f'You could go to {place} in {area}')

    async def post_primantis_reminder(self):
        logger.info('Posting Primanti\'s reminder')
        await self.channel_map['アニメ_execs'].send('It\'s Primanti\'s Monday.')
        area, place = get_rando_place()
        await self.channel_map['アニメ_execs'].send(f'You could go to {place} in {area}.')


if __name__ == '__main__':
    with open('config.yaml') as f:
        config = yaml.safe_load(f)

    client = Marvin()
    client.loop.create_task(reminder_loop(client))
    client.run(config['token'])
