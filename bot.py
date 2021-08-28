import discord
import os
from discord.ext import commands

from dotenv import load_dotenv
load_dotenv()

client = commands.Bot(command_prefix='!', Intents=discord.Intents.all())

for filename in os.listdir('./cogs'):
   if filename.endswith('.py'):
       client.load_extension(f'cogs.{filename[:-3]}')


@client.event
async def on_ready():
    print(f'{client.user} is online!')

client.run(os.getenv('token'))