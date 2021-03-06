import asyncio
import re
import discord
from random import randint
from typing import List, Union
import pickle

from disc_info import TOKEN, GUILD, OWNER
from character import Character, Rolodex, SKILL, ATTR, ATTR_FLAT, FULL_SKILLLIST

ROLL_REGEX = re.compile(r'(?P<n>\d+)?d?(?P<d>\d+)\+?(?P<mod>\d+)?')
ADVANTAGE = ('adv', 'advantage')
DISADVANTAGE = ('dis', 'disadv', 'disadvantage')

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

        try:
            with open('usersids.p', 'rb') as fin:
                self.userids = pickle.load(fin)
        except:
            self.userids = dict()

    async def on_message(self, message):

        if (uid := message.author.id) not in self.userids:
            self.userids[uid] = set()
        if (name := message.author.name) not in (nameset := self.userids[message.author.id]):
            nameset.add(name)
            with open('userids.p', 'wb') as fout:
                pickle.dump(self.userids, fout)
            

        if message.author == client.user:
            return

        if message.content in (None, '') or message.content[0] != '!':
            return


        cmd, *args = message.content.lower().split()


        if cmd == '!roll':
            if len(args) == 0:
                await message.channel.send(f"1d20:  **{roll()[0]}**")
            elif args[0] in ADVANTAGE:
                await message.channel.send(roll_d20_adv())
            elif args[0] in DISADVANTAGE:
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
                else:
                    await message.channel.send("I do not understand this roll command")

        elif cmd == '!character':
            if len(args) == 0:
                await message.channel.send(f'You must provide arguments: new update')
                return
            if args[0] == 'new':
                try:
                    newchar = Character(args[1], args[2], *map(int, args[3:]))
                    self.rd.add_character([str(message.author.id), OWNER], newchar)
                    self.rd.store()
                except Exception as e:
                    await message.channel.send(f'failed to create characted: {e}')

        elif cmd == '!list':
            await message.channel.send(f'{", ".join(self.rd.characters)}')

        elif cmd in [f'!{name.lower()}' for name in self.rd.characters]:
            charname = cmd[1:]
            try:
                character = self.rd.get_character(str(message.author.id), charname)
                if len(args) == 0:
                    await message.channel.send(str(character))
                elif args[0] == 'roll':
                    
                    if len(args) == 1:
                        await message.channel.send(roll()[0])

                    elif args[1] in list(SKILL.keys()) + list(ATTR_FLAT):
                        adv_dis = ''
                        func = roll
                        save = False
                        for var in args[2:]:
                            if var in ADVANTAGE:
                                func = roll_d20_adv
                                adv_dis = ' with advantage'
                            elif var in DISADVANTAGE:
                                func = roll_d20_dis
                                adv_dis = ' with disadvantage'
                            elif var == 'save':
                                save = True

                        mod = character.get_modifier(args[1])
                        total, vals = roll(mod=mod)
                        await message.channel.send(f'**{total}**  *{charname.title()} rolled a {args[1].lower()} {"save" if save else "check"}{adv_dis}.*')

                elif args[0] in FULL_SKILLLIST:
                    await message.channel.send(character.explain_modifier(args[0]))

                elif args[0] == 'update':
                    
                    if len(args) == 1:
                        await message.channel.send(f'What am I supposed to update?')

                    elif args[1] in ATTR_FLAT:
                        if len(args) == 2:
                            await message.channel.send(f"What should I update {attr[1]} to?")
                        else:
                            try:
                                newval = int(args[2])
                                if 0 > newval > 20:
                                    await message.channel.send("Attribute must be between 0 and 20, inclusive.")
                                attr = ATTR.get(args[1], args[1])  # convert str to strength, int to intelligence, etc
                                setattr(character, attr, newval)
                                self.rd.store()
                                await message.channel.send(f"Updated {charname.title()}'s {attr.title()} to {newval}")
                            except ValueError:
                                await message.channel.send("Attribute value must be an integer")

                    elif args[1] == 'proficiency':
                        if len(args) == 2:
                            await message.channel.send(f'What skill should be added/removed from the proficiency list?')
                        elif (skill := args[2].lower()) in SKILL or args[2].lower() in ATTR_FLAT:
                            if skill in character.proficiencies:
                                character.proficiencies.remove(skill)
                                await message.channel.send(f"{skill} removed from proficiency list.")
                                self.rd.store()
                            else:
                                character.add_proficiency(skill)
                                await message.channel.send(f"{skill} added to proficiency list")
                                self.rd.store()
                        else:
                            await message.channel.send(f'{args[2]} is not a skill, is there a typo')
                    elif args[1] == 'class':
                        if len(args) == 2:
                            await message.channel.send(f'What class do you want me to update?')
                        elif len(args) == 3:
                            await message.channel.send(f'You must provide a level (0 to delete)')
                        else:
                            print('here')
                            character.update_class(args[2], int(args[3]))
                            self.rd.store()

                    elif args[1] == 'skillmod':
                        if len(args) == 2:
                            await message.channel.send(f'what skill do you want to modify?')
                        if len(args) < 5:
                            await message.channel.send(f'Skill Mod format: !char update skillmod <modname> <skillname> <integer or "prof">')
                        else:
                            name = args[2]
                            skill = args[3]
                            if args[4] == 'prof':
                                character.create_skill_modifier(skill, name=name, add_prof=True)
                            else:
                                character.create_skill_modifier(skill, name=name, modifier=int(args[4]))
                            self.rd.store()


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
