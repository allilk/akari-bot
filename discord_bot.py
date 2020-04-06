import json, asyncio, requests, datetime
from datetime import timedelta
from os.path import exists

import discord
from discord import *
from discord.client import *
from discord.ext import commands
from discord.ext.commands import has_permissions
from discord.utils import *

client=commands.Bot(command_prefix='>')
client.remove_command("help")
bot_token=#bot token
updates_channel=# channel to post changes too
authorized_servers=[]#authorized servers, if server isnt here, prevents particular commands from running
my_server=# your personal server
my_server_lounge=# your servers main channel
message_counter=0

@client.event
async def on_ready():
    print(f'LOG : Logged in as: {client.user.name} ({client.user.id})')

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account

# SCOPES #
scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/admin.directory.group', 'https://www.googleapis.com/auth/drive.activity.readonly']

# BEGIN GOOGLE AUTH #
def get_creds(credentials,token):
    creds = None
    if exists(token):
        with open(token,'r') as t:
            creds = json_to_cred(t)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials, scopes)
            creds = flow.run_local_server(port=0)
        with open(token,'w') as t:
            json.dump(cred_to_json(creds),t,indent=2)

    return creds
def cred_to_json(cred_to_pass):
    cred_json = {
        'token': cred_to_pass.token,
        'refresh_token': cred_to_pass.refresh_token,
        'id_token': cred_to_pass.id_token,
        'token_uri': cred_to_pass.token_uri,
        'client_id': cred_to_pass.client_id,
        'client_secret': cred_to_pass.client_secret,
    }
    return cred_json
def json_to_cred(json_to_pass):
    cred_json = json.load(json_to_pass)
    creds = Credentials(
        cred_json['token'],
        refresh_token=cred_json['refresh_token'],
        id_token=cred_json['id_token'],
        token_uri=cred_json['token_uri'],
        client_id=cred_json['client_id'],
        client_secret=cred_json['client_secret']
    )
    return creds

creds=get_creds(credentials="credentials.json",token="token.json") # set your files 

group_service=build('admin','directory_v1',credentials=creds)
service=build('drive', 'v3',credentials=creds)
a_service=build('driveactivity', 'v2', credentials=creds)
gsuite_domain=# gsuite domain
user_group=# user group to manage
shared_drive= #specify drive to watch for changes
watched_channel=# channel to repost from
bot_client_id=# your bot client id
key_active=False
# END GOOGLE AUTH #

# BEGIN FUNCTIONS #
async def server_check(guild_id, personal=False):
    await client.wait_until_ready()
    for guild in authorized_servers:
        if personal is False:
            if guild_id == guild:
                return True
        elif personal is True:
            if my_server == guild:
                return True
async def watch_changes(client, file_id):
    await client.wait_until_ready()
    while True:
        await asyncio.sleep(15)
        print("LOG : Scanning for changes...")
        old_cache=json.load(open("cache.json", "r+"))
        act_name=""
        item=service.files().get(fileId=file_id, fields="name, id, parents, size, mimeType, lastModifyingUser", supportsAllDrives=True).execute()
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            act_name='ancestorName'
        else:
            act_name='itemName'
        result_list=a_service.activity().query(body={
            'pageSize':10,
            f'{act_name}':f'items/{file_id}'}).execute()['activities']
        change_list=[]
        total_changes=0
        for activity in result_list:
            timestamp=activity['timestamp']
            targets=activity['targets'][0]
            changed_id=""
            if 'teamDrive' in targets:
                new_target=targets['teamDrive']
                changed_id=(new_target['name']).split('teamDrives/')[1]
            elif 'driveItem' in targets:
                new_target=targets['driveItem']
                changed_id=(new_target['name']).split('items/')[1]
            actions=activity['actions'][0]
            if 'create' in actions['detail']: file_action='Created'
            elif 'delete' in actions['detail']: file_action='Deleted'
            elif 'move' in actions['detail']: file_action='Moved'
            elif 'rename' in actions['detail']: file_action='Renamed'
            elif 'permissionChange' in actions['detail']: file_action='Permissions updated.'
            elif 'restore' in actions['detail']: file_action='Restored from Trash.'
            elif 'edit' in actions['detail']: file_action='Edited.'
            now=datetime.datetime.utcnow()-timedelta(seconds=15)
            message_title=f"File {file_action}!"

            last_user=item['lastModifyingUser']
            if 'photoLink' in last_user:
                user_photo=last_user['photoLink']
            if activity not in old_cache:
                total_changes+=1
                d=activity['timestamp']
                if d.endswith('Z'):
                    d = d[:-1]
                timestamp=datetime.datetime.fromisoformat(d)
                if not timestamp < now and len(total_changes) < 5:
                    print(activity)
                    embed=discord.Embed(title=message_title,description=f"[{new_target['title']}](https://drive.google.com/open?id={changed_id})",color=0x0f0f0f)
                    embed=discord.Embed(title=message_title,description=f"`Content`: [{new_target['title']}](https://drive.google.com/open?id={changed_id})\n`Size`: 0G\n",color=0x0f0f0f)
                    embed.set_footer(text=f"{last_user['displayName']}",icon_url=f"{user_photo}")
                    channel=client.get_channel(updates_channel)
                    await channel.send(embed=embed)
                else:
                    change_list.append(activity)

        with open('cache.json', 'w+') as json_file:
            json.dump(result_list, json_file, indent=1)
