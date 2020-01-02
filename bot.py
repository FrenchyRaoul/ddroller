import re

from disc_info import TOKEN, GUILD
import discord
from random import randint


class DDClient(discord.Client):

    async def on_ready(self):
        if len(client.guilds) != 1:
            raise Exception('not connected to 1 guild')
        assert str(client.guilds[0]) == GUILD
    
        print(f'{client.user} has connected to Discord')
        print(f'Connected to {client.guilds[0]}')

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
                rolls = roll(n=2)
                if args[0] == 'adv':
                    await message.channel.send(f"2d20+Adv:   **{max(rolls)}**   *({rolls[0]}, {rolls[1]})*")
                else: 
                    await message.channel.send(f"2d20+Dis:   **{min(rolls)}**   *({rolls[0]}, {rolls[1]})*")
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

def roll(d=20, n=1):
    d = int(d)
    n = int(n)
    results = [randint(1, d) for die in range(n)]
    return results


client = DDClient()
client.run(TOKEN)
