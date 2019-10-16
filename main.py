from discord.ext import commands
import discord
import asyncio
import json
import emojis
import bottoken
import dbl
from io import StringIO
import sys
import datetime

# Initialising and defining the bot
bot = commands.Bot(owner_id=311268449181630464,
                   description="If a message is extraordinarily funny,\nreact with"
                               " a specified emoji and it gets posted in your channel\n"
                               "of wish.",
                   command_prefix=["!"],
                   help_command=None)


class System(commands.Cog):

    def __init__(self, discord_bot):
        self.bot = discord_bot

    @commands.command()
    @commands.is_owner()
    async def exec(self, ctx):
        """Executes the given code in the discord message"""

        command = ctx.message.content.split("```")[1]

        # redirects the output
        old_out = sys.stdout
        result = StringIO()
        sys.stdout = result

        exec(command)  # troubleshooting

        # redirects the output again
        sys.stdout = old_out

        # gets the result of the command
        result_string = result.getvalue()
        await ctx.send(result_string)

        return 0

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx):
        """Reloads an extension"""

        ext_name = ctx.message.content.split()[-1]
        bot.reload_extension(ext_name)  # troubleshooting
        await ctx.send(f"{ext_name} was successfully reloaded")

        return 0

    @commands.command()
    @commands.is_owner()
    async def gc(self, ctx):
        """Counts the guilds the bot is in"""

        await ctx.send(f"The bot is currently in {len(bot.guilds)} guilds")

        return 0

class DiscordBotsOrgAPI(commands.Cog):
    """Handles interactions with the top.gg API"""

    def __init__(self, discord_bot):
        self.bot = discord_bot
        self.token = bottoken.dbltoken()
        self.dblpy = dbl.DBLClient(self.bot, self.token)
        self.updating = self.bot.loop.create_task(self.update_stats())

    async def update_stats(self):
        """This function runs every 30 minutes to automatically update the server count"""
        while not self.bot.is_closed():
            try:
                await self.dblpy.post_guild_count()
            except Exception:
                pass
            await asyncio.sleep(1800)

        return 0

class Core(commands.Cog):

    def __init__(self, discord_bot):
        self.bot = discord_bot

    @commands.command()
    @commands.bot_has_permissions(send_messages=True,
                                  embed_links=True)
    @commands.has_permissions(manage_messages=True)
    async def trophy(self, ctx, message):
        """Triggers the bot manually to generate an embed

        The message must either be:
        -   a valid ID
        -   a valid message link"""

        with open("Settings/Settings.json", "r") as file:
            settings_trophy = json.load(file)

        message = await commands.MessageConverter().convert(ctx, message)

        if settings_trophy[f"{ctx.guild.id}"]["channel_id"] == 0:

            try:
                await ctx.send("The quotation channel has not been defined,\n"
                           "to do this, type ``!setchannel`` in the desired channel.\n"
                           "(Manage server permissions required)")
            except discord.Forbidden:
                return 0

        else:
            await embed_message(ctx.guild, message)

        return 0

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def invite(self, ctx):
        """Shows the invite link for this bot if you like it"""
        try:
            await ctx.send(
            "My invite link is https://discordapp.com/api/oauth2/authorize?client_id=625112945881382912&permissions=18432&scope=bot")
        except discord.Forbidden:
            return 0

        return 0

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def vote(self, ctx):
        """Shows the link to vote for this bot if you really like it"""
        try:
            await ctx.send("My link to vote is https://discordbots.org/bot/625112945881382912")
        except discord.Forbidden:
            return 0

        return 0

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def help(self, ctx):
        """Help message and tutorial"""

        try:
            await ctx.send("This bot lets you react to a certain message with an emoji (default :trophy:) and post it into a "
                           "custom starboard channel. You are completely free in customization whatsoever.\n"
                           "You find the link to my help page by clicking 'watch' on my profile or by using this link: https://www.twitch.tv/quotebot_5599\n\n"
                           ":warning: If it doesnt work when reacting to a message, make sure you checked the following:\n"
                           "- First, make sure the bot is able to __**VIEW**__ the channel it is supposed to create embeds of (general chat, etc)\n"
                           "- Second, make sure that the one who created the message did not react to it. On default, the bot ignores it but you can"
                           " change that behaviour\n"
                           "- Third, make sure you are not writing and reacting in the channel the bot is posting the embeds. If you react there, the"
                           " reactions get ignored too\n\n"
                           "If you still have troubles setting up the bot, please refer to the support server (can be found with ``!vote``, you dont need"
                           " to vote, I just dont want to advertise my server here)")
        except discord.Forbidden:
            return 0

        return 0


