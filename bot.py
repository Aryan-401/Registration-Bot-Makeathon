import contextlib
import io
import os
import re
import textwrap
import time
import traceback

import discord
from discord.ext import commands
from discord.utils import get
from dotenv import load_dotenv

import exceptions

load_dotenv()
import mongo_db_functions


class CustomHelpCommand(commands.HelpCommand):

    def __init__(self):
        super().__init__()

    def get_ending_note(self):
        command_name = self.invoked_with
        return "Type {0}{1} <command/category> for more information".format(self.clean_prefix, command_name)

    async def send_bot_help(self, mapping):
        help_command = discord.Embed(
            title='Help is on the way',
            description=f'Heard you needed help! Here are all the commands you can access. {client.description}',
            colour=discord.Colour.blurple(),
        )
        for cog in mapping:
            if cog is not None:
                cog_name = cog.qualified_name
            else:
                cog_name = 'Default Commands'
            filtered = await self.filter_commands([command for command in mapping[cog]], sort=True)
            value = os.linesep.join([("> " + command.name.title()) for command in filtered])
            if len(value) > 1:
                help_command.add_field(name=cog_name, value=value)

        help_command.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=help_command)
        return await super(CustomHelpCommand, self).send_bot_help(mapping)

    async def send_cog_help(self, cog):
        cog_embed = discord.Embed(
            title=cog.qualified_name,
            colour=discord.Colour.blurple(),
        )
        filtered = await self.filter_commands([command for command in cog.get_commands()], sort=True)
        for command in filtered:
            cog_embed.add_field(name=command.name.title(), value=command.help, inline=False)
        cog_embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=cog_embed)
        return await super(CustomHelpCommand, self).send_cog_help(cog)

    async def send_group_help(self, group):  # Don't Need
        return await super(CustomHelpCommand, self).send_group_help(group)

    async def send_command_help(self, command):
        ctx = self.context
        if len("|".join(command.aliases)) > 0:
            base = f'{"."}[{command.name}|{"|".join(command.aliases)}]'
        else:
            base = f'{"."}[{command.name}]'
        syntax = f'```{base} {command.signature}```'
        command_embed = discord.Embed(
            title=command.name.title(),
            description=command.help + '\n' + syntax,
            colour=discord.Colour.blurple(),
        )
        command_embed.set_footer(text=self.get_ending_note())
        await self.get_destination().send(embed=command_embed)
        return await super(CustomHelpCommand, self).send_command_help(command)


client = commands.Bot(command_prefix=".", case_insensitive=True, help_command=CustomHelpCommand())


@client.event
async def on_ready():
    await client.change_presence(activity=discord.Activity(type=5, name="MAKE4THON"))
    print('Bot is ready')


@client.command(pass_context=True,
                help='Register your team to Make4thon and get exclusive your own channel and VC. Only to be used by '
                     'Team Leaders')
async def register(ctx, team_name, *, members):
    if ctx.channel.id == 942728218505510975:  # Channel where registration will take place
        members_list = [int(re.sub('[^A-Za-z0-9]+', '', x)) for x in members.split()]
        if len(members_list) > 4:
            raise exceptions.TooManyMembers
        guild = ctx.guild
        mongo_db_functions.add_team(team_name=team_name, leader=ctx.author.id, members=members_list)
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False),
                      ctx.author: discord.PermissionOverwrite(read_messages=True),
                      get(guild.roles, id=942775012983717948): discord.PermissionOverwrite(read_messages=True)}
        for i in members_list:
            member = guild.get_member(i)
            overwrites[member] = discord.PermissionOverwrite(read_messages=True)

        category = client.get_channel(942824676076429352)

        # Text channel
        channel = await guild.create_text_channel(team_name, overwrites=overwrites, category=category)
        # Voice channel
        vc = await guild.create_voice_channel(team_name, overwrites=overwrites, category=category)
        mongo_db_functions.add_team(team_name=team_name, leader=ctx.author.id, members=members_list, channel_form=True,
                                    channels_list=[channel.id, vc.id])


@client.command(pass_context=True, aliases=['lookup', 'team'], help='Look up the members of a team')
async def team_lookup(ctx, team_name: str):
    team_name = team_name.lower()
    team_data = mongo_db_functions.lookup(team_name=team_name)
    embed = discord.Embed(
        title=f"Looking for Team **\"{team_name.title()}\"**",
        colour=discord.Colour.dark_orange(),
    )

    leader = await client.fetch_user(team_data['leader'])
    members = [await client.fetch_user(id_) for id_ in team_data['members']]

    embed.add_field(name="Team Leader", value=leader.display_name)
    embed.add_field(name="Members", value=", ".join([m.name for m in members]))

    await ctx.send(embed=embed)


