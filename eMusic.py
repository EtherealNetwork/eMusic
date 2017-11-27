import os
import sys
import math
import yaml
import asyncio
import discord
from datetime import datetime
from discord.ext import commands
from PlayerPlaylist import PlayerPlaylist

properties_file_path = 'emusic_properties.yml'
exception_log_path = 'emusic_exception_log.txt'

BOT_NAME = ''
BOT_ID = ''
BOT_TOKEN = ''
CMD_PREFIX = ''
bot = None

SERVER_PLAYERS = {}
SERVER_QUEUES = {}
SERVER_PLAYLISTS = {}


# Get needed bot info from the properties file.
def initialize_bot():
    if os.path.isfile(properties_file_path):
        properties = yaml.load(open(properties_file_path))

        if len(properties) < 4:
            print('Missing properties; bot may not work properly.')

        global BOT_NAME, BOT_ID, BOT_TOKEN, CMD_PREFIX, bot
        BOT_NAME = properties['bot-name']
        BOT_ID = properties['bot-id']
        BOT_TOKEN = properties['bot-token']
        CMD_PREFIX = properties['cmd-prefix']

        # Disable default help command to use custom one later.
        bot = commands.Bot(command_prefix=CMD_PREFIX, help_attrs={'disabled': True})
    else:
        exception = 'Properties file not found at: {}\nExiting.'.format(properties_file_path)
        print(exception)
        exception_log_write(exception)
        sys.exit()


# Method for logging exceptions.
def exception_log_write(exception):
    with open(exception_log_path, 'a') as exception_log:
        exception_log.write('{} | {}'.format(datetime.now(), exception))


initialize_bot()


# ----- Events -----


@bot.event
async def on_ready():
    global BOT_NAME
    if BOT_NAME is None or BOT_NAME == '':
        BOT_NAME = bot.user.name

    print('Successfully logged in as:', bot.user)
    print("Using {} as the bot's name.".format(BOT_NAME))
    print('Add me to a server via: https://discordapp.com/api/oauth2/authorize?client_id={}&scope=bot&permissions=1'
          .format(BOT_ID))


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Allows the use of a custom help command.
    if message.content.lower() == '?' + BOT_NAME.lower() or message.content.lower() == CMD_PREFIX + BOT_NAME.lower():
        await show_help(message.author)
        return

    # Needed for any @bot.command() methods to work.
    await bot.process_commands(message)


# ----- Commands -----


@bot.command(pass_context=True, aliases=['connect'])
async def join(ctx):
    command = ctx.message.content
    cmd_args = command.split(" ")
    author = ctx.message.author
    server = ctx.message.server

    if server is None:
        voice_client = await get_voice_client(author, None, None)
        if voice_client is None:
            await bot.say('Unable to connect to a voice channel.')
        else:
            await bot.say('{} connected to: {}'.format(BOT_NAME, voice_client.channel.name))
    elif len(cmd_args) == 1:
        voice_client = await get_voice_client(author, server, None)
        if voice_client is None:
            await bot.say('Unable to connect to a voice channel.')
        else:
            await bot.say('{} connected to: {}'.format(BOT_NAME, voice_client.channel.name))
    else:
        arg_channel = ''
        for arg in cmd_args[1:]:
            arg_channel += arg + ' '
        arg_channel = arg_channel[:-1]

        voice_client = await get_voice_client(author, server, arg_channel)
        if voice_client is None:
            await bot.say('Unable to connect to voice channel **{}**.'.format(arg_channel))
        else:
            await bot.say('{} connected to: {}'.format(BOT_NAME, voice_client.channel.name))


@bot.command(pass_context=True, aliases=['disconnect'])
async def leave(ctx):
    author = ctx.message.author
    server = ctx.message.server
    if server is None:
        for s in bot.servers:
            for channel in s.channels:
                if author in channel.voice_members:
                    voice_client = bot.voice_client_in(s)
                    if voice_client is None:
                        await bot.say('{} is not currently connected to a voice channel.'.format(BOT_NAME))
                    else:
                        await voice_client.disconnect()
                        await bot.say('{} disconnected from: {}'.format(BOT_NAME, voice_client.channel.name))
    elif bot.is_voice_connected(server):
        voice_client = None
        for vc in list(bot.voice_clients):
            if vc.server == ctx.message.server:
                voice_client = vc
                break
        if voice_client is None:
            await bot.say('{} is not currently connected to a voice channel.'.format(BOT_NAME))
        else:
            await voice_client.disconnect()
            await bot.say('{} disconnected from: {}'.format(BOT_NAME, voice_client.channel.name))
    else:
        await bot.say('{} is not currently connected to a voice channel.'.format(BOT_NAME))


