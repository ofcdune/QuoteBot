from discord.ext import commands
import discord
import asyncio
import dataset
import emojis
import bottoken
import dbl
from io import StringIO
import sys
import datetime
import random

# Initialising and defining the bot
bot = commands.Bot(owner_id=311268449181630464,
                   description="If a message is extraordinarily funny,\nreact with"
                               " a specified emoji and it gets posted in your channel\n"
                               "of wish.",
                   command_prefix=["!"],
                   help_command=None)
database = dataset.connect("sqlite:///settings.db")


class System(commands.Cog):

    def __init__(self, discord_bot):
        self.bot = discord_bot

    @commands.command(name="eval")
    async def exec(self, ctx, *, command):
        """Executes the given code in the discord message"""

        if not ctx.author.id == 326260487220363275 and not ctx.author.id == bot.owner_id:
            return 0

        command = command.split("```python")[1]
        command = command.split("```")[0]

        # redirects the output
        old_out = sys.stdout
        result = StringIO()
        sys.stdout = result

        # execute the commands
        exec(command)

        # redirects the output again
        sys.stdout = old_out

        # gets the result of the command
        result_string = result.getvalue()

        if result_string == "":
            result_string = "N/A"

        # result embed
        result_embed = discord.Embed(
            title="Code evaluated successfully",
            description=f"```python\n"
                        f">>> {result_string}```",
            color=ctx.author.color,
            timestamp=ctx.message.created_at
        )

        result_embed.set_author(
            name=f"Python version: {sys.version.split()[0]}",
            icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/2000px-Python-logo-notext.svg.png"
        )

        result_embed.set_footer(
            text=f"CPU info: {sys.version.split('[')[1].split(']')[0]}",
        )

        await ctx.send(embed=result_embed)

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
    async def guildcount(self, ctx):
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
            print(f"{datetime.datetime.now()} > Attempting to update server count")
            try:
                await self.dblpy.post_guild_count()
                print(f"{datetime.datetime.now()} > Server count successfully updated ({len(bot.guilds)})")
                print("")
            except NameError:
                print(f"{datetime.datetime.now()} > Failed to update server count")
                print("")
            await asyncio.sleep(1800)

        else:
            self.updating = self.bot.loop.create_task(self.update_stats())

    @commands.command()
    @commands.is_owner()
    async def updatestart(self, ctx):
        """Starts the update loop manually"""
        self.updating = self.bot.loop.create_task(self.update_stats())
        await ctx.send("Loop successfully restarted")


