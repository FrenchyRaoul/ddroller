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
        self.user_ids = None
        self.rd = None

    async def on_ready(self):
        if len(self.guilds) != 1:
            raise Exception('not connected to 1 guild')
        assert str(self.guilds[0]) == GUILD
    
        print(f'{self.user} has connected to Discord')
        print(f'Connected to {client.guilds[0]}')

        self.rd = Rolodex.load()
        print(f'Loaded {len(self.rd)} characters')

        try:
            with open('usersids.p', 'rb') as fin:
                self.user_ids = pickle.load(fin)
        except:
            self.user_ids = dict()

    async def on_message(self, message):

        if (uid := message.author.id) not in self.user_ids:
            self.user_ids[uid] = set()
        if (name := message.author.name) not in (nameset := self.user_ids[message.author.id]):
            nameset.add(name)
            with open('userids.p', 'wb') as fout:
                pickle.dump(self.user_ids, fout)

        if message.author == self.user:
            return

        if message.content in (None, '') or message.content[0] != '!':
            return

        cmd, *args = message.content.lower().split()

        if cmd == '!roll':
            await message.channel.send(self.bot_roll(args))
            return

        elif cmd == '!character':
            await message.channel.send(self.bot_character(args, message))
            return

        elif cmd == '!list':
            await message.channel.send(f'{", ".join(self.rd.characters)}')

        elif cmd in [f'!{name.lower()}' for name in self.rd.characters]:
            charname = cmd[1:]
            try:
                character = self.rd.get_character(str(message.author.id), charname)
                if len(args) == 0:
                    await message.channel.send(str(character))
                elif args[0] == 'roll':
                    await message.channel.send(self.character_roll(charname, character, args))

                elif args[0] in FULL_SKILLLIST:
                    await message.channel.send(character.explain_modifier(args[0]))

                elif args[0] == 'update':
                    await message.channel.send(self.update_character(args, charname, character))

            except PermissionError:
                await message.channel.send(f'You do not have permission to use {charname.title()}')

        else:
            await message.channel.send("There is no command or character by this name")

    def bot_roll(self, args) -> str:
        if len(args) == 0:
            return f"1d20:  **{roll()[0]}**"
        elif args[0] in ADVANTAGE:
            return roll_d20_adv()
        elif args[0] in DISADVANTAGE:
            return roll_d20_dis()
        else:
            match = ROLL_REGEX.match(args[0])
            if match:
                n = int(match['n']) if match['n'] else 1
                d = int(match['d'])
                mod = int(match['mod']) if match['mod'] else 0
                if n > 15:
                    return "How about you don't roll so many dice"
                if d > 10e10:
                    return "Too many sides, this die just rolls around"

                total, vals = roll(d, n, mod=mod)
                return format_rolls(d, n, vals, [mod], total)
            else:
                return "I do not understand this roll command"

    def bot_character(self, args, message) -> str:
        if len(args) == 0:
            return f'You must provide arguments: new update'
        if args[0] == 'new':
            try:
                newchar = Character(args[1], args[2], *map(int, args[3:]))
                self.rd.add_character([str(message.author.id), OWNER], newchar)
                self.rd.store()
            except Exception as e:
                return f'failed to create character: {e}'

    def character_roll(self, charname, character, args) -> str:
        if len(args) == 1:
            return str(roll()[0])

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
            total, vals = func(mod=mod)
            return f'**{total}**  *{charname.title()} rolled a {args[1].lower()} {"save" if save else "check"}{adv_dis}.*'

    def update_attribute(self, charname, character, args) -> str:
        if len(args) == 2:
            return f"What should I update {args[1]} to?"
        else:
            try:
                newval = int(args[2])
            except ValueError:
                return "Attribute value must be an integer"
            if 0 > newval > 20:
                return "Attribute must be between 0 and 20, inclusive."
            attr = ATTR.get(args[1], args[1])  # convert str to strength, int to intelligence, etc
            setattr(character, attr, newval)
            self.rd.store()
            return f"Updated {charname.title()}'s {attr.title()} to {newval}"

    def update_proficiency(self, args, character) -> str:
        if len(args) == 2:
            return f'What skill should be added/removed from the proficiency list?'
        elif (skill := args[2].lower()) in SKILL or args[2].lower() in ATTR_FLAT:
            if skill in character.proficiencies:
                character.proficiencies.remove(skill)
                self.rd.store()
                return f"{skill} removed from proficiency list."
            else:
                character.add_proficiency(skill)
                self.rd.store()
                return f"{skill} added to proficiency list"
        else:
            return f'{args[2]} is not a skill, is there a typo'

    def update_class(self, args, character) -> str:
        if len(args) == 2:
            return f'What class do you want me to update?'
        elif len(args) == 3:
            return f'You must provide a level (0 to delete)'
        else:
            character.update_class(args[2], int(args[3]))
            self.rd.store()
            return f"I successfully updated {character.name}'s class to {args[2]} {int(args[3])}"

    def update_skill_mod(self, args, character):
        if len(args) == 2:
            return f'what skill do you want to modify?'
        if len(args) < 5:
            return f'Skill Mod format: !char update skillmod <modname> <skillname> <integer or "prof">'
        else:
            name = args[2]
            skill = args[3]
            if args[4] == 'prof':
                character.create_skill_modifier(skill, name=name, add_prof=True)
            else:
                character.create_skill_modifier(skill, name=name, modifier=int(args[4]))
            self.rd.store()
            return "UPDATE ME LATER BUT I UPDATED THE MOD"

    def update_character(self, args, charname, character) -> str:
        if len(args) == 1:
            return f'What am I supposed to update?'

        elif args[1] in ATTR_FLAT:
            return self.update_attribute(charname, character, args)

        elif args[1] == 'proficiency':
            return self.update_proficiency(args, character)

        elif args[1] == 'class':
            return self.update_class(args, character)

        elif args[1] == 'skillmod':
            return self.update_skill_mod(args, character)


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
