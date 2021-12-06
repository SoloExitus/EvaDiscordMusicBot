import asyncio
import os
import datetime
import re
import random
import typing
from enum import Enum

import discord
import wavelink
from discord.ext import commands

URL_REG = re.compile(r'https?://(?:www\.)?.+')

class AlreadyConnectedToChannel(commands.CommandError):
    pass

class NoVoiceChannel(commands.CommandError):
    pass

class QueueIsEmpty(commands.CommandError):
    pass


class NoTracksFound(commands.CommandError):
    pass


class PlayerIsAlreadyPaused(commands.CommandError):
    pass


class NoMoreTracks(commands.CommandError):
    pass


class NoPreviousTracks(commands.CommandError):
    pass


class InvalidRepeatMode(commands.CommandError):
    pass


class VolumeTooLow(commands.CommandError):
    pass


class VolumeTooHigh(commands.CommandError):
    pass


class MaxVolume(commands.CommandError):
    pass


class MinVolume(commands.CommandError):
    pass


class NoLyricsFound(commands.CommandError):
    pass


class InvalidEQPreset(commands.CommandError):
    pass


class NonExistentEQBand(commands.CommandError):
    pass


class EQGainOutOfBounds(commands.CommandError):
    pass


class InvalidTimeString(commands.CommandError):
    pass

class RepeatMode(Enum):
    OFF = 0
    TRACK = 1
    QUEUE = 2

class Queue:
    def __init__(self):
        self._queue = []
        self.position = 0
        self.skip = False
        self.repeat_mode = RepeatMode.OFF

    @property
    def is_empty(self):
        return not self._queue

    @property
    def current_track(self):
        if not self._queue:
            raise QueueIsEmpty

        if self.position <= len(self._queue) - 1:
            return self._queue[self.position]

        return None

    @property
    def upcoming(self):
        if not self._queue:
            raise QueueIsEmpty

        return self._queue[self.position + 1:]

    @property
    def history(self):
        if not self._queue:
            raise QueueIsEmpty

        return self._queue[:self.position]

    @property
    def length(self):
        return len(self._queue)

    def add(self, track):
        self._queue.append(track)

    def get_next(self):
        if not self._queue:
            raise QueueIsEmpty

        if self.repeat_mode == RepeatMode.TRACK:
            return self._queue[self.position]

        self.position += 1

        if self.position < 0:
            return None
        elif self.position > len(self._queue) - 1:
            if self.repeat_mode == RepeatMode.QUEUE:
                self.position = 0
            else:
                return None

        return self._queue[self.position]

    def next(self):
        if self.repeat_mode == RepeatMode.TRACK and not self.skip:
            self.skip = False
            return

        self.position += 1

        if self.position > len(self._queue) - 1:
            if self.repeat_mode == RepeatMode.QUEUE:
                self.position = 0

    def shuffle(self):
        if not self._queue:
            raise QueueIsEmpty

        upcoming = self.upcoming
        random.shuffle(upcoming)
        self._queue = self._queue[:self.position + 1]
        self._queue.extend(upcoming)

    def set_repeat_mode(self, mode):
        if mode == "off":
            self.repeat_mode = RepeatMode.OFF
        elif mode == "track":
            self.repeat_mode = RepeatMode.TRACK
        elif mode == "queue":
            self.repeat_mode = RepeatMode.QUEUE

    def clear(self):
        self._queue.clear()
        self.position = 0