@bot.command(pass_context=True, aliases=['start'])
async def play(ctx):
    command = ctx.message.content
    cmd_args = command.split(" ")

    global SERVER_PLAYERS

    if len(cmd_args) <= 1:
        server = ctx.message.server.id
        if server in SERVER_PLAYERS:
            player = SERVER_PLAYERS[server]
            if player is None:
                await bot.say("-play [Audio Source Link]")
            elif not player.is_playing():
                player.resume()
                await bot.say('Playback has resumed.', embed=player_info(player))
            else:
                await bot.say("-play [Audio Source Link]")
    else:
        author = ctx.message.author
        server = ctx.message.server
        if server is None:
            server = get_voice_connected_server(author)
        voice_client = await get_voice_client(author, server, None)
        if voice_client is not None:
            # list= is YouTube and /sets/ is SoundCloud
            if 'list=' in cmd_args[1] or '/sets/' in cmd_args[1]:
                global SERVER_PLAYLISTS
                message = await bot.say('Downloading playlist data. This could take a while (about 1 sec per song).')
                if server.id in SERVER_PLAYLISTS:
                    SERVER_PLAYLISTS[server.id].append(PlayerPlaylist(message.channel, voice_client, cmd_args[1]))
                else:
                    SERVER_PLAYLISTS[server.id] = []
                    SERVER_PLAYLISTS[server.id].append(PlayerPlaylist(message.channel, voice_client, cmd_args[1]))
            else:
                try:
                    player = await create_player(voice_client, cmd_args[1])
                except commands.CommandInvokeError:
                    await bot.say('Unable to find a video from the source: **{}**'.format(cmd_args[1]))
                    return
                queued = await queue_player(player, server.id)
                if queued:
                    await bot.say('__**Added to queue:**__', embed=player_info(player))
                else:
                    await bot.say('Unable to queue the specified song.')
        else:
            await bot.say('Unable to queue the specified song.')


@bot.command(pass_context=True, aliases=['nowplaying', 'playing'])
async def info(ctx):
    server = ctx.message.server
    if server is None:
        server = get_voice_connected_server(ctx.message.author)
    server_id = server.id
    if server_id not in SERVER_PLAYERS or SERVER_PLAYERS[server_id] is None:
        await bot.say('There is nothing playing.')
    else:
        await bot.say('__**Now Playing:**__ ', embed=player_info(SERVER_PLAYERS[server_id]))


@bot.command(pass_context=True, aliases=['list', 'playlist', 'page'])
async def queue(ctx):
    command = ctx.message.content
    cmd_args = command.split(" ")

    server = ctx.message.server
    if server is None:
        server = get_voice_connected_server(ctx.message.author)
    server_id = server.id

    if server_id in SERVER_QUEUES:
        titles = []
        total_duration = 0
        for player in SERVER_QUEUES[server_id]:
            if player.duration is not None:
                total_duration += player.duration
            if player.title is not None:
                titles.append(player.title)
            else:
                titles.append(player.url)

        if len(titles) == 0:
            await bot.say('Nothing is currently queued.')
        else:
            if len(cmd_args) <= 1:
                em = await queue_em_info(titles, total_duration, 1)
                await bot.say(embed=em)
            else:
                page = 1
                try:
                    page = int(cmd_args[1])
                except ValueError:
                    await bot.say('Invalid page number; defaulting to page 1.')
                em = await queue_em_info(titles, total_duration, page)
                await bot.say(embed=em)
    else:
        await bot.say('Nothing is currently queued.')


@bot.command(pass_context=True, aliases=['next', 'pass'])
async def skip(ctx):
    server = ctx.message.server
    if server is None:
        server = get_voice_connected_server(ctx.message.author)
    server_id = server.id

    global SERVER_PLAYERS
    if server_id in SERVER_PLAYERS:
        SERVER_PLAYERS[server_id].stop()
    await asyncio.sleep(2)  # Lets queue_check() update player.
    if SERVER_PLAYERS[server_id] is None or SERVER_PLAYERS[server_id].is_done():
        await bot.say('No more songs in queue.')
    else:
        await bot.say('Song skipped.')
        await bot.say('__**Now Playing:**__', embed=player_info(SERVER_PLAYERS[server_id]))


