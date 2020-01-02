import asyncio
import re
import discord
from random import randint

from disc_info import TOKEN, GUILD, OWNER
from character import Character, Rolodex, SKILL, ATTR


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

        if message.content[0] != '!':
            return

        cmd, *args = message.content.split()


        if cmd == '!roll':
            if len(args) == 0:
                await message.channel.send(f"1d20:  **{roll()[0]}**")
            elif args[0] in ('adv', 'dis'):
                if args[0] == 'adv':
                    await message.channel.send(roll_d20_adv)
                else: 
                    await message.channel.send(roll_d20_dis)
            else:
                if 'd' in args[0]:
                    n, d = args[0].split('d')
                else:
                    n = 1
                    d = args[0]
                n = int(n)
                d = int(d)
                if n > 15:
                    await message.channel.send("How about you don't roll so many dice")
                    return
                if d > 10e10:
                    await message.channel.send("Too many sides, this die just rolls around")
                    return
                rolls = roll(d, n)
                await message.channel.send(f'{n}d{d}:   **{sum(rolls)}**   *({", ".join(str(val) for val in rolls)})*')

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
                        mod = character.get_modifier(args[1])
                        total = roll()[0] + mod
                        await message.channel.send(f'**{total}**  *{charname.title()} rolled {args[1].lower()}.*')

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



            except PermissionError:
                await message.channel.send(f'You do not have permission to use {charname.title()}')

        else:
            await message.channel.send("There is no command or character by this name")


def roll(d=20, n=1):
    d = int(d)
    n = int(n)
    results = [randint(1, d) for die in range(n)]
    return results

def roll_d20_adv():
    rolls = roll(n=2)
    return f"2d20+Adv:   **{max(rolls)}**   *({rolls[0]}, {rolls[1]})*"

def roll_d20_dis():
    rolls = roll(n=2)
    return f"2d20+Dis:   **{min(rolls)}**   *({rolls[0]}, {rolls[1]})*"
    


client = DDClient()
client.run(TOKEN)
