from discord.ext import commands
import discord
import asyncio
import json
import emojis
import bottoken

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
    async def execute(self, ctx):
        """Executes the given code in the discord message"""

        command = ctx.message.content.split("``")[1]
        exec(command) # troubleshooting

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx):
        """Reloads an extension"""

        ext_name = ctx.message.content.split()[-1]
        bot.reload_extension(ext_name) # troubleshooting
        await ctx.send(f"{ext_name} was successfully reloaded")

class Core(commands.Cog):

    def __init__(self, discord_bot):
        self.bot = discord_bot
        with open("Settings/Settings.json", "r") as file:
            self.settings = json.load(file)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True,
                                  embed_links=True)
    @commands.has_permissions(manage_messages=True)
    async def trophy(self, ctx, message):
        """Triggers the bot manually to generate an embed

        The message must either be:
        -   a valid ID
        -   a valid message link"""
        await ctx.send("Successfully")

        message = await commands.MessageConverter().convert(ctx, message)

        if self.settings[f"{ctx.guild.id}"]["channel_id"] == 0:
            await ctx.send("The quotation channel has not been defined,\n"
                           "to do this, type ``!setchannel`` in the desired channel.\n"
                           "(Manage server permissions required)")
        else:
            await embed_message(ctx.guild, message)

        return 0

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def invite(self, ctx):
        """Shows the invite link for this bot if you like it"""
        await ctx.send(
            "My invite link is https://discordapp.com/api/oauth2/authorize?client_id=625112945881382912&permissions=18432&scope=bot")

        return 0

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def vote(self, ctx):
        """Shows the link to vote for this bot if you really like it"""
        await ctx.send("My link to vote is https://discordbots.org/bot/625112945881382912")

        return 0

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def help(self, ctx):
        """Help message and tutorial"""

        await ctx.send("This bot lets you 'quote' a message by either reacting "
                       "with an emoji (default: 🏆) or typing ``!trophy {message_id}``.\n"
                       "To get more information about all available commands,"
                       " just click on 'Watch' on my profile")

        return 0

class Customizing(commands.Cog):

    def __init__(self, discord_bot):
        self.bot = discord_bot
        with open("Settings/Settings.json", "r") as file:
            self.settings = json.load(file)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(send_messages=True)
    @commands.cooldown(1, 2, commands.BucketType.default)
    async def setchannel(self, ctx):
        """Lets a user define the quotes channel

        Usage
        !setchannel
        in the desired channel"""

        self.settings[f"{ctx.guild.id}"]["channel_id"] = ctx.channel.id

        with open("Settings/Settings.json", "w") as file:
            json.dump(self.settings, file)
            await ctx.send(f"New quotes channel successfully set to {ctx.channel.mention}")

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

        self.settings[f"{ctx.guild.id}"]["emoji"] = emoji

        with open("Settings/Settings.json", "w") as file:
            json.dump(self.settings, file)
            await ctx.send(f"New reaction emoji successfully set to {emoji}")

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
            self.settings[f"{ctx.guild.id}"]["min_reaction"] = int(minimum)
        else:
            await ctx.send(f"{minimum} is not a number above zero")
            return 0

        with open("Settings/Settings.json", "w") as file:
            json.dump(self.settings, file)
            await ctx.send(f"Minimum amount of reactions successfully set to {minimum}")

        return 0

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.cooldown(1, 2, commands.BucketType.default)
    async def settings(self, ctx):
        """Shows the current settings for the server triggered in"""

        channel = self.settings[f"{ctx.guild.id}"]["channel_id"]
        emoji = self.settings[f"{ctx.guild.id}"]["emoji"]
        min_reaction = self.settings[f"{ctx.guild.id}"]["min_reaction"]

        settings_embed = discord.Embed(
            title=f"Settings for {ctx.guild.name}",
            description=f"\nChannel posting in: <#{channel}>\n\n"
                        f"Emoji to be reacted with: {emoji}\n\n"
                        f"Minimum amount of users to react: {min_reaction}",
            color=ctx.author.color
        )

        settings_embed.set_author(
            name=ctx.author.name,
            icon_url=ctx.author.avatar_url
        )

        await ctx.send(embed=settings_embed)

        return 0