@bot.command(pass_context=True, aliases=['unpause', 'resume'])
async def pause(ctx):
    server = ctx.message.server
    if server is None:
        server = get_voice_connected_server(ctx.message.author)
    server_id = server.id

    global SERVER_PLAYERS
    if server_id in SERVER_PLAYERS:
        player = SERVER_PLAYERS[server_id]
        if player.is_playing():
            player.pause()
            await bot.say('Playback has been paused.')
        else:
            player.resume()
            await bot.say('Playback has resumed.', embed=player_info(player))
    else:
        await bot.say('There is currently nothing playing to paused.')


@bot.command(pass_context=True, aliases=['end'])
async def stop(ctx):
    server = ctx.message.server
    if server is None:
        server = get_voice_connected_server(ctx.message.author)
    server_id = server.id

    global SERVER_PLAYERS
    if server_id in SERVER_PLAYERS:
        player = SERVER_PLAYERS[server_id]
        if player.is_playing():
            SERVER_PLAYERS[server_id].stop()
            await bot.say('Playback has been stopped.')
        else:
            await bot.say('Playback is already stopped or paused.')
    else:
        await bot.say('There is currently nothing playing to stop.')


@bot.command(pass_context=True, aliases=['cancel', 'ditch'])
async def remove(ctx):
    server = ctx.message.server
    if server is None:
        server = get_voice_connected_server(ctx.message.author)
    server_id = server.id

    global SERVER_QUEUES
    if server_id in SERVER_QUEUES:
        cmd_args = ctx.message.content.split(' ')
        if len(SERVER_QUEUES[server_id]) == 0:
            await bot.say('There is no queue to remove from.')
            return
        if len(cmd_args) > 1:
            try:
                player = SERVER_QUEUES[server_id].pop(int(cmd_args[1]) - 1)
                await bot.say('__**Removed from queue:**__', embed=player_info(player))
            except KeyError:
                await bot.say('**{}** is not a valid number.'.format(cmd_args[1]))
                return
        else:
            player = SERVER_QUEUES[server_id].pop()
            await bot.say('__**Removed from queue:**__', embed=player_info(player))
    else:
        await bot.say('There is no queue to remove from.')


@bot.command(pass_context=True, aliases=['empty'])
async def clear(ctx):
    server = ctx.message.server
    if server is None:
        server = get_voice_connected_server(ctx.message.author)
    server_id = server.id

    global SERVER_QUEUES
    if server_id in SERVER_QUEUES:
        if len(SERVER_QUEUES[server_id]) == 0:
            await bot.say('There was no queue to clear.')
        else:
            SERVER_QUEUES[server_id] = []
            await bot.say('The queue has been cleared.')
    else:
        await bot.say('There was no queue to clear.')


@bot.command(pass_context=True, aliases=['restart'])
async def reset(ctx):
    await bot.say('{} is resetting; this may take a moment.'.format(BOT_NAME))
    server = ctx.message.server
    if server is None:
        server = get_voice_connected_server(ctx.message.author)
    server_id = server.id

    global SERVER_PLAYERS, SERVER_QUEUES
    if server_id in SERVER_QUEUES:
        SERVER_QUEUES[server_id] = []
        await bot.say('Queue has been cleared.')
    if server_id in SERVER_PLAYERS:
        voice_client = bot.voice_client_in(server)
        if SERVER_PLAYERS[server_id] is not None and SERVER_PLAYERS[server_id].is_playing():
            SERVER_PLAYERS[server_id].stop()
            await bot.say('Playback has been stopped.')
        if voice_client is not None:
            voice_channel_name = voice_client.channel.name
            await voice_client.disconnect()
            await bot.say('{} has disconnected from **{}**.'.format(BOT_NAME, voice_channel_name))
        SERVER_PLAYERS[server_id] = None
        await bot.say('Player has been cleared.')
    await bot.say('{} has finished resetting.'.format(BOT_NAME))


# ----- Functions -----