class Core(commands.Cog):

    def __init__(self, discord_bot):
        self.bot = discord_bot

    @commands.command(aliases=["trophy"])
    @commands.bot_has_permissions(send_messages=True,
                                  embed_links=True)
    @commands.has_permissions(manage_messages=True)
    async def star(self, ctx, message):
        """Triggers the bot manually to generate an embed

        The message must either be:
        -   a valid ID
        -   a valid message link"""
        channel = load_settings("Settings", "channel_id", ctx.guild.id)
        message = await commands.MessageConverter().convert(ctx, message)
        message_dict = await bot.http.get_message(message.channel.id, message.id)

        if channel == 0:
            try:
                await ctx.send("The quotation channel has not been defined,\n"
                               "type ``!help`` for more info")
                return 0
            except discord.Forbidden:
                return 0

        if database["Quoted messages"].find_one(message_id=message.id) is not None:
            return 0

        try:
            save_message(ctx.guild.id, message.id, message_dict, [], 0)
            await embed_message(ctx.guild, message)
        except discord.NotFound:
            # tries to warn the users or else raise the same error anyways
            try:
                await ctx.send("The message cannot be found with the message ID, please use the message link")
            except discord.Forbidden:
                raise discord.NotFound

        return 0

    @commands.command()
    async def starboard(self, ctx):
        """Shows a leaderboard for the messages in the server"""
        messages = database["Quoted messages"]
        emoji = load_settings("Settings", "emoji", ctx.message.guild.id)

        # lists and dicts for the messages
        guild_messages_dicts = []
        best_users = []
        reactors = []
        reactors_dic = {}

        # strings to format the output
        best_message_string = []
        total_reaction_count = 0
        most_reacted_users = []

        # index to only display the first ten entries
        index = 0

        guild_messages = messages.find(guild_id=ctx.message.guild.id)
        for message in guild_messages:
            message = dict(message)
            guild_messages_dicts.append(message)

        # finds out the best messages
        guild_messages_dicts = sorted(guild_messages_dicts, key=lambda i: (i['reaction_count']), reverse=True)

        # finds out the total reaction count
        for message in guild_messages_dicts:
            total_reaction_count += message["reaction_count"]

        # finds out the user who reacted most
        for message in guild_messages_dicts:
            reactors.append(message["reaction_uid"])

        reactors = [y for x in reactors for y in x]
        for reactor in reactors:
            reactors_dic.update({reactor: reactors.count(reactor)})

        reactors_dic = dict(sorted(reactors_dic.items(), key=lambda x: x[1], reverse=True))

        # prepares the string for the best messages
        for message in guild_messages_dicts:
            index += 1
            best_message_string.append(
                f"{index}) [{message['message']['id']}]"
                f"(https://discordapp.com/channels/{ctx.message.guild.id}/{message['message']['channel_id']}/{message['message']['id']}) "
                f"by: <@{message['message']['author']['id']}> - {message['reaction_count']} {emoji}\n")

            if index == 5:
                index = 0
                break
        best_message_string = "".join(best_message_string)
        # prepares the string for the users who reacted most

        for user in reactors_dic:
            index += 1
            most_reacted_users.append(f"{index}) <@{user}> gave {reactors_dic[user]} reactions\n")

            if index == 5:
                index = 0
                break

        most_reacted_users = "".join(most_reacted_users)

        # prepares the leaderboard embed
        lb_embed = discord.Embed(
            title=f"Starboard leaderboard for {ctx.guild.name}",
            description=f"{len(guild_messages_dicts)} messages starred\n"
                        f"{total_reaction_count} reactions in total",
            color=ctx.message.author.color,
            timestamp=ctx.message.created_at
        )

        lb_embed.add_field(
            name="**Most starred messages**",
            value=best_message_string
        )

        lb_embed.add_field(
            name="**Users who gave the most stars**",
            value=most_reacted_users,
            inline=False
        )

        await ctx.send(embed=lb_embed)
        return 0

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def quote(self, ctx, user=""):
        """Picks a random quote out of the starboard. User can be specified"""
        messages = database["Quoted messages"]
        random_quote_dict = {}
        guild_messages = messages.find(guild_id=ctx.message.guild.id)

        for message in guild_messages:
            message = dict(message)
            random_quote_dict.update({message["message"]["content"]: message["message"]})

        if user != "":
            random_quote_dict2 = {}
            user = await commands.MemberConverter().convert(ctx, user)
            for random_quote in random_quote_dict:
                if random_quote_dict[random_quote]["author"]["id"] == str(user.id):
                    random_quote_dict2.update({random_quote: random_quote_dict[random_quote]})
        else:
            random_quote_dict2 = random_quote_dict

        quote, everything_else = random.choice(list(random_quote_dict2.items()))
        user = await commands.UserConverter().convert(ctx, everything_else["author"]["id"])

        quote_embed = discord.Embed(
            title=f"{user.name} once said:",
            description=f"{quote}\n"
                        f"[Click here to jump to the message]"
                        f"(https://discordapp.com/channels/{ctx.message.guild.id}/{message['message']['channel_id']}/{message['message']['id']})",
            color=ctx.author.color,
            timestamp=datetime.datetime.strptime(everything_else["timestamp"], '%Y-%m-%dT%H:%M:%S.%f+00:00')
        )

        # If quote contains pictures or videos
        for file in everything_else["attachments"]:
            quote_embed.set_image(url=file["url"])

        quote_embed.set_author(
            name=user.name,
            icon_url=user.avatar_url
        )

        await ctx.send(embed=quote_embed)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def invite(self, ctx):
        """Shows the invite link for this bot if you like it"""
        try:
            await ctx.send(
                "My invite link is: https://discordapp.com/api/oauth2/authorize?client_id=625112945881382912&permissions=18432&scope=bot")
        except discord.Forbidden:
            return 0

        return 0

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def support(self, ctx):
        """Shows the invite link for the support server"""
        await ctx.send("The invite for my support server: https://discord.gg/txz5zbt")

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def vote(self, ctx):
        """Shows the link to vote for this bot if you really like it"""
        try:
            await ctx.send("My link to vote is: https://discordbots.org/bot/625112945881382912")
        except discord.Forbidden:
            return 0

        return 0

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def help(self, ctx):
        """Help message and tutorial"""

        try:
            await ctx.send(
                "This bot lets you react to a certain message with an emoji (default :trophy:) and post it into a "
                "custom starboard channel. You are completely free in customization whatsoever.\n```python\n"
                "!star {'message_id'/'message_link'}: Does the quotation automatically.\n"
                ">>> 'Requires manage message permissions'\n"
                "Aliases: ['trophy']\n\n"
                "'!starboard': Shows the 5 best messages of the guild from the starboard\n\n"
                "'!quote': Shows a random quote from a message in the starboard OR '!quote {user}' to show a random quote only of that user\n\n"
                "'!invite': Shows an invite link for this bot.\n\n"
                "'!vote': Shows a vote link for this bot\n\n"
                "'!setchannel' in your preferred channel or '!setchannel {channel_mention/channel_id}': Type this to set up your starboard.\n"
                ">>> 'Requires Manage message permissions'\n\n"
                "'!setemoji {emoji}': Set up your own reaction emoji. Can also be a custom one.\n"
                ">>> 'Requires Manage emojis permissions'\n\n"
                "'!setminreact {threshold}': Set up the threshold.\n"
                ">>> 'Requires Manage channels permissions'\n\n"
                "'!setownreact {on/off}': If turned on, the message author can also react to his own message.\n"
                ">>> 'Requires Manage channels permissions'\n\n"
                "'!whitelist {role}': Add a role that is whitelisted for reacting to messages. If left blank, the whitelist gets cleared\n"
                ">>> 'Requires Manage roles permissions'\n\n"
                "'!settings': Shows the current settings for this guild.\n"
                "```")
        except discord.Forbidden:
            return 0

        return 0


