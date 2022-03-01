import asyncio
import contextlib
import datetime
import io
import os
import random
import textwrap
import time
import traceback

import discord
from discord.ext import commands
from discord.utils import get
from dotenv import load_dotenv
from pandas import read_csv

import exceptions

load_dotenv()
import mongo_db_functions

check_table = read_csv("entries.csv")


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


async def is_worker(ctx):
    return ctx.author.id in [664401331250921473, 438281883881701391]


@client.command(help="Register for Make4thon")
async def register(ctx, team_name: str, email_address: str):
    guild = ctx.guild
    role_register = discord.utils.get(guild.roles, name="Registered")
    if role_register in ctx.author.roles:
        raise exceptions.BrokenRequest("You are already registered for a team.")
    email_address = email_address.lower()
    try:
        index_of_person = check_table["email_address"][check_table["email_address"] == email_address].index[0]
        if check_table.iloc[index_of_person]['team_name'].lower() == team_name.lower():
            need_role = mongo_db_functions.add_team(team_name=team_name, member_id=ctx.author.id, role_id=0)
            if need_role == 1:
                role = await guild.create_role(name=team_name,
                                               colour=discord.Colour.from_rgb(r=random.randint(0, 255),
                                                                              g=random.randint(0, 255),
                                                                              b=random.randint(0, 255)))
                await ctx.author.add_roles(role)
                mongo_db_functions.teams.update_one({"_id": team_name.lower()}, {"$set": {'role_id': role.id}})
                category = get(guild.categories, name='Channels')  # TODO: Change Category name
                overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False),
                              ctx.author: discord.PermissionOverwrite(read_messages=True),
                              get(guild.roles, id=942775012983717948): discord.PermissionOverwrite(read_messages=True),
                              role: discord.PermissionOverwrite(
                                  read_messages=True)}  # TODO: Change ID to Coordinator role
                # Text channel
                await guild.create_text_channel(team_name, overwrites=overwrites, category=category)
                # Voice channel
                await guild.create_voice_channel(team_name, overwrites=overwrites, category=category)
            else:
                role = get(guild.roles, name=team_name)
                await ctx.author.add_roles(role)

            await ctx.send(f"You have successfully registered for team {team_name}")
            await ctx.author.add_roles(role_register)

        else:
            raise exceptions.BrokenRequest(
                message="Your Email Address matches, but team name doesn't. please make sure it is spelt correctly")

    except IndexError:
        raise exceptions.BrokenRequest(
            message="Email not found in database. If the issue persists please call an admin")


@client.command(help="Add someone new to a particular team\nAdding Someone New: `add`, `a`, `+`\nRemoving Someone "
                     "from a team: `remove`, `rem`, `r`, `-`")
@commands.has_role(942775012983717948)  # TODO: Change to Cordinator Role
async def alter(ctx, flag, member: discord.Member, team_role: discord.Role):
    if flag in ['add', 'a', '+']:
        if team_role in member.roles:
            raise exceptions.BrokenRequest(message=f"{member.display_name} is already part of the team")
        else:
            role_register = discord.utils.get(ctx.guild.roles, name="Registered")
            await member.add_roles(team_role)
            await member.add_roles(role_register)
            mongo_db_functions.teams.update_one({"_id": team_role.name.lower()}, {"$push": {"member_id": member.id}})
            await ctx.send(f"{member.display_name} added to {team_role.name}")
    elif flag in ['remove', 'rem', 'r', '-']:
        if team_role not in member.roles:
            raise exceptions.BrokenRequest(message=f"{member.display_name} is not part of this team")
        else:
            role_register = discord.utils.get(ctx.guild.roles, name="Registered")
            await member.remove_roles(team_role)
            await member.remove_roles(role_register)
            mongo_db_functions.teams.update_one({"_id": team_role.name.lower()}, {"$pull": {"member_id": member.id}})
            await ctx.send(f"{member.display_name} removed from {team_role.name}")
    else:
        raise exceptions.BrokenRequest(
            message="Incorrect Usage of `Flag` please use the flags mentioned in the help command.")


@client.command(help='Download all data in the form of a CSV')  # DM send
@commands.check(predicate=is_worker)
async def download(ctx):
    path = f"CSV_Storage/{ctx.author.display_name}-{int(datetime.datetime.now(datetime.timezone.utc).timestamp())}.csv"
    with open(path, 'w') as csv:
        all_data = list(mongo_db_functions.teams.find())
        csv.write("Team Name,Members Seperated with Pipes,Role ID\n")
        for item in all_data:
            try:
                csv.write(
                    f"{item['_id']},{' | '.join(map(str, item['member_id']))},{str(item['role_id'])}\n")
            except KeyError:
                pass
    await ctx.message.delete()
    await ctx.author.send(file=discord.File(path))
    os.remove(path)


@client.command(help='Get Bot and Database Latency\nAccess: Everyone')
async def ping(ctx):
    bot_latency = f"{round(client.latency * 1000, 2)} ms"
    await ctx.send(
        embed=discord.Embed(
            title='You have been Ponged',
            description=f'Bot Latency: {bot_latency}\nDatabase Latency: {mongo_db_functions.calculate_ping()[0]}\n'
                        f'Write Latency [MongoDB]: {mongo_db_functions.calculate_ping()[1]}\nRead Latency [MongoDB]: '
                        f'{mongo_db_functions.calculate_ping()[2]}',
            colour=discord.Colour(0x63e916)
        )
    )


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