class Customizing(commands.Cog):

    def __init__(self, discord_bot):
        self.bot = discord_bot

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.cooldown(1, 2, commands.BucketType.default)
    async def setchannel(self, ctx):
        """Lets a user define the quotes channel

        Usage
        !setchannel
        in the desired channel"""

        settings_setchannel = load_settings()

        settings_setchannel[f"{ctx.guild.id}"]["channel_id"] = ctx.channel.id

        with open("Settings/Settings.json", "w") as file:
            json.dump(settings_setchannel, file, indent=4, sort_keys=True)

        try:
            await ctx.send(f"New quotes channel successfully set to {ctx.channel.mention}")
        except discord.Forbidden:
            return 0


        return 0

    @commands.command()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.cooldown(1, 2, commands.BucketType.default)
    async def setemoji(self, ctx, emoji):
        """Lets a user define the emoji the user have to react with
        in order to let the bot quote it

        Usage:
        !setemoji {emoji}"""

        settings_setemoji = load_settings()

        # if the emoji is a normal (no custom) emoji
        if not emoji.startswith("<"):
            emoji = emojis.decode(emoji)

        settings_setemoji[f"{ctx.guild.id}"]["emoji"] = emoji

        with open("Settings/Settings.json", "w") as file:
            json.dump(settings_setemoji, file, indent=4, sort_keys=True)

        try:
            await ctx.send(f"New reaction emoji successfully set to {emoji}")
        except discord.Forbidden:
            return 0

        return 0

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.cooldown(1, 2, commands.BucketType.default)
    async def setminreact(self, ctx, minimum):
        """Lets a user define how many users have to react
        to a message to let the bot quote it

        Usage:
        !setminusers {number}"""

        settings_minreact = load_settings()

        if minimum.isdigit() and int(minimum) > 0:
            settings_minreact[f"{ctx.guild.id}"]["threshold"] = int(minimum)
        else:
            await ctx.send(f"{minimum} is not a number above zero")
            return 0

        with open("Settings/Settings.json", "w") as file:
            json.dump(settings_minreact, file, indent=4, sort_keys=True)

        try:
            await ctx.send(f"Minimum amount of reactions successfully set to {minimum}")
        except discord.Forbidden:
            return 0

        return 0

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.cooldown(1, 2, commands.BucketType.default)
    async def setownreact(self, ctx, argument):
        """Lets a user define if the guild allows to define
        if the bot ignores messages, that have been reacted upon by the message auhthor
        or not

        Usage: !setownreact {"ON/OFF"} """

        settings_setownreact = load_settings()

        if argument.lower() == "on":
            settings_setownreact[f"{ctx.guild.id}"]["react_to_own"] = 1
            reply = "on"
        else:
            settings_setownreact[f"{ctx.guild.id}"]["react_to_own"] = 0
            reply = "off"

        with open("Settings/Settings.json", "w") as file:
            json.dump(settings_setownreact, file, indent=4, sort_keys=True)

        try:
            await ctx.send(f"Self reacting successfully turned {reply}")
        except discord.Forbidden:
            return 0

        return 0

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.cooldown(1, 2, commands.BucketType.default)
    async def settings(self, ctx):
        """Shows the current settings for the server triggered in"""

        settings_settings = load_settings()

        channel = settings_settings[f"{ctx.guild.id}"]["channel_id"]
        emoji = settings_settings[f"{ctx.guild.id}"]["emoji"]
        threshold = settings_settings[f"{ctx.guild.id}"]["threshold"]

        if settings_settings[f"{ctx.guild.id}"]["react_to_own"] == 0:
            selfreact = ":regional_indicator_x:"
        else:
            selfreact = ":ballot_box_with_check:"

        settings_embed = discord.Embed(
            title=f"Settings for {ctx.guild.name}",
            description=f"\nChannel posting in: <#{channel}>\n\n"
                        f"Emoji to be reacted with: {emoji}\n\n"
                        f"Minimum amount of users to react: {threshold}\n\n"
                        f"Can react to own message: {selfreact}",
            color=ctx.author.color
        )

        settings_embed.set_author(
            name=ctx.author.name,
            icon_url=ctx.author.avatar_url
        )
        try:
            await ctx.send(embed=settings_embed)
        except discord.Forbidden:
            return 0

        return 0