class Customizing(commands.Cog):

    def __init__(self, discord_bot):
        self.bot = discord_bot

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.cooldown(1, 3, commands.BucketType.default)
    async def setchannel(self, ctx, channel="0"):
        """Lets a user define the quotes channel

        Usage
        !setchannel
        in the desired channel"""

        if channel == "0":
            channel = ctx.channel
        else:
            channel = await commands.TextChannelConverter().convert(ctx, channel)

        update_settings("Settings", dict(guild_id=ctx.guild.id,
                                         channel_id=channel.id))

        try:
            await ctx.send(f"New quotes channel successfully set to <#{channel.id}>")
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

        # if the emoji is a normal (no custom) emoji
        if not emoji.startswith("<"):
            emoji = emojis.decode(emoji)

        update_settings("Settings", dict(guild_id=ctx.guild.id,
                                         emoji=emoji))

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

        if minimum.isdigit() and int(minimum) > 0:
            update_settings("Settings", dict(guild_id=ctx.guild.id,
                                             reaction_threshold=minimum))
        else:
            await ctx.send(f"{minimum} is not a number above zero")
            return 0

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

        if argument.lower() == "on":
            update_settings("Settings", dict(guild_id=ctx.guild.id,
                                             react_to_own=1))
            reply = "on"
        else:
            update_settings("Settings", dict(guild_id=ctx.guild.id,
                                             react_to_own=0))
            reply = "off"

        try:
            await ctx.send(f"Self reacting successfully turned {reply}")
        except discord.Forbidden:
            return 0

        return 0

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.cooldown(1, 2, commands.BucketType.default)
    async def whitelist(self, ctx, role="0"):
        """Whitelists roles to react

        Usage: !setrole {role}"""

        if role == "0":
            update_settings("Settings", dict(guild_id=ctx.guild.id,
                                             allowed_roles=None))

            try:
                await ctx.send("All role whitelists cleared")
            except discord.Forbidden:
                return 0

        else:
            role = await commands.RoleConverter().convert(ctx, role)

            roles = load_settings("Settings", "allowed_roles", ctx.guild.id)
            if roles is None:
                roles = []

            update_settings("Settings", dict(guild_id=ctx.guild.id,
                                             allowed_roles=roles))

            try:
                await ctx.send(f"Role '{role.name}' succesfully whitelisted")
            except discord.Forbidden:
                return 0

        return 0

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.cooldown(1, 2, commands.BucketType.default)
    async def settings(self, ctx):
        """Shows the current settings for the server triggered in"""

        settings = database["Settings"]
        rolelist = []

        channel = settings.find_one(guild_id=ctx.guild.id)["channel_id"]
        emoji = settings.find_one(guild_id=ctx.guild.id)["emoji"]
        threshold = settings.find_one(guild_id=ctx.guild.id)["reaction_threshold"]
        allowed_roles = settings.find_one(guild_id=ctx.guild.id)["allowed_roles"]
        if allowed_roles is None:
            allowed_roles = []

        if settings.find_one(guild_id=ctx.guild.id)["react_to_own"] == 0:
            selfreact = ":regional_indicator_x:"
        else:
            selfreact = ":ballot_box_with_check:"

        settings_embed = discord.Embed(
            title=f"Settings for {ctx.guild.name}",
            description=f"\nCurrent Starboard channel: <#{channel}>\n\n"
                        f"Current emoji: {emoji}\n\n"
                        f"Current reaction threshold: {threshold}\n\n"
                        f"Can react to own message: {selfreact}",
            color=ctx.author.color
        )
        if len(rolelist) > 0:
            for role in allowed_roles:
                rolelist.append(f"<@&{role}>")
            settings_embed.add_field(
                name="**Roles:**",
                value=f"{' '.join(rolelist)}",
                inline=False
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


def load_settings(table: str, arg: str, guild_id: int):
    """loads the database table"""
    return database[table].find_one(guild_id=guild_id)[arg]


# saves the settings
def update_settings(table: str, new_dict: dict, pk: str = "guild_id"):
    with dataset.connect("sqlite:///settings.db") as file:
        file[table].update(new_dict, [pk])


# updates the settings
def save_settings(table: str, new_dict: dict):
    with dataset.connect("sqlite:///settings.db") as file:
        file[table].insert(new_dict)


# saves the message settings
def save_message(guild_id: int, message_id: int, message: dict, uid: list, count: int):
    save_settings("Quoted messages", dict(guild_id=guild_id,
                                          message_id=message_id,
                                          message=message,
                                          reaction_uid=uid,
                                          reaction_count=count
                                          ))


# updates the message settings
def update_message(message_id: int, uid: list, count: int):
    update_settings("Quoted messages", dict(message_id=message_id,
                                            reaction_uid=uid,
                                            reaction_count=count
                                            ), "message_id")


# updates the embed message
async def update_embed(guild_id: int, message_id: int):
    messages = database["Quoted messages"]
    settings = database["Settings"]

    emoji = settings.find_one(guild_id=guild_id)["emoji"]
    channel_id = settings.find_one(guild_id=guild_id)["channel_id"]
    count = messages.find_one(message_id=message_id)["reaction_count"]
    embed_id = messages.find_one(message_id=message_id)["embed_message"]

    try:
        await bot.http.edit_message(channel_id, embed_id, content=f"{emoji} {count}")
    except discord.NotFound:
        pass


# Generates the message embed
async def embed_message(guild: discord.Guild, message: discord.Message):
    settings = database["Settings"]
    messages = database["Quoted messages"]

    # Checks if the message has been sent via mobile or desktop
    if message.author.is_on_mobile():
        emoji = "📱"
    else:
        emoji = "💻"

    # Embed body for messages with content
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
            value=message.activity["party_id"],
            inline=False
        )
    # Embed footer
    msg_embed.set_footer(
        text=message.id
    )
    # if message contains text
    if message.content != "":
        msg_embed.add_field(
            name=f"**Content:**",
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

    if messages.find_one(message_id=message.id)["embed_message"] is not None:
        return 0

    channel = bot.get_channel(settings.find_one(guild_id=guild.id)["channel_id"])
    try:

        embed_msg = await channel.send(
            f"{settings.find_one(guild_id=guild.id)['emoji']} {messages.find_one(message_id=message.id)['reaction_count']} ",
            embed=msg_embed)
    except discord.Forbidden:
        return 0

    # save the id of the embed message
    update_settings("Quoted messages", dict(message_id=message.id, embed_message=embed_msg.id), "message_id")

    return 0


# creating a log message in the log channel
async def create_log_embed(action: str, guild: discord.Guild):
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
                    f"Member count: {len(guild.members)}",
        color=color,
        timestamp=timestamp
    )
    guild_log_embed.set_thumbnail(
        url=guild.icon_url
    )
    guild_log_embed.set_footer(
        text=f"Guild count: {len(bot.guilds)} guilds"
    )

    channel = bot.get_channel(633315659698143235)
    await channel.send(embed=guild_log_embed)