@client.command(pass_context=True, help='Add someone new to your team. Only for Team Leaders')
async def add(ctx, member: discord.Member):
    channel_list = mongo_db_functions.channel_lookup(ctx.author.id)  # add member into database
    text_channel = client.get_channel(channel_list[0])
    text_perms = text_channel.overwrites_for(member)
    text_perms.read_messages = True
    await text_channel.set_permissions(member, overwrite=text_perms)

    voice_channel = client.get_channel(channel_list[1])
    voice_perms = voice_channel.overwrites_for(member)
    voice_perms.read_messages = True
    await voice_channel.set_permissions(member, overwrite=voice_perms)
    mongo_db_functions.member_delta(leader=ctx.author.id, member_id=member.id, delta=1)


@client.command(pass_context=True, help='Remove someone from your Team. Only for Team Leaders')
async def remove(ctx, member: discord.Member):
    channel_list = mongo_db_functions.channel_lookup(ctx.author.id)  # remove the guy
    text_channel = client.get_channel(channel_list[0])
    text_perms = text_channel.overwrites_for(member)
    text_perms.read_messages = False
    await text_channel.set_permissions(member, overwrite=text_perms)

    voice_channel = client.get_channel(channel_list[1])
    voice_perms = voice_channel.overwrites_for(member)
    voice_perms.read_messages = False
    await voice_channel.set_permissions(member, overwrite=voice_perms)
    mongo_db_functions.member_delta(leader=ctx.author.id, member_id=member.id, delta=-1)


@client.command(help='Get Bot and Database Latency\nAccess: Everyone')
async def ping(ctx):
    bot_latency = f"{round(client.latency * 1000, 2)} ms"
    await ctx.send(
        embed=discord.Embed(
            title='You have been Ponged',
            description=f'Bot Latency: {bot_latency}\nDatabase Latency: {mongo_db_functions.calculate_ping()[0]}\nWrite Latency [MongoDB]: {mongo_db_functions.calculate_ping()[1]}\nRead Latency [MongoDB]: {mongo_db_functions.calculate_ping()[2]}',
            colour=discord.Colour(0x63e916)
        )
    )


async def is_worker(ctx):
    return ctx.author.id in [664401331250921473, 438281883881701391]


@client.command(aliases=['eval'], help='Owner Only Command for debugging')
@commands.check(predicate=is_worker)
async def code(ctx, *, block):
    code_block = mongo_db_functions.cleancode(block)

    local_variables = {
        "discord": discord,
        "commands": commands,
        "client": client,
        "ctx": ctx,
        "channel": ctx.channel,
        "author": ctx.author,
        "guild": ctx.guild,
        "message": ctx.message,
        'mongo_db_functions': mongo_db_functions,
    }

    stdout = io.StringIO()
    start_time = time.time() * 1000
    try:
        with contextlib.redirect_stdout(stdout):
            exec(
                f"async def func():\n{textwrap.indent(code_block, '    ')}", local_variables,
            )
            await ctx.message.add_reaction('⏱')
            obj = await local_variables["func"]()
            result = f"{stdout.getvalue()}"
            react_add = '✅'
    except Exception as e:
        result = "".join(traceback.format_exception(e, e, e.__traceback__))
        obj = e
        react_add = '❌'
    end_time = time.time() * 1000
    await ctx.message.remove_reaction('⏱', client.user)
    await ctx.send(f'```py\n{result}\n[{obj}]\nExecuted in {round(end_time - start_time, 3)} ms```')
    await ctx.message.add_reaction(react_add)


@client.check
async def globally_block_dms(ctx):
    return ctx.guild is not None


@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        if len("|".join(ctx.command.aliases)) > 0:
            base = f'{"."}[{ctx.command.name}|{"|".join(ctx.command.aliases)}]'
        else:
            base = f'{"."}[{ctx.command.name}]'
        error = f'{str(error)}\nCorrect syntax: ```{base} {ctx.command.signature}```'
    else:
        if str(error).startswith("Command"):
            error = str(error)[29:]
        else:
            error = str(error)
    embed = discord.Embed(
        title='Houston we have a problem',
        description=error,
        colour=discord.Colour(0xE93316)
    )
    embed.set_footer(text=f'For more information try running {"."}help')

    await ctx.message.channel.send(embed=embed)


client.run(os.getenv("TOKEN"))
