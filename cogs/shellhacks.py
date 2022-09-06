import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
from pyairtable import Table
from pyairtable.formulas import match
from collections.abc import Sequence
import firebase_admin
from firebase_admin import db
from firebase_admin import credentials

load_dotenv()
airtable_api_key = os.environ["AIRTABLE_API_KEY"]
shellhacks_base_id = os.environ["SHELLHACKS_BASE_ID"]
shellhacks_firebase_key = os.environ["SHELLHACKS_FIREBASE_KEY"]

class ShellHacks(commands.Cog):

    '''
    Commands specifically designed to tackle logistical needs for UPE Shellhacks
    '''

    def __init__(self, bot):
        self.bot = bot

        #Firebase
        cred = credentials.Certificate({    
            "projectId": "shellhacks2022",
            "clientEmail": "firebase-adminsdk-fz1lg@shellhacks2022.iam.gserviceaccount.com",
            "privateKey": shellhacks_firebase_key
        })
        firebase_admin.initialize_app(cred, {
            'databaseURL' : 'https://shellhacks2022-default-rtdb.firebaseio.com'
        })

        #Roles/Identities
        self.MODERATOR_ROLE_ID = 399551100799418370 
        self.ORGANIZER_ROLE_ID = 888960305693069402 
        self.EBOARD_ROLE_ID = 399558426511802368
        self.SHELL_COMMITTEE_ROLE_ID = 523306918727385088
        self.GUI_USER_ID = 675403234172731393
        self.HACKER_ROLE_NAME = "ShellHacks Hacker"
        self.MENTOR_ROLE_NAME = "ShellHacks Mentor"
        self.SPONSOR_ROLE_NAME = "ShellHacks Sponsor"
        self.HACKER_ROLE_ID = 888957354417192960
        self.MENTOR_ROLE_ID = 888959725037846578
        self.SPONSOR_ROLE_ID = 758159745872953374

        #Channels
        self.CHECKING_MESSAGE_ID = 889331203788914781
        self.CHECKIN_CHANNEL_ID = 888987697442590740
        self.CHECKING_MESSAGE_ID = 889331203788914781
        self.MENTOR_CHANNEL_ID = 888969040641540146
        self.TEXT_TEMPLATE_CHANNEL_ID = 888979710435029022
        self.VOICE_TEMPLATE_CHANNEL_ID = 891129451658760222
        self.BOT_LOGS_CHANNEL_ID = 626541886533795850
        self.log_channel = self.bot.get_channel(self.BOT_LOGS_CHANNEL_ID)
        self.channels_dict = {}

        #Airtable
        self.hacker_database = Table(airtable_api_key, shellhacks_base_id, '2021 Application')
        self.company_database = Table(airtable_api_key, shellhacks_base_id, '2021 Logistics Forms')
        #Colors HEX and Emojis
        self.GREEN_HEX = 0x238823 
        self.RED_HEX = 0xD2222D
        self.SHELL_EMOJI = "<:upeshellhacks:753692446621433927>"

        #Strings & URLS
        self.HACKER_GUIDE_SHORTENED_URL = "https://go.fiu.edu/Shell2022HackerGuide"
        self.HACKER_GUIDE_URL = "https://upefiu.notion.site/ShellHacks-2022-Hacker-Guide-eca293e75b8d432baf7f410129547dac"
        self.SCHEDULE_SHORTENED_URL = "https://go.fiu.edu/shellhacksschedule"
        self.SHELLHACKS_DASHBOARD_URL = "https://www.shellhacks.net/dashboard"
        self.HACKER_PRIMER = f"Welcome to ShellHacks 2022! We highly recommend you check out the hacker guide at {self.HACKER_GUIDE_SHORTENED_URL}\nIt contains answers to frequently asked questions and essential information to help make the most of your experience at ShellHacks!"
        self.MENTOR_PRIMER = f"Welcome ShellHacks! Feel free to hang out and ask questions in the #mentors-lounge channel.\nWhenever a hacker is in need of help, __a new #ticket channel__ will appear at the bottom of the ShellHacks category.\nWe encourage you to resolve the ticket by replying in that ticket's channel"
        self.SPONSOR_PRIMER = f"Welcome to ShellHacks! Feel free to have a conversation with our other sponsors and ask our organizers questions at the #sponsor-lounge channel.\n__There are also channels for each company__ where our hackers can ask questions about your company, or your products!"
        self.GENERIC_PRIMER = f'Welcome to UPE, and welcome to ShellHacks!\nIf you have confirmed your attendance and are here for ShellHacks, remember to check-in by going to the #check-in channel in the ShellHacks category.\nYou can also click on this link: https://discord.com/channels/245393533391863808/888987697442590740/889331203788914781 to be directed to the #check-in channel!\nTo check-in, make sure you __react to the message by clicking on the ShellHacks {self.SHELL_EMOJI} emoji__ !'

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id == self.CHECKING_MESSAGE_ID:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            found = False

            initial_message = f'Welcome to ShellHacks 2022! {self.SHELL_EMOJI}\nPlease provide me with the code on your ShellHacks profile dashboard at {self.SHELLHACKS_DASHBOARD_URL}.'
            send_initial_message = await member.send(initial_message)
            
            while not found:
                message_response = await self.bot.wait_for('message', check=message_check(channel=member.dm_channel))
                code = message_response.content

                ref = db.collection('hackers').document({code.strip()})
                snapshot = ref.get()

                if snapshot.exists:
                    found = True
                    data = snapshot.to_dict()

                    try:
                        if data['isAccepted'] == True:
                            if data['isConfirmed' == True]:
                                if data['acceptedAttendance'] == 'In-Person':
                                    if data['isCheckedIn'] == True:
                                        if data.has_key('discord') and data['discord'] != '':
                                            # Send message letting them know they should have roles
                                            initial_reply = "The hacker tied to the given code has already received the appropriate roles. If this was not you, please visit the registration table to sort out this issue."
                                            send_initial_reply = await member.send(initial_reply)
                                        else:
                                            # Give Hacker role
                                            hacker_role = discord.utils.get(guild.roles, name=self.HACKER_ROLE_NAME)
                                            await member.add_roles(hacker_role)
                                            # Give In-Person role

                                            # Store Discord user ID (to track down who got the roles in case of identity theft >:( )
                                            ref.update({'discord': member.id})
                                            # Send message letting them know it succeeded
                                            final_reply = "You're all set!\n"
                                            final_reply += self.HACKER_PRIMER
                                            final_reply += f"\nHappy Hacking~! {self.SHELL_EMOJI}"
                                            send_final_reply = await member.send(final_reply)

                                            await self.log_channel.send(f'{self.SHELL_EMOJI} {member.mention} has **checked-in** to ShellHacks 2022!')
                                    else:
                                        initial_reply = "You have not been checked-in in-person. Please do so at the registration table"
                                        send_initial_reply = await member.send(initial_reply)
                                else:
                                    if data['isCheckedIn'] == True:
                                        initial_reply = "You have already checked in as a virtual hacker."
                                        send_initial_reply = await member.send(initial_reply)    
                                    else:
                                        # Check-In update
                                        ref.update({'isCheckedIn': True})
                                        # Give Hacker role
                                        hacker_role = discord.utils.get(guild.roles, name=self.HACKER_ROLE_NAME)
                                        await member.add_roles(hacker_role) 
                                        #Give Remote role

                                        # Send message letting them know it succeeded
                                        final_reply = "You're all set!\n"
                                        final_reply += self.HACKER_PRIMER
                                        final_reply += f"\nHappy Hacking~! {self.SHELL_EMOJI}"
                                        send_final_reply = await member.send(final_reply)

                                        await self.log_channel.send(f'{self.SHELL_EMOJI} {member.mention} has **checked-in** to ShellHacks 2022!')
                            else:
                                initial_reply = f'You have not confirmed your attendance as a hacker. Please do so at {self.SHELLHACKS_DASHBOARD_URL}'
                                send_initial_reply = await member.send(initial_reply)     
                        else:
                            initial_reply = "You are not an accepted hacker."
                            send_initial_reply = await member.send(initial_reply)                        
                    except KeyError:
                        initial_reply = "There was an issue retrieving your information."
                        send_initial_reply = await member.send(initial_reply)      

                else:
                    initial_reply = "I could not find a matching code. Make sure to provide only the code on your dashboard from the ShellHacks website."
                    send_initial_reply = await member.send(initial_reply)
    
    @commands.Cog.listener()
    async def on_message(self, payload):
        if payload.channel.id == self.MENTOR_CHANNEL_ID or payload.channel.id == self.CHECKIN_CHANNEL_ID:
            if payload.author.id == self.bot.user.id or payload.author.id == self.GUI_USER_ID:
                return
            else:
                await payload.delete()
                
        if payload.author.id == self.bot.user.id:
            return
        if not payload.guild:
            try:
                if payload.content == "<:pineappleemoji:798036434320621579>":
                    await payload.channel.send("Ding ding ding!")
                    await payload.channel.send("<a:blobcookie:799276646586646528>") 
                    await payload.channel.send("I was just feeling lonely and a tiny bit bored.")
                    await payload.channel.send("I'm glad you reached it out however!")
                    await payload.channel.send("I've logged your completion of my little challenge...")
                    await payload.channel.send("<a:blobdance:430822490747437056>")
                    await self.log_channel.send(f'{self.SHELL_EMOJI} {payload.author.mention} has completed the **Finding Gui Challenge**')
            except discord.errors.Forbidden:
                pass
        else:
            pass

    @commands.command()    
    async def ticket(self, ctx):
        '''
        Creates a #ticket channel for the author where they can recieve dedicated attention. Ex: ?ticket
        Only works in the #mentor-help channel.
        '''
        create_ticket_channel = self.bot.get_channel(self.MENTOR_CHANNEL_ID)
        if ctx.channel != create_ticket_channel:
            return
        guild = ctx.guild
        text_template_channel = guild.get_channel(self.TEXT_TEMPLATE_CHANNEL_ID)
        voice_template_channel = guild.get_channel(self.VOICE_TEMPLATE_CHANNEL_ID)

        name = ctx.author.name.replace(' ', '-')
        ticket_channel = await text_template_channel.clone(name='📑│ticket-' + name)
        voice_ticket_channel = await voice_template_channel.clone(name='💡│ticket-' + name)

        self.channels_dict[ticket_channel.id] = voice_ticket_channel.id

        await ticket_channel.set_permissions(target=ctx.author, read_messages=True, send_messages=True, read_message_history=True)
        await voice_ticket_channel.set_permissions(target=ctx.author, connect=True, speak=True, view_channel=True)

        await ticket_channel.send(ctx.author.mention + ', howdy! Thank you for making a new ticket, **type below what you need help with** and a mentor will be with you shortly. Once your concern has been resolved, you can close this ticket by using the `?close` command!')
        await ctx.message.delete()

    @commands.command()    
    async def close(self, ctx):
        '''
        Closes a #ticket channel Ex: ?ticket
        Only works inside #ticket channels.
        '''
        if 'ticket' in ctx.channel.name and ctx.channel.id != self.MENTOR_CHANNEL_ID and ctx.channel.id != self.TEXT_TEMPLATE_CHANNEL_ID:
            voice_ticket_channel = ctx.guild.get_channel(self.channels_dict[ctx.channel.id])
            self.channels_dict.pop(ctx.channel.id)
            await ctx.channel.delete()
            await voice_ticket_channel.delete()
            print("Channel closed.")
        else:
            await ctx.send("Sorry, this command only works for ticket channels")

    @commands.command()    
    async def gethacker(self, ctx, hacker_email):
        '''
        Used to fetch a hacker record based on email address from Shell DB.\nEx: ?gethacker roary@fiu.edu
        '''
        if not is_allowed(ctx, ctx.author): 
            return

        author_roles = ctx.author.roles
        mod_role = ctx.guild.get_role(self.MODERATOR_ROLE_ID)
        organizer_role = ctx.guild.get_role(self.ORGANIZER_ROLE_ID)
        response_title = None
        response_description = f"<a:utilfailure:809713365088993291> Hacker record could not be found..."
        embed_color = self.RED_HEX
        success = False

        if (mod_role not in author_roles) and (organizer_role not in author_roles):
            response_description += f'{ctx.author.mention} this command is only meant to be used by Moderators or Shell Directors'
        else:
            by_email = match({"lowercase-emails": hacker_email.strip().lower()})
            response = self.hacker_database.first(formula=by_email)
            if(response != None):
                success = True
                hacker_record = response["fields"]
                response_description = f"ID: {hacker_record['Application ID']}"
                response_title = "Hacker Record <a:verified:798786443903631360>"
                embed_color = self.GREEN_HEX

        embed_response = discord.Embed(title=response_title, description=response_description, color=embed_color)
        if success:
            embed_response.add_field(name=f"Name", value=hacker_record['First Name'] + " " + hacker_record['Last Name'], inline=False)
            embed_response.add_field(name=f"Email", value=hacker_record['E-mail Address'], inline=False)
            embed_response.add_field(name=f"Country", value=hacker_record['Country'], inline=False)
            embed_response.add_field(name=f"Status", value=hacker_record['Acceptance Status'], inline=False)
            try:
                embed_response.add_field(name=f"Confirmed", value=hacker_record['Confirmed'], inline=False)
            except KeyError:
                embed_response.add_field(name=f"Confirmed", value=False, inline=False)
            try:
                embed_response.add_field(name=f"Checked In", value=hacker_record['Checked In'], inline=False)
            except KeyError:
                embed_response.add_field(name=f"Checked In", value=False, inline=False)
            
        await ctx.send(embed=embed_response)

    @commands.command()    
    async def guide(self, ctx):
        '''
        Used to peek into the hacker guide for ShellHacks 2021.\nEx: ?guide
        '''
        await ctx.channel.send(self.HACKER_GUIDE_SHORTENED_URL)

    @commands.command()    
    async def schedule(self, ctx):
        '''
        Used to peek into the schedule for ShellHacks 2021.\nEx: ?guide
        '''
        await ctx.channel.send(self.SCHEDULE_SHORTENED_URL)

    @commands.command()    
    async def scan_sponsors(self, ctx):
        '''
        Used to scan server for ShellHacks 2021 sponsors and assign them the appropiate roles and nicknames.\nEx: ?sponsors
        '''  
        if not self.is_allowed(ctx, ctx.author): 
            return

        sponsor_role = discord.utils.get(ctx.guild.roles, name=self.SPONSOR_ROLE_NAME)

        with_discord = match({"Type": "Discord Username"})
        response = self.company_database.all(formula=with_discord)

        for sponsor_record in response:
            user = ctx.guild.get_member_named(sponsor_record["fields"]["Discord Username"])
            if user:
                try:
                    if sponsor_role not in user.roles:
                        full_name = sponsor_record["fields"]["Full Name"]
                        company = sponsor_record["fields"]["Company"]
                        await user.edit(nick = full_name + " | " + company)
                        await user.add_roles(sponsor_role)
                        self.company_database.update(sponsor_record["id"], {"In Server": True})
                        print(f"New sponsor located: {user}")
                        await self.log_channel.send(f'{self.SHELL_EMOJI} A wild **sponsor** appeared! {user.mention} from {company} is here for ShellHacks 2021!')
                    else:
                        print(f"Previously located sponsor: {user}")
                except:
                    print(f"Missing Permissios for: {user}")
            else: 
                print("Sponsor not found...")

    @commands.command()    
    async def scan_organizers(self, ctx):
        '''
        Used to scan server for ShellHacks 2021 sponsors and assign them the appropiate roles and nicknames.\nEx: ?sponsors
        '''  
        if not self.is_allowed(ctx, ctx.author): 
            return

        eboard_role = ctx.guild.get_role(self.EBOARD_ROLE_ID)
        committee_role = ctx.guild.get_role(self.SHELL_COMMITTEE_ROLE_ID)
        organizer_role = ctx.guild.get_role(self.ORGANIZER_ROLE_ID)
        for member in ctx.guild.members:
            if eboard_role in member.roles or committee_role in member.roles:
                await member.add_roles(organizer_role) 

    @commands.command()    
    async def primer(self, ctx, user: discord.Member = None):
        '''
        Used to send a primer to the passed user relevant to their ShellHacks role.\nEx: ?primer @roary#0001
        '''  
        if not self.is_allowed(ctx, ctx.author): 
            return

        if user == None:
            user = ctx.author

        roles = user.roles
        hacker_role = ctx.guild.get_role(self.HACKER_ROLE_ID)
        mentor_role = ctx.guild.get_role(self.MENTOR_ROLE_ID)
        sponsor_role = ctx.guild.get_role(self.SPONSOR_ROLE_ID)

        if hacker_role in roles:
            primer_message = f'Hi {user.mention}!\n' + self.HACKER_PRIMER
        elif mentor_role in roles:
            primer_message = f'Hi {user.mention}!\n' + self.MENTOR_PRIMER
        elif sponsor_role in roles:
            primer_message = f'Hi {user.mention}!\n' + self.SPONSOR_PRIMER
        else:
            primer_message = f'Hi {user.mention}!\n' + self.GENERIC_PRIMER 
        
        send_initial_message = await user.send(primer_message)
    
    @commands.command()    
    async def edit_checkin(self, ctx, new_message):  
        if not self.is_allowed(ctx, ctx.author): 
            return  

        channel = self.bot.get_channel(self.CHECKIN_CHANNEL_ID)
        original_message = await channel.fetch_message(self.CHECKING_MESSAGE_ID)
        await original_message.edit(content=new_message)


    def is_allowed(self, ctx, user: discord.Member):
        roles = user.roles
        mod_role = ctx.guild.get_role(self.MODERATOR_ROLE_ID)
        organizer_role = ctx.guild.get_role(self.ORGANIZER_ROLE_ID)

        return True if organizer_role in roles or mod_role in roles else False

# auxiliary function for the message_check function to make a string sequence of the given parameter
def make_sequence(seq):
    if seq is None:
        return ()
    if isinstance(seq, Sequence) and not isinstance(seq, str):
        return seq
    else:
        return (seq,)

# function to make logical checks when receiving DMs
def message_check(channel=None, author=None, content=None, ignore_bot=True, lower=True):
    channel = make_sequence(channel)
    author = make_sequence(author)
    content = make_sequence(content)
    if lower:
        content = tuple(c.lower() for c in content)
    # check that the sender of DM is the same as the receiver of the original DM from bot
    def check(message):
        if ignore_bot and message.author.bot:
            return False
        if channel and message.channel not in channel:
            return False
        if author and message.author not in author:
            return False
        actual_content = message.content.lower() if lower else message.content
        if content and actual_content not in content:
            return False
        return True
    return check

def setup(bot):
    bot.add_cog(ShellHacks(bot)) 