async def embed_message(guild: discord.Guild, message: discord.Message):

    with open("Settings/Settings.json", "r") as file:
        settings = json.load(file)

    # Checks if the message has been sent via mobile or desktop
    if message.author.is_on_mobile():
        emoji = "📱"
    else:
        emoji = "💻"

    # Embed body
    msg_embed = discord.Embed(
        title=f"In #{message.channel} via {emoji}",
        description=f"{message.content}",
        color=message.author.color,
        timestamp=message.created_at
    )

    # If message contains an invite
    if message.activity is not None:
        msg_embed.add_field(
            name="Invite",
            value=message.activity["party_id"]
        )

    # If message contains pictures
    for image in message.attachments:
        msg_embed.set_image(url=image.url)

    # Embed footer
    msg_embed.set_footer(
        text=message.id
    )

    # Embed author
    msg_embed.set_author(
        name=str(message.author),
        url=message.jump_url,
        icon_url=message.author.avatar_url
    )

    channel = discord.utils.get(guild.text_channels, id=settings[f"{guild.id}"]["channel_id"])
    await channel.send(embed=msg_embed)
    return 0

def setup(discord_bot):
    discord_bot.add_cog(System(discord_bot))
    discord_bot.add_cog(Core(discord_bot))
    discord_bot.add_cog(Customizing(discord_bot))

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
    await bot.change_presence(activity=discord.Activity(name='React with 🏆 | !help', type=1, url="https://www.twitch.tv/quotebot_5599"))

@bot.event
async def on_reaction_add(reaction, member):

    with open("Settings/Settings.json", "r") as file:
        settings = json.load(file)

    # Extracts the emoji
    # If the emoji should be custom, the bot searches through the server
    emoji = settings[f"{reaction.message.guild.id}"]["emoji"]
    if emoji.startswith(":"):
        emoji = emojis.encode(emoji)
    else:
        emoji = discord.utils.get(reaction.message.guild.emojis, id=int(emoji.split(":")[-1].split(">")[0]))


    if reaction.emoji == emoji and reaction.count == settings[f"{reaction.message.guild.id}"]["min_reaction"]:

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

        if len(guild.members) > 7:
            min_reaction = int(len(guild.members)/4)
        else:
            min_reaction = len(guild.members)

        new_guild_dict = {f"{guild.id}":{"channel_id": 0, "emoji": ":trophy:", "min_reaction": min_reaction}}
        s_settings.update(new_guild_dict)

    with open("Settings/Settings.json", "w") as f_file:
        json.dump(s_settings, f_file)
    return 0

#####################################
# When a guild is left,             #
# the respective entry gets deleted #
#####################################

@bot.event
async def on_guild_remove(guild):

    with open("Settings/Settings.json", "r") as f_file:
        s_settings = json.load(f_file)
        del s_settings[f"{guild.id}"]

    with open("Settings/Settings.json", "w") as f_file:
        json.dump(s_settings, f_file)
    return 0

#########################################
# Most errors should happen silently    #
# and only show up on the console       #
#########################################

@bot.event
async def on_command_error(ctx, error):

    if error == commands.CommandOnCooldown:
        await ctx.send(f"{error}")
    if ctx.command is not None:
        print(f"[ERROR]: During handling of command {ctx.command.name} in guild {ctx.guild.id}"
              f" happened following error: \n{error}\n")
    else:
        print(f"[ERROR]: command '{ctx.message.content}' not found\n")

#####################
# Bot starting loop #
#####################

async def bot_start():
    await bot.start(bottoken.token())

loop = asyncio.get_event_loop()
loop.run_until_complete(bot_start())
loop.close()