@client.event
async def on_message(message):
    #channels to post to
    post_to=[]

    global key_active
    global game_title
    global game_key
    global game_provider
    if message.channel.id == watched_channel and message.author.id != (bot):
        # Repost messages from one channel, to another.
        for c in post_to:
            channel=client.get_channel(c)
            await channel.send(message.content)
    if await server_check(message.guild.id, personal=True) is True and message.channel.id == my_server_lounge and message.author.id != (self): # replace self with the id of your bot(to prevent the bot from reposting it's own messages)
        # Gamekey Giveaway every 75 messages
        global message_counter
        if message_counter == 74 and key_active is False:
            message_counter = 0
            channel=client.get_channel(my_server_lounge)
            f = open("steam_cheap.txt", "r")
            c = open("line_counter.txt", "r")
            seek_value=int(c.readlines()[0])-1
            text=f.readlines()
            game_list=[]
            for line in text:
                game_list.append(line)
            key=game_list[seek_value]
            game=key.split(",")
            game_title=game[0]
            game_key=game[1]
            game_provider=game[2]
            embed=discord.Embed(color=0x0000FF,description=f"{game_title} `### Type the game's name to get it! ###`\n{game_provider}")
            c.close()
            c=open("line_counter.txt","w")
            new_value=seek_value+2
            c.write(str(new_value))
            key_active=True
            await channel.send(embed=embed)
        elif key_active is True:
            if message.content == game_title:
                embed=discord.Embed(color=0x0000FF,description=f"{game_title}: `{game_key}`\n{game_provider}")
                user=client.get_user(message.author.id)
                key_active=False
                await user.send(embed=embed)
        else:
            message_counter+=1

    await client.process_commands(message)
# END FUNCTIONS #

# BEGIN COMMANDS
@client.command()
@has_permissions(ban_members=True)
async def list_users(ctx, *, group=None):
    global gsuite_domain
    use_service_admin=group_service
    if await server_check(ctx.message.guild.id) is True:
        email_list=""
        if group is not None:
            result_list=use_service_admin.members().list(groupKey=f'{group}@{gsuite_domain}').execute()['members']
            if result_list:
                for user in result_list:
                    email_list+=user['email']+"\n"
                    embed=discord.Embed(color=0x00FF00,title="List of Users:",description=email_list)
            else:
                embed=discord.Embed(color=0xFF0000,title="A error occurred.")
        else:
            result_list=use_service_admin.groups().list(domain=f'{gsuite_domain}').execute()['groups']
            for group in result_list:
                email_list+=group['email']+"\n"
            embed=discord.Embed(color=0x00FF00,title="Groups:",description=email_list)
        embed.set_author(name="gsuite-discord")
        await ctx.send(embed=embed)
@client.command()
@has_permissions(ban_members=True)
async def add_user(ctx, group=user_group, *, user_email, username=None):
    global gsuite_domain
    use_service_admin=group_service
    if await server_check(ctx.message.guild.id) is True:
        result_list=use_service_admin.members().list(groupKey=f'{group}@{gsuite_domain}').execute()['members']
        if user_email in result_list:
            embed=discord.Embed(color=0xFF0000,description="Member/Email already exists in this group.")
        else:
            new_user={'email':user_email}
            result=use_service_admin.members().insert(groupKey=f'{group}@{gsuite_domain}',body=new_user).execute()
            embed=discord.Embed(color=0x00FF00,description=f"Member added: `{result['email']}` to user group.")
        embed.set_author(name="gsuite-discord")
        await ctx.send(embed=embed)