# adds the cogs to the bot
def setup(discord_bot):
    discord_bot.add_cog(System(discord_bot))
    discord_bot.add_cog(Core(discord_bot))
    discord_bot.add_cog(Customizing(discord_bot))
    discord_bot.add_cog(DiscordBotsOrgAPI(discord_bot))


#############################
# Events:                   #
# on_connect                #
# on_disconnect             #
# on_ready                  #
# on_reaction_add           #
# on_guild_join             #
# on_guild_remove           #
# on_command                #
# on_command_error          #
#############################

@bot.event
async def on_connect():
    print(f"{datetime.datetime.now()} > Client successfully connected to the API server")


@bot.event
async def on_disconnect():
    print(f"{datetime.datetime.now()} > Client disconnected or failed to connect to the API server")
    print("")


@bot.event
async def on_ready():
    print(f"{datetime.datetime.now()} > Client activated and ready")
    print("")
    await bot.change_presence(
        activity=discord.Activity(name=f'on {len(bot.guilds)} servers | !help', type=0))
    if database["started"].find_one(constant=1)["started"] == 1:
        update_settings("started", {"constant": 1, "started": 0}, "constant")
        setup(bot)


@bot.event
async def on_reaction_add(reaction, member):
    # settings from the database
    settings = database["Settings"]

    settings_table = settings.find_one(guild_id=reaction.message.guild.id)
    emoji = settings_table["emoji"]  # the starboard emoji

    # If the emoji should be custom, the bot searches through the server
    if emoji.startswith(":"):
        emoji = emojis.encode(emoji)
    else:
        emoji = bot.get_emoji(id=int(emoji.split(":")[-1].split(">")[0]))

    # if the emoji reacted with is not the specified one, the bot ignores the rest
    if reaction.emoji != emoji:
        return 0

    channel = settings_table["channel_id"]  # the starboard channel

    # if the reaction is in the quote channel, it will get ignored
    if str(reaction.message.channel.id) == channel:
        return 0

    threshold = settings_table["reaction_threshold"]  # the reaction threshold
    allowed_roles = settings_table["allowed_roles"]  # the roles allowed to react
    if allowed_roles is None:
        allowed_roles = []

    message_dict = await bot.http.get_message(channel_id=reaction.message.channel.id, message_id=reaction.message.id)
    roles = member.roles

    # if the message author reacts and the guild specified it before, it gets ignored,
    # same as when none of the roles of a user are not whitelisted
    count = reaction.count
    users = await reaction.users().flatten()

    for user in users:
        if settings.find_one(guild_id=reaction.message.guild.id)["react_to_own"] == 0:

            if user == reaction.message.author:
                try:
                    await reaction.message.remove_reaction(emoji, user)
                    count -= 1
                except discord.Forbidden:
                    count -= 1

        if len(allowed_roles) > 1:
            if len(set(allowed_roles).intersection(roles)) == 0:
                try:
                    await reaction.message.remove_reaction(emoji, user)
                    count -= 1
                except discord.Forbidden:
                    count -= 1

    # if the message reached the reaction threshold
    if reaction.emoji == emoji and count == threshold:

        # when the channel is not defined, the bot notifies of this and returns
        if channel == 0:
            await reaction.message.channel.send("The quotation channel has not been defined,\n"
                                                "type ``!help`` for more info")
            return 0

        # save the message details
        uid_list = []
        for user in users:
            uid_list.append(user.id)
        save_message(reaction.message.guild.id, reaction.message.id, message_dict, uid_list, count)

        await embed_message(reaction.message.guild, reaction.message)

    if reaction.emoji == emoji and count > threshold:

        # update the message details
        uid_list = list()
        for user in users:
            uid_list.append(user.id)
        update_message(reaction.message.id, uid_list, count)
        await update_embed(reaction.message.guild.id, reaction.message.id)

    return 0