# Loads up the settings for the bot
def load_settings():
    with open("Settings/Settings.json", "r") as file:
        settings = json.load(file)
    return settings


# Generates the message embed
async def embed_message(guild: discord.Guild, message: discord.Message):
    settings = load_settings()

    if message.id in settings[f"{guild.id}"]["quoted_messages"]:
        return 0

    # Checks if the message has been sent via mobile or desktop
    if message.author.is_on_mobile():
        emoji = "📱"
    else:
        emoji = "💻"

    # Embed body
    msg_embed = discord.Embed(
        title=f"In #{message.channel} via {emoji}",
        description=f"[Jump to message]({message.jump_url})",
        color=message.author.color,
        timestamp=message.created_at
    )

    # If message contains an invite
    if message.activity is not None:
        msg_embed.add_field(
            name="Invite",
            value=message.activity["party_id"]
        )

    # Embed footer
    msg_embed.set_footer(
        text=message.id
    )

    # if message contains text
    if message.content != "":
        msg_embed.add_field(
            name=f"Content:",
            value=f"{message.content}"
        )

    # If message contains pictures or videos
    for file in message.attachments:
        if not file.filename.endswith((".mp4", ".ogg", ".m4a", ".webm", ".ovm")):
            msg_embed.set_image(url=file.url)
        else:
            msg_embed.add_field(
                name=file.filename,
                value=file.url
            )

    # Embed author
    msg_embed.set_author(
        name=str(message.author),
        icon_url=message.author.avatar_url
    )

    channel = discord.utils.get(guild.text_channels, id=settings[f"{guild.id}"]["channel_id"])
    try:
        await channel.send(embed=msg_embed)
    except discord.Forbidden:
        return 0

    # prevent the message from being sent again
    settings[f"{guild.id}"]["quoted_messages"].append(message.id)
    with open("Settings/Settings.json", "w") as file:
        json.dump(settings, file, indent=4, sort_keys=True)

    return 0


# creating a log message in the log channel
async def create_log_embed(action: str, guild: discord.Guild, settings: dict):

    if action == "add":
        color = 0x00FF00
        title = f"Joined **{guild.name}**"
        timestamp = guild.me.joined_at
    else:
        color = 0xFF0000
        title = f"Left **{guild.name}**"
        timestamp = datetime.datetime.utcnow()

    # log embed for when the bot gets added to a guild
    guild_log_embed = discord.Embed(
        title=title,
        description=f"Guild id:     {guild.id}\n"
                    f"Member count: {len(guild.members)-1}",
        color=color,
        timestamp=timestamp
    )

    guild_log_embed.set_thumbnail(
        url=guild.icon_url
    )

    guild_log_embed.set_footer(
        text=f"Guild count: {len(bot.guilds)} guilds"
    )

    channel = 0
    for guild_id in settings:
        if "log_channel" in settings[guild_id].keys():
            channel = bot.get_channel(settings[guild_id]["log_channel"])

    await channel.send(embed=guild_log_embed)

# adds the cogs to the bot
def setup(discord_bot):
    discord_bot.add_cog(System(discord_bot))
    discord_bot.add_cog(Core(discord_bot))
    discord_bot.add_cog(Customizing(discord_bot))
    discord_bot.add_cog(DiscordBotsOrgAPI(discord_bot))