@client.command()
@has_permissions(ban_members=True)
async def remove_user(ctx, *, user_email):
    global gsuite_domain
    use_service_admin=group_service
    if await server_check(ctx.message.guild.id) is True:
        result=use_service_admin.members().delete(groupKey=f'{user_group}@{gsuite_domain}',memberKey=user_email).execute()
        await asyncio.sleep(2)
        if not result:
            verify_removed=use_service_admin.members().list(groupKey=f'{user_group}@{gsuite_domain}').execute()
            email_list=[member['email'] for member in verify_removed['members']]
            if user_email in email_list:
                embed=discord.Embed(color=0xFF0000,description=f"ERROR: `{user_email}` still exists in user list")
            else:
                embed=discord.Embed(color=0x00FF00,description=f"`{user_email}` was successfully removed.")
        embed.set_author(name="gsuite-discord")
        await ctx.send(embed=embed)
@client.command()
@has_permissions(manage_roles=True)
async def give_role(ctx, user: discord.Member, give_role: discord.Role):
    await user.add_roles(give_role)
@client.command()
@has_permissions(manage_roles=True)
async def remove_role(ctx, user: discord.Member, give_role: discord.Role):
    await user.remove_roles(give_role)
@client.command()
@has_permissions(ban_members=True)
async def mute(ctx, user: discord.Member):
    role=discord.utils.get(user.guild.roles, name='Muted')
    if user is None or user is ctx.message.author:
        embed=discord.Embed(color=0xFF0000, description=f'You cannot mute yourself!')
    elif discord.utils.get(user.roles, name='Admin') or discord.utils.get(user.roles, name='Moderator'):
        embed=discord.Embed(color=0xFF0000, description=f'You cannot mute a mod/admin!')
    else:
        await user.add_roles(role)
        embed=discord.Embed(title="**Muted!**", description=f"**{user}** was muted by **{ctx.message.author}**.", color=0x00FF00)
    await ctx.send(embed=embed)
@client.command()
@has_permissions(ban_members=True)
async def unmute(ctx, user: discord.Member):
    if user is None:
        embed=discord.Embed(color=0xFF0000, description=f'No user provided.')
    else:
        embed=discord.Embed(title="**Unmuted!**", description=f"**{user}** was unmuted by **{ctx.message.author}**.", color=0x00FF00)
        role=discord.utils.get(user.guild.roles, name='Muted')
        await user.remove_roles(role)
    await ctx.send(embed=embed)
@client.command()
@has_permissions(ban_members=True)
async def send_message(ctx):
    message=ctx.message.content
    message=message.split(">send_message")[1]
    await client.http.delete_message(ctx.message.channel.id, ctx.message.id)
    await ctx.send(message)
@client.command()
@has_permissions(ban_members=True)
async def edit_message(ctx, msg_id, *, content):
    msg=await ctx.channel.fetch_message(msg_id)
    await msg.edit(content=content)
    await client.http.delete_message(ctx.message.channel.id, ctx.message.id)
@client.command()
@has_permissions(manage_emojis=True)
async def add_emoji(ctx, link=None, *, emoji_name=None):
    if link and emoji_name is not None:
        image=requests.get(link)
        await ctx.guild.create_custom_emoji(name=emoji_name, image=image.content)
        embed=discord.Embed(color=0x00FF00, description="Emoji added successfully.")
        msg=await ctx.send(embed=embed)
        await client.http.delete_message(ctx.message.channel.id, ctx.message.id)
        await asyncio.sleep(2)
        await client.http.delete_message(msg.channel.id, msg.id)
    # await ctx.send(link)
@client.command()
async def guild_check(ctx):
    if await server_check(ctx.message.guild.id) is True:
        embed=discord.Embed(colour=0x00FF00, description="This server is authorized by the bot maker.")
    else:
        embed=discord.Embed(colour=0xFF0000, description="This server is not authorized by the bot maker.")
    await ctx.send(embed=embed)
# END COMMANDS

# # BEGIN EVENTS #
@client.event
async def on_command_error(ctx, error):
    message_desc=str(error)
    if isinstance(error, commands.CommandNotFound):
        embed = None
    else:
        embed=discord.Embed(colour=0xFF0000, description=message_desc)
    await ctx.send(embed=embed)
    
# END EVENTS #

client.loop.create_task(watch_changes(client=client,file_id=shared_drive))
client.run(bot_token)