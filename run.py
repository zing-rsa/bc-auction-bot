# bot.py
import os
import time
import discord
import asyncio
from datetime import datetime
from discord.ext import commands, tasks

TOKEN = os.getenv('TOKEN')
GUILD = os.getenv('GUILD')
COMMAND_CHANNEL = os.getenv('COMMAND_CHANNEL')
TX_CHANNEL = os.getenv('TX_CHANNEL')


auctions = {}

auctions_list = []

bot = commands.Bot(command_prefix='!')

async def update_tx(a_id):
    c = bot.get_channel(int(TX_CHANNEL))

    e = discord.Embed(
        title="Auction for " + auctions[a_id]['name'] + " completed.",
        description="",
        color=0xFF5733
    )
    e.add_field(name="Winner:", value=f"{auctions[a_id]['highBidName']}({auctions[a_id]['highBidId']})", inline=True)
    e.add_field(name="Sale Price:", value=f"{auctions[a_id]['highBid']}ADA", inline=True)
    e.add_field(name="Total bids:", value=auctions[a_id]['bids'], inline=False)
    e.set_footer(text=str(datetime.now()))
    
    await c.send(embed=e)


async def reply_error(ctx, e):
    reply = await ctx.message.reply(e)
    time.sleep(2)
    await ctx.message.delete()
    await reply.delete()


async def handle_start(a_id):
    print('auction-' + auctions[a_id]['name'] + ' started!')
    channel = bot.get_channel(a_id)
    auctions[a_id]['active'] = True
    await channel.send("This auction has started! Goodluck!")


async def handle_end(a_id):
    print('auction-' + auctions[a_id]['name'] + ' ended!')

    await update_tx(a_id)

    auctions_list.remove(a_id)
    del auctions[a_id]

    channel = bot.get_channel(a_id)
    await channel.send("This auction has ended! Thank you!")


async def run_checks():
    while True:
        now = datetime.now()

        for a_id in auctions_list[:]:
            if bot.get_channel(a_id) == None:
                print('Detected removed channel, deleting auction')
                auctions_list.remove(a_id)
                del auctions[a_id]
            else:
                if now > auctions[a_id]['start'] and now < auctions[a_id]['end'] and auctions[a_id]['active'] == False:
                    await handle_start(a_id)
                elif now > auctions[a_id]['end']:
                    await handle_end(a_id)

        await asyncio.sleep(5)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

@bot.command(name='create', help='Creates a new auction', usage='<name> <price> <start(yyyy-MM-ddTHH:mm:ss)> <end(yyyy-MM-ddTHH:mm:ss)> <image-url>')
async def create(ctx, name, price: int, start, end, url):

    if (str(ctx.channel.id) == COMMAND_CHANNEL):

        auctionName = "auction-" + name.lower()

        guild = bot.get_guild(int(GUILD))
        existing_channel = discord.utils.get(guild.channels, name=auctionName)
        
        if not existing_channel:

            c = await guild.create_text_channel(auctionName, category=discord.utils.get(guild.categories, name='Auctions'))

            auctions[c.id] = {
                'id': c.id,
                'name': name,
                'price': price,
                'highBid': price,
                'highBidId': None,
                'highBidName': None,
                'start': datetime.strptime(start, "%Y-%m-%dT%H:%M:%S"),
                'end': datetime.strptime(end, "%Y-%m-%dT%H:%M:%S"),
                'active': False,
                'bids': 0
            }

            auctions_list.append(c.id)

            await ctx.send("Auction Created!")

            e = discord.Embed(
                title="Auction: " + name,
                description="A new auction has started for " + name + "!",
                color=0xFF5733
            )

            e.set_thumbnail(url=url)
            e.add_field(name="Reserve Price:", value=str(price)+"ADA", inline=False)
            e.add_field(name="Start time", value=datetime.strptime(start, "%Y-%m-%dT%H:%M:%S"), inline=True)
            e.add_field(name="End Time", value=datetime.strptime(end, "%Y-%m-%dT%H:%M:%S"), inline=True)
            e.add_field(name = chr(173), value = chr(173), inline=False)
            e.add_field(name="Highest Bidder:", value="---", inline=True)
            e.add_field(name="Price:", value="---", inline=True)
            e.add_field(name = chr(173), value = chr(173), inline=False)
            e.add_field(name="How to participate?", value="!bid " + str(price+10), inline=False)
            e.set_footer(text='Goodluck!')

            msg = await c.send(embed=e)

            auctions[c.id]['embed'] = e.to_dict()
            auctions[c.id]['msg'] = msg

        else:
            print("channel already exists")
            ctx.send("Auction channel already exists")
            
    else: 
        print("Use correct channel")


@bot.command(name='bid', help='Creates a bid', usage='!bid <price>')
async def bid(ctx, price: int):

    now = datetime.now()
    a_id = ctx.channel.id

    if a_id in auctions_list:

        a = auctions[a_id]

        if a['start'] < now and a['end'] > now:
            if price > a['highBid']:

                a['highBid'] = price
                a['highBidId'] = ctx.message.author.id
                a['highBidName'] = ctx.message.author.name
                a['bids'] = a['bids'] + 1

                for field in a['embed']['fields']:
                    if field['name'] == 'Price:':
                        field['value'] = price
                    if field['name'] == 'Highest Bidder:':
                         field['value'] = ctx.message.author.name
                
                update_embed=discord.Embed(title="Bid Accepted!", description=ctx.message.author.name + " placed a bid", color=0x00a113)
                update_embed.add_field(name="Price:", value=str(price)+"ADA")
                update_embed.set_footer(text=str(now))

                await ctx.send(embed=update_embed)

                await a['msg'].edit(embed=discord.Embed.from_dict(a['embed']))
                
            else:
                await reply_error(ctx, "Min bid is: " + str(a['highBid'] + 1) + "ADA")

        elif a['start'] > now:
           await reply_error(ctx, "This auction has not started yet")

        elif a['end'] < now:
            await reply_error(ctx, "This auction has ended")
        
    else:
        await reply_error(ctx, "This auction has ended")

bot.loop.create_task(run_checks())
bot.run(TOKEN)