class Player(wavelink.Player):
    """Custom wavelink Player class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = Queue()
        self.wait = None

    async def playback(self):
        # await self.track info
        track = self.queue.current_track

        if track is not None:
            self.cancelWait()
            return await self.play(track)

        await self.stop()
        self.startWait()


    async def waittask(self):
        await asyncio.sleep(420)
        await self.teardown()

    async def play_next(self):
            track = self.queue.get_next()
            if track is not None:
                await self.play(track)
                #await self.track info

    def startWait(self):
        self.cancelWait()

        self.wait = asyncio.create_task(self.waittask())

    def cancelWait(self):
        if self.wait:
            self.wait.cancel()
            self.wait = None



    async def playnext(self):
            self.queue.next()
            await self.playback()

    async def teardown(self):
        try:
            await self.destroy()
        except KeyError:
            pass


class Music(commands.Cog, wavelink.WavelinkMixin):
    """Music Cog."""

    def __init__(self, client: commands.Bot):
        self.client = client
        self.wavelink = wavelink.Client(bot=client)
        self.client.loop.create_task(self.start_nodes())

    async def start_nodes(self):
        await self.client.wait_until_ready()

        nodes = {
            "MAIN": {
                "host": os.getenv('lavalink_host'),
                "port": 2333,
                "rest_uri": os.getenv('lavalink_uri'),
                "password": os.getenv('lavalink_password'),
                "identifier": "MAIN",
                "region": "europe",
            }
        }

        for node in nodes.values():
            await self.wavelink.initiate_node(**node)




    async def cog_check(self, ctx):
        """Cog wide check, which disallows commands in DMs."""
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send('Music commands are not available in Private Messages.')
            return False

        return True

    # Cog Listeners  -----------------------------

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        members = getattr(before.channel, 'members', None)
        if members:
            if not [m for m in members if not m.bot]:
                player: Player = self.wavelink.get_player(member.guild.id, cls=Player)
                await player.teardown()

    # Wavelink Listeners ---------------------------------

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node):
        print(f" Wavelink node `{node.identifier}` ready.")

    @wavelink.WavelinkMixin.listener('on_track_stuck')
    @wavelink.WavelinkMixin.listener('on_track_end')
    @wavelink.WavelinkMixin.listener('on_track_exception')
    async def on_player_stop(self, node: wavelink.Node, payload):
        await payload.player.playnext()

    # Commands ------------------------------------------

    @commands.command(name="connect", aliases=["join"])
    async def connect(self, ctx):
        channel = ctx.author.voice.channel

        if not channel:
            return await ctx.reply('No channel to join. Please either specify a valid channel or join one.')

        player: Player = self.wavelink.get_player(ctx.guild.id, cls=Player)

        if player.is_connected and player.channel_id == channel.id:
            return

        await player.connect(channel.id)
        await ctx.send(f'Connecting to **`{channel.name}`**', delete_after=15)
        player.startWait()

    @commands.command(name="disconnect", aliases=["leave","out"])
    async def disconnect(self, ctx):
        player: Player = self.wavelink.get_player(ctx.guild.id, cls=Player)
        player.queue.clear()
        await player.teardown()
        await ctx.send("Disconnected.")

    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx: commands.Context, *, query: str):
        """Play or queue a song with the given query."""
        player: Player = self.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.is_connected:
            await self.connect(ctx)

        query = query.strip('<>')
        if not URL_REG.match(query):
            query = f'ytsearch:{query}'

        tracks = await self.wavelink.get_tracks(query)
        if not tracks:
            return await ctx.send('No songs were found with that query. Please try again.', delete_after=15)

        if isinstance(tracks, wavelink.TrackPlaylist):
            for track in tracks.tracks:
                player.queue.add(track)

            await ctx.send(f'```ini\nAdded the playlist {tracks.data["playlistInfo"]["name"]}'
                           f' with {len(tracks.tracks)} songs to the queue.\n```', delete_after=15)
        else:
            track = tracks[0]
            player.queue.add(track)
            await ctx.send(f'```ini\nAdded {track.title} to the Queue\n```', delete_after=15)

        if not player.is_playing and not player.queue.is_empty:
            await player.playback()

    @commands.command(name="pause")
    async def pause(self, ctx):
        player: Player = self.wavelink.get_player(ctx.guild.id, cls=Player)

        player.startWait()

        if player.is_paused:
            raise PlayerIsAlreadyPaused

        await player.set_pause(True)
        await ctx.reply("Playback paused.")

    @commands.command(name="resume")
    async def resume(self, ctx):
        player: Player = self.wavelink.get_player(ctx.guild.id, cls=Player)

        # if not player.is_paused:
        #     raise PlayerIsAlreadyPaused
        player.cancelWait()
        await player.set_pause(False)
        await ctx.reply("Playback resumed.")

    @commands.command(name="stop")
    async def stop(self, ctx):
        player: Player = self.wavelink.get_player(ctx.guild.id, cls=Player)
        player.queue.clear()
        await player.stop()
        await ctx.reply("Playback stopped.")

    @commands.command(name="queue", aliases=["q"])
    async def queue(self, ctx):
        player: Player = self.wavelink.get_player(ctx.guild.id, cls=Player)

        player.startWait()

        if not player.is_connected:
            return await ctx.reply('I am not connected to any channel.', delete_after=20)

        if player.queue.is_empty:
            return await ctx.send('There are no songs currently in the queue.', delete_after=20)

        upcoming = player.queue.upcoming
        fmt = '\n'.join(f'**`{str(song)}`**' for song in upcoming[:10])
        embed = discord.Embed(title=f'Upcoming - Next {len(upcoming)}', description=fmt)
        await ctx.send(embed=embed)

    @commands.command(name="repeat", aliases=["loop"])
    async def repeat(self, ctx, mode: str):
        if mode not in ("off", "track", "queue"):
            raise InvalidRepeatMode

        player: Player = self.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.is_connected:
            return await ctx.reply('I am not connected to any channel.', delete_after=20)

        player.queue.set_repeat_mode(mode)
        await ctx.send(f"The repeat mode has been set to {mode}.")

    @commands.command(name="next", aliases=["skip"])
    async def skip(self, ctx):
        player: Player = self.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.is_connected:
            return

        if not player.is_playing:
            return await ctx.send('I am not currently playing anything!', delete_after=15)

        player.skip = True
        await player.stop()
        await ctx.reply('Skipping the song!', delete_after=15)

    @commands.command(name="song", aliases=["np"])
    async def playing(self, ctx):
        player: Player = self.wavelink.get_player(ctx.guild.id, cls=Player)

        player.startWait()

        if not player.is_playing:
            return await ctx.reply("Nothing is playing.")

        embed = discord.Embed(
            title="Now playing",
            colour=ctx.author.colour,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_author(name="Playback Information")
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
        embed.add_field(name="Track title", value=player.queue.current_track.title, inline=False)
        embed.add_field(name="Artist", value=player.queue.current_track.author, inline=False)

        position = divmod(player.position, 60000)
        length = divmod(player.queue.current_track.length, 60000)
        embed.add_field(
            name="Position",
            value=f"{int(position[0])}:{round(position[1] / 1000):02}/{int(length[0])}:{round(length[1] / 1000):02}",
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.command(name="clear")
    async def clear(self, ctx):
        player: Player = self.wavelink.get_player(ctx.guild.id, cls=Player)

        if not player.is_connected:
            return await ctx.reply('There are no songs currently in the queue.', delete_after=20)

        player.queue.clear()
        await ctx.reply("Queue cleared.")

    @commands.command()
    async def volume(self, ctx, *, vol: int):
        """Set the player volume."""
        player: Player = self.wavelink.get_player(ctx.guild.id, cls=Player)

        vol = min(max(vol, 0), 100)

        await player.set_volume(vol)
        await ctx.send(f'Setting the player volume to `{vol}`')

def setup(client):
    client.add_cog(Music(client))