setup(bot)


#############################
# Events:                   #
# on_ready                  #
# on_reaction_add           #
# on_guild_join             #
# on_guild_remove           #
# on_command_error          #
#############################

@bot.event
async def on_ready():
    print("logged in successfully")
    await bot.change_presence(
        activity=discord.Activity(name='React with 🏆 | !help', type=1, url="https://www.twitch.tv/quotebot_5599"))


@bot.event
async def on_reaction_add(reaction, member):
    settings = load_settings()

    # if the reaction is in the quote channel, it will get ignored
    if reaction.message.channel.id == settings[f"{reaction.message.guild.id}"]["channel_id"]:
        return 0

    # Extracts the emoji
    # If the emoji should be custom, the bot searches through the server
    emoji = settings[f"{reaction.message.guild.id}"]["emoji"]
    if emoji.startswith(":"):
        emoji = emojis.encode(emoji)
    else:
        emoji = discord.utils.get(reaction.message.guild.emojis, id=int(emoji.split(":")[-1].split(">")[0]))

    count = reaction.count
    # if the message author reacts and the guild specified it before, it gets ignored,
    if settings[f"{reaction.message.guild.id}"]["react_to_own"] == 0:
        users = await reaction.users().flatten()
        if reaction.message.author in users:
            count -= 1

    if reaction.emoji == emoji and count == settings[f"{reaction.message.guild.id}"]["threshold"]:

        # when the channel is not defined, the bot notifies of this and returns
        if settings[f"{reaction.message.guild.id}"]["channel_id"] == 0:
            await reaction.message.channel.send("The quotation channel has not been defined,\n"
                                                "to do this, type ``!setchannel`` in the desired channel.\n"
                                                "(Manage server permissions required)")
            return 0

        await embed_message(reaction.message.guild, reaction.message)

    return 0


#########################################################################################################
# On guild join, the bot opens the template for the different servers.                                  #
# It saves the server.                                                                                  #
# The channel id is 0 in the beginning. If it stays zero, the bot will post the embed in the channel    #
# the message is in.                                                                                    #
# The lowest role id is "None" in the beginning. If it stays "None". only users with the manage message #
# permissions are able to configure and use it                                                          #
#########################################################################################################

@bot.event
async def on_guild_join(guild):

    with open("Settings/Settings.json", "r") as f_file:
        s_settings = json.load(f_file)

        threshold = 3

        new_guild_dict = {f"{guild.id}":
            {
                "channel_id": 0,
                "emoji": ":trophy:",
                "threshold": threshold,
                "quoted_messages": [],
                "react_to_own": 0
            }
        }
        s_settings.update(new_guild_dict)


    with open("Settings/Settings.json", "w") as f_file:
        json.dump(s_settings, f_file, indent=4, sort_keys=True)

    await create_log_embed("add", guild, s_settings)

    return 0

#####################################
# When a guild is left,             #
# the respective entry gets deleted #
#####################################

@bot.event
async def on_guild_remove(guild):
    s_settings = load_settings()
    del s_settings[f"{guild.id}"]

    with open("Settings/Settings.json", "w") as f_file:
        json.dump(s_settings, f_file, indent=4, sort_keys=True)

    await create_log_embed("remove", guild, s_settings)

    return 0


#########################################
# Errors get retuned via the bot/client #
#########################################

@bot.event
async def on_command_error(ctx, error):
    if ctx.command is not None:
        try:
            await ctx.send(f"[COMMAND ERROR]: During handling of command '{ctx.command.name}' in guild {ctx.guild.id} happened following error: \n{error}\n")
        except discord.Forbidden:
            return 0
    else:
        try:
            await ctx.send(f"[COMMAND ERROR]: command '{ctx.message.content}' not found\n")
        except discord.Forbidden:
            return 0

    return 0


#####################
# Bot starting loop #
#####################

async def bot_start():
    await bot.start(bottoken.token())


loop = asyncio.get_event_loop()
loop.run_until_complete(bot_start())
loop.close()
