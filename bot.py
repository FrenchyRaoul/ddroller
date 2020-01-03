import asyncio
import re
import discord
from random import randint
from typing import List, Union

from disc_info import TOKEN, GUILD, OWNER
from character import Character, Rolodex, SKILL, ATTR

ROLL_REGEX = re.compile(r'(?P<n>\d+)?d?(?P<d>\d+)\+?(?P<mod>\d+)?')


class DDClient(discord.Client):

    def __init__(self):
        super().__init__()
        self.rd = None

    async def on_ready(self):
        if len(client.guilds) != 1:
            raise Exception('not connected to 1 guild')
        assert str(client.guilds[0]) == GUILD
    
        print(f'{client.user} has connected to Discord')
        print(f'Connected to {client.guilds[0]}')

        self.rd = Rolodex.load()
        print(f'Loaded {len(self.rd)} characters')

    async def on_message(self, message):
        if message.author == client.user:
            return

        if message.content in (None, '') or message.content[0] != '!':
            return

        cmd, *args = message.content.split()


        if cmd == '!roll':
            if len(args) == 0:
                await message.channel.send(f"1d20:  **{roll()[0]}**")
            elif args[0] in ('adv', 'dis'):
                if args[0] == 'adv':
                    await message.channel.send(roll_d20_adv())
                else: 
                    await message.channel.send(roll_d20_dis())
            else:
                match = ROLL_REGEX.match(args[0])
                if match:
                    n = int(match['n']) if match['n'] else 1
                    d = int(match['d'])
                    mod = int(match['mod']) if match['mod'] else 0
                    if n > 15:
                        await message.channel.send("How about you don't roll so many dice")
                        return
                    if d > 10e10:
                        await message.channel.send("Too many sides, this die just rolls around")
                        return
                    total, vals = roll(d, n, mod=mod)
                    await message.channel.send(format_rolls(d, n, vals, [mod], total))

        elif cmd == '!character':
            if len(args) == 0:
                await message.channel.send(f'You must provide arguments: new update')
                return
            if args[0] == 'new':
                try:
                    newchar = Character(*args[1:])
                    self.rd.add_character([message.author.name, OWNER], newchar)
                    self.rd.store()
                except Exception as e:
                    await message.channel.send(f'failed to create characted: {e}')

        elif cmd == '!list':
            await message.channel.send(f'{", ".join(self.rd.characters)}')

        elif cmd.lower() in [f'!{name.lower()}' for name in self.rd.characters]:
            charname = cmd[1:]
            try:
                character = self.rd.get_character(message.author.name, charname)
                print(type(character))
                if len(args) == 0:
                    await message.channel.send(str(character))
                elif args[0] == 'roll':
                    
                    if len(args) == 1:
                        await message.channel.send(roll()[0])

                    elif args[1].lower() in SKILL or args[1].lower() in ATTR:
                        adv_dis = ''
                        func = roll
                        save = False
                        for var in args[2:]:
                            if var == 'adv':
                                func = roll_d20_adv
                                adv_dis = ' with advantage'
                            elif var == 'dis':
                                func = roll_d20_dis
                                adv_dis = ' with disadvantage'
                            elif var == 'save':
                                save = True

                        mod = character.get_modifier(args[1])
                        total, vals = roll(mod=mod)
                        await message.channel.send(f'**{total}**  *{charname.title()} rolled a {args[1].lower()} {"save" if save else "check"}{adv_dis}.*')

                elif args[0] == 'update':
                    
                    if len(args) == 1:
                        await message.channel.send(f'What am I supposed to update?')

                    elif args[1] in ATTR:
                        if len(args) == 2:
                            await message.channel.send(f"What should I update {attr[1]} to?")
                        else:
                            try:
                                newval = int(args[2])
                                if 0 > newval > 20:
                                    await message.channel.send("Attribute must be between 0 and 20, inclusive.")
                                setattr(character, args[1], newval)
                                self.rd.store()
                                await message.channel.send(f"Updated {charname.title()}'s {args[1]} to {newval}")
                            except ValueError:
                                await message.channel.send("Attribute value must be an integer")

                    elif args[1] == 'proficiency':
                        if len(args) == 2:
                            await message.channel.send(f'What skill should be added/removed from the proficiency list?')
                        elif (skill := args[2].lower()) in SKILL:
                            if skill in character.proficiencies:
                                character.proficiencies.remove(skill)
                                await message.channel.send(f"{skill} removed from proficiency list.")
                            else:
                                character.add_proficiency(skill)
                                await message.channel.send(f"{skill} added to proficiency list")
                        else:
                            await message.channel.send(f'{args[2]} is not a skill, is there a typo')



            except PermissionError:
                await message.channel.send(f'You do not have permission to use {charname.title()}')

        else:
            await message.channel.send("There is no command or character by this name")


def roll(d=20, n=1, agg=sum, mod=0):
    d = int(d)
    n = int(n)
    results = [randint(1, d) for die in range(n)]
    return agg(results)+mod, results

def roll_d20_adv(mod=0):
    total, rolls = roll(n=2, mod=mod, agg=max)
    return format_rolls(d=20, n=2, total=total, vals=rolls, mods=['adv', mod])

def roll_d20_dis(mod=0):
    total, rolls = roll(n=2, mod=mod, agg=min)
    return format_rolls(d=20, n=2, total=total, vals=rolls, mods=['dis', mod])

def format_rolls(d: int, n: int, vals: List[int], mods=List[Union[str, int]], total=None):
    modstr = ''.join(f'+{str(mod)}' for mod in mods if mod not in (0, '0'))
    return f"{n}d{d}{modstr}:  **{total}**  *({', '.join(map(str, vals))})*"
    


client = DDClient()
client.run(TOKEN)
