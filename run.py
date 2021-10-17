# bot.py
import os
import time
import json
import copy
import discord
import asyncio
from datetime import datetime
from pymongo import MongoClient
from discord.ext import commands, tasks

TOKEN = os.getenv('TOKEN')
GUILD = os.getenv('GUILD')
COMMAND_CHANNEL = os.getenv('COMMAND_CHANNEL')
TX_CHANNEL = os.getenv('TX_CHANNEL')
MONGO_URL = os.getenv('MONGO_URL')

auctions = {}
auctions_list = []
ready = False
looping = True

bot = commands.Bot(command_prefix='!')

client = MongoClient(MONGO_URL)
db = client.bensdb
mongo_auctions = db.auctions

def save_auc_history():
    mongo_auctions.replace_one({}, auctions, upsert=True)

def get_auc_history():
    print("Fetching auctions")
    global auctions
    global auctions_list

    db_results = mongo_auctions.find_one({})

    print("Got auctions, db results: " + str(db_results))

    auctions = db_results if db_results is not None and len(db_results.keys()) > 1 else {}

    for key in list(auctions.keys()):
        if key != '_id':
            auctions_list.append(key)

    print("Done fetching")

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
    channel = bot.get_channel(int(a_id))
    auctions[a_id]['active'] = True
    save_auc_history()
    await channel.send("This auction has started. Goodluck!")

async def handle_end(a_id):
    print('auction-' + auctions[a_id]['name'] + ' ended!')

    await update_tx(a_id)

    auctions_list.remove(a_id)
    del auctions[a_id]

    save_auc_history()

    channel = bot.get_channel(int(a_id))
    await channel.send("This auction has ended. Thank you!")

async def run_checks():

    global bot
    global looping
    
    while looping:

        if ready:
            now = datetime.now()

            for a_id in auctions_list[:]:

                if bot.get_channel(int(a_id)) == None:
                    print('Detected removed channel, deleting auction')
                    auctions_list.remove(a_id)
                    del auctions[a_id]
                    save_auc_history()
                    
                else:
                    if now > auctions[a_id]['start'] and now < auctions[a_id]['end'] and auctions[a_id]['active'] == False:
                        await handle_start(a_id)
                    elif now > auctions[a_id]['end']:
                        await handle_end(a_id)
            
            if len(auctions_list) == 0:
                looping = False
        
        await asyncio.sleep(5)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    global ready
    ready = True

@bot.command(name='create', help='Creates a new auction', usage='<name> <price> <increment> <start(yyyy-MM-ddTHH:mm:ss)> <end(yyyy-MM-ddTHH:mm:ss)> <image-url> \n\n -- Note all times are in UTC --')
async def create(ctx, name, price: int, increment: int, start, end, url):
    global looping 

    if (str(ctx.channel.id) == COMMAND_CHANNEL):

        auctionName = "auction-" + name.lower()

        guild = bot.get_guild(int(GUILD))
        existing_channel = discord.utils.get(guild.channels, name=auctionName)
        
        if not existing_channel:

            c = await guild.create_text_channel(auctionName, category=discord.utils.get(guild.categories, name='Auctions'))

            auctions[str(c.id)] = {
                'name': name,
                'price': price,
                'increment': increment,
                'highBid': price,
                'highBidId': None,
                'highBidName': None,
                'start': datetime.strptime(start, "%Y-%m-%dT%H:%M:%S"),
                'end': datetime.strptime(end, "%Y-%m-%dT%H:%M:%S"),
                'active': False,
                'bids': 0
            }

            auctions_list.append(str(c.id))

            await ctx.send("Auction Created!")

            e = discord.Embed(
                title="Auction: " + name,
                description="A new auction has been created for " + name,
                color=0xFF5733
            )

            e.set_thumbnail(url=url)
            e.add_field(name="Reserve Price:", value=str(price)+"ADA", inline=True)
            e.add_field(name="Increment:", value=str(increment)+"ADA", inline=True)
            e.add_field(name = chr(173), value = chr(173), inline=False)
            e.add_field(name="Start time (UTC)", value=datetime.strptime(start, "%Y-%m-%dT%H:%M:%S"), inline=True)
            e.add_field(name="End Time (UTC)", value=datetime.strptime(end, "%Y-%m-%dT%H:%M:%S"), inline=True)
            e.add_field(name = chr(173), value = chr(173), inline=False)
            e.add_field(name="Highest Bidder:", value="---", inline=True)
            e.add_field(name="Price:", value="---", inline=True)
            e.add_field(name = chr(173), value = chr(173), inline=False)
            e.add_field(name="How to participate?", value="!bid " + str(price+10), inline=False)
            e.set_footer(text='Goodluck!')

            msg = await c.send(embed=e)

            auctions[str(c.id)]['embed'] = e.to_dict()
            auctions[str(c.id)]['msg_id'] = msg.id

            save_auc_history()

            if looping == False:
                looping = True
                bot.loop.create_task(run_checks())

        else:
            await reply_error(ctx, "Auction channel already exists")
            
    else: 
        await reply_error(ctx, "Creating auctions is not permitted from this channel")

@bot.command(name='bid', help='Creates a bid', usage='!bid <price>')
async def bid(ctx, price: int):

    now = datetime.now()
    a_id = ctx.channel.id

    if str(a_id) in auctions_list:

        a = auctions[str(a_id)]

        if a['start'] < now and a['end'] > now:
            if price >= (a['highBid'] + a['increment']):

                a['highBid'] = price
                a['highBidId'] = ctx.message.author.id
                a['highBidName'] = ctx.message.author.name
                a['bids'] = a['bids'] + 1

                for field in a['embed']['fields']:
                    if field['name'] == 'Price:':
                        field['value'] = price
                    if field['name'] == 'Highest Bidder:':
                         field['value'] = ctx.message.author.name
                
                save_auc_history()
                
                bid_embed=discord.Embed(title="Bid Accepted!", description=ctx.message.author.name + " placed a bid", color=0x00a113)
                bid_embed.add_field(name="Price:", value=str(price)+"ADA")
                bid_embed.set_footer(text=str(now))

                await ctx.send(embed=bid_embed)

                org_embed_msg = await ctx.fetch_message(a['msg_id'])

                await org_embed_msg.edit(embed=discord.Embed.from_dict(a['embed']))
                
            else:
                await reply_error(ctx, "Min bid is: " + str(a['highBid'] + a['increment']) + "ADA")

        elif a['start'] > now:
           await reply_error(ctx, "This auction has not started yet")

        elif a['end'] < now:
            await reply_error(ctx, "This auction has ended")
        
    else:
        await reply_error(ctx, "This auction is no longer valid")

if __name__ == "__main__":
    get_auc_history()
    bot.loop.create_task(run_checks())
    bot.run(TOKEN)