# Returns the VoiceClient of the bot; otherwise returns None.
async def get_voice_client(author, server, channel):
    if channel is None:
        if server is None:
            for s in bot.servers:
                for channel in s.channels:
                    if author in channel.voice_members:
                        if not bot.is_voice_connected(s):
                            return await bot.join_voice_channel(channel)
                        else:
                            await bot.voice_client_in(s).move_to(channel)
                            return bot.voice_client_in(s)

        voice_channel = None
        for vc in server.channels:
            if author in vc.voice_members:
                voice_channel = vc

        if voice_channel is None:
            await bot.send_message(author, 'User is not in a voice channel. Unable to connect.')
            return None
        else:
            if bot.is_voice_connected(server):
                voice_client = None
                for vc in list(bot.voice_clients):
                    if vc.server == server:
                        voice_client = vc
                        break
                if voice_client is None:
                    return await bot.join_voice_channel(voice_channel)
                else:
                    await voice_client.move_to(voice_channel)
                    return bot.voice_client_in(voice_channel.server)
            else:
                return await bot.join_voice_channel(voice_channel)
    else:
        voice_channel = None
        for vc in server.channels:
            if vc.type is discord.ChannelType.voice:
                if vc.name.lower() == channel.lower():
                    voice_channel = vc
                    break

        if voice_channel is None:
            await bot.send_message(author, 'Unable to find voice channel **{}** to connect to.'.format(channel))
            return None
        else:
            if bot.is_voice_connected(server):
                voice_client = None
                for vc in list(bot.voice_clients):
                    if vc.server == server:
                        voice_client = vc
                        break
                if voice_client is None:
                    return await bot.join_voice_channel(voice_channel)
                else:
                    return await voice_client.move_to(voice_channel)
            else:
                return await bot.join_voice_channel(voice_channel)


# Returns a StreamPlayer created with youtube-dl.
async def create_player(voice_client, source):
    youtube_dl_options = dict(
        format="bestaudio/best",
        extractaudio=True,
        audioformat="mp3",
        noplaylist=True,
        default_search="auto",
        quiet=True,
        nocheckcertificate=True,
    )

    player = await voice_client.create_ytdl_player(
        source,
        ytdl_options=youtube_dl_options,
        before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    )

    return player


# Queues the playlist and sends the progress to Discord.
async def create_player_list(playlist):
    channel = playlist.channel
    voice_client = playlist.voice_client
    server = voice_client.server

    content = 'Queueing songs from playlist: 0/{}'.format(len(playlist.urls))
    message = await bot.send_message(channel, content)
    count = 0
    for url in playlist.urls:
        player = await create_player(voice_client, url)
        count += 1
        new_message = 'Queueing songs from playlist: {}/{}'.format(count, len(playlist.urls))
        await bot.edit_message(message, new_message)
        queued = await queue_player(player, server.id)
        if not queued:
            await bot.send_message(channel, 'Unable to queue {} from the playlist.'.format(player.url))
    await bot.say('Finished queueing playlist.')


# Returns the Server with the bot that the user is connected to; otherwise returns None.
def get_voice_connected_server(user):
    for s in bot.servers:
        for channel in s.channels:
            if user in channel.voice_members:
                return s
    return None


# Adds the Player to the queue. Starts it if there is currently nothing playing.
async def queue_player(player, server_id):
    if player is not None:
        global SERVER_PLAYERS
        if server_id not in SERVER_PLAYERS or SERVER_PLAYERS[server_id] is None:
            SERVER_PLAYERS[server_id] = player
            SERVER_PLAYERS[server_id].start()
        else:
            global SERVER_QUEUES
            if server_id not in SERVER_QUEUES:
                SERVER_QUEUES[server_id] = []
            SERVER_QUEUES[server_id].append(player)
        return True
    else:
        return False


# Returns the player info as an embed.
def player_info(player):
    title = player.title
    if title is None:
        title = player.url

    uploader = player.uploader
    if uploader is None:
        uploader = ''

    url = player.url
    if 'http' not in url:
        url = ''

    em = discord.Embed(title=title, description='Uploader: {}'.format(uploader), url=url, colour=0x0000ff)
    vid_duration = player.duration
    if vid_duration is not None:
        em.add_field(name='Length:', value='{0}:{1:0>2}'.format(int(vid_duration / 60), int(vid_duration % 60)))

    return em


# Returns the queue info as an embed with pagination.
async def queue_em_info(titles, total_duration, page):
    end = page * 5
    if end <= 0:
        end = 5
    if end > len(titles):
        end = len(titles)
    start = end - 5
    if start < 0:
        start = 0

    to_embed = []
    for i in range(start, end):
        to_embed.append(titles[i])

    current_queue = '__**Current Queue ({}):**__'.format(len(titles))
    m, s = divmod(total_duration, 60)
    h, m = divmod(m, 60)
    playback_time = 'Total playback time: {0:0>2}:{1:0>2}:{2:0>2}'.format(
        h,  # Hours
        m,  # Minutes
        s  # Seconds
    )
    em = discord.Embed(title=current_queue, description=playback_time, colour=0x0000ff)

    queue_pos = start + 1
    for title in to_embed:
        em.add_field(name=title, value='Queue position: {}'.format(queue_pos), inline=False)
        queue_pos += 1

    footer = 'Page: {}/{}'.format(math.ceil(end / 5), math.ceil(len(titles) / 5))
    em.set_footer(text=footer)
    return em