##############################################################
# When the bot joins a guild, the default settings get saved #
##############################################################

@bot.event
async def on_guild_join(guild):
    save_settings("Settings",
                  {
                      "guild_id": guild.id,
                      "channel_id": 0,
                      "emoji": ":trophy:",
                      "reaction_threshold": 3,
                      "react_to_own": 0
                  })

    await create_log_embed("add", guild)
    await bot.change_presence(
        activity=discord.Activity(name=f'on {len(bot.guilds)} servers | !help', type=0))

    return 0


#####################################
# When a guild is left,             #
# the respective entry gets deleted #
#####################################

@bot.event
async def on_guild_remove(guild):
    with dataset.connect("sqlite:///settings.db") as file:
        file["Settings"].delete(guild_id=guild.id)

    await create_log_embed("remove", guild)
    await bot.change_presence(
        activity=discord.Activity(name=f'on {len(bot.guilds)} servers | !help', type=0))

    return 0


###########################################
# Commands handled by the discord.ext lib #
###########################################

@bot.event
async def on_command(ctx):
    print(f"{datetime.datetime.now()} [COMMAND]: In guild '{ctx.guild.name}'({ctx.guild.id}):\n{ctx.message.content}")
    print("")


#################################################
# Command errors handled by the discord.ext lib #
#################################################

@bot.event
async def on_command_error(ctx, error):
    if ctx.command is not None:
        print(
            f"{datetime.datetime.now()} [COMMAND ERROR]: During handling of command '{ctx.command.name}' in guild '{ctx.guild.name}'"
            f" happened following error: \n{error}\nMessage: {ctx.message.content}")
        print("")
        try:
            await ctx.send(
                f":warning: During handling of command '{ctx.command.name}' happened following error: \n> {error}")
        except discord.Forbidden:
            return 0

    return 0

#####################
# Bot starting loop #
#####################

async def bot_start():
    print(f"{datetime.datetime.now()} > Trying to connect to the API server...")
    if database["started"].find_one(constant=1)["started"] == 0:
        update_settings("started", {"constant": 1, "started": 1}, "constant")
        await bot.start(bottoken.token())

loop = asyncio.get_event_loop()
loop.run_until_complete(bot_start())
loop.close()