# Shows the available commands.
async def show_help(member):
    em = discord.Embed(title='eMusic Bot', description='Plays music from media links.', colour=0x0000ff)
    em.add_field(name='{}join | {}connect'.format(CMD_PREFIX, CMD_PREFIX),
                 value='Joins the voice channel of the user if possible.',
                 inline=False)
    em.add_field(name='{}leave | {}disconnect'.format(CMD_PREFIX, CMD_PREFIX),
                 value='Leaves the current voice channel if the bot is in one.',
                 inline=False)
    em.add_field(name='{}play | {}start [Audio Source Link]'.format(CMD_PREFIX, CMD_PREFIX),
                 value='Starts playback from a link to an audio source. Also resumes playback.',
                 inline=False)
    em.add_field(name='{}pause | {}unpause | {}resume'.format(CMD_PREFIX, CMD_PREFIX, CMD_PREFIX),
                 value='Pauses/Resumes playback.',
                 inline=False)
    em.add_field(name='{}skip | {}next | {}pass'.format(CMD_PREFIX, CMD_PREFIX, CMD_PREFIX),
                 value='Skips to the next song in the queue if available.',
                 inline=False)
    em.add_field(name='{}nowplaying | {}info'.format(CMD_PREFIX, CMD_PREFIX),
                 value="Displays the current song's info if possible.",
                 inline=False)
    em.add_field(name='{}queue | {}list'.format(CMD_PREFIX, CMD_PREFIX),
                 value='Displays the current queue if there is one.',
                 inline=False)
    em.add_field(name='{}stop | {}end'.format(CMD_PREFIX, CMD_PREFIX),
                 value='Stops playback; keeps queue.',
                 inline=False)
    em.add_field(name='{}remove | {}cancel | {}ditch [Position]'.format(CMD_PREFIX, CMD_PREFIX, CMD_PREFIX),
                 value='Removes the song in the queue at the given position. If no position is given, '
                       'the last song will be removed.',
                 inline=False)
    em.add_field(name='{}clear | {}empty'.format(CMD_PREFIX, CMD_PREFIX),
                 value='Clears the queue.',
                 inline=False)
    em.add_field(name='{}reset | {}restart'.format(CMD_PREFIX, CMD_PREFIX),
                 value='Stops playback, clears the queue, and disconnects from the VoiceChannel.',
                 inline=False)
    em.add_field(name='?{} | {}{}'.format(BOT_NAME, CMD_PREFIX, BOT_NAME),
                 value='Messages the user a list of commands.',
                 inline=False)
    await bot.send_message(member, embed=em)


# Background task that tells the bot to go to the next song if the previous one has finished.
async def queue_check():
    await bot.wait_until_ready()

    global SERVER_PLAYERS, SERVER_QUEUES, SERVER_PLAYLISTS

    while not bot.is_closed:
        for server, player in SERVER_PLAYERS.items():
            if player is not None:
                if player.is_done():
                    player.stop()
                    try:
                        if server in SERVER_QUEUES:
                            SERVER_PLAYERS[server] = SERVER_QUEUES[server].pop(0)
                            SERVER_PLAYERS[server].start()
                    except IndexError:
                        SERVER_PLAYERS[server] = None
        await asyncio.sleep(1)


# Background task that updates the queue list.
async def playlist_check():
    await bot.wait_until_ready()

    global SERVER_PLAYLISTS

    while not bot.is_closed:
        for server in SERVER_PLAYLISTS:
            if len(SERVER_PLAYLISTS[server]) > 0:
                if SERVER_PLAYLISTS[server][0].completed:
                    playlist = SERVER_PLAYLISTS[server].pop(0)
                    await create_player_list(playlist)
        await asyncio.sleep(1)


# ----- Run Bot -----


try:
    bot.loop.create_task(queue_check())
    bot.loop.create_task(playlist_check())
    bot.run(BOT_TOKEN)
except Exception as e:
    exception_log_write(e)
    pass
