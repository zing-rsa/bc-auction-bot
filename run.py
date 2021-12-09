# bot.py
import os
import time
import json
import copy
import discord
import asyncio
from datetime import datetime, timedelta
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

async def reply_error_delete(ctx, e):
    reply = await ctx.message.reply(e)
    time.sleep(2)
    await ctx.message.delete()
    await reply.delete()

async def reply_error(ctx, e):
    await ctx.message.reply(e)

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
            
            for a_id in auctions_list[:]:

                now = datetime.now()

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
        
        await asyncio.sleep(2)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    global ready
    ready = True

@bot.command(name='create', help='This command is used to create a new auction.\n\nNOTE:\n1. All arguments are required, execpt for image-url\n2. Dates are expected in the UTC timezone\n3. Please make sure to include the "T" between the date and time\n4. To delete an auction you can just delete the channel', usage='<name> <price> <increment> <start(yyyy-MM-ddTHH:mm:ss)> <end(yyyy-MM-ddTHH:mm:ss)> <image-url>')
async def create(ctx, name, price: int, increment: int, start, end, url='none'):
    global looping 

    if (str(ctx.channel.id) == COMMAND_CHANNEL):

        auctionName = "auction-" + name.lower()

        guild = bot.get_guild(int(GUILD))
        existing_channel = discord.utils.get(guild.channels, name=auctionName)
        
        if not existing_channel:

            c = await guild.create_text_channel(auctionName, category=discord.utils.get(guild.categories, name='Auctions'))

            try:

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

                e = discord.Embed(
                    title="Auction - " + name,
                    description="A new auction has been created for " + name,
                    color=0xfdbf2f
                )
                if url != 'none':
                    e.set_thumbnail(url=url)

                e.add_field(name="Starting Price:", value=str(price)+"ADA", inline=True)
                e.add_field(name="Increment:", value=str(increment)+"ADA", inline=True)
                e.add_field(name = chr(173), value = chr(173), inline=False)
                e.add_field(name="Start time (UTC)", value=datetime.strptime(start, "%Y-%m-%dT%H:%M:%S"), inline=True)
                e.add_field(name="End Time (UTC)", value=datetime.strptime(end, "%Y-%m-%dT%H:%M:%S"), inline=True)
                e.add_field(name = chr(173), value = chr(173), inline=False)
                e.add_field(name="Highest Bidder:", value="---", inline=True)
                e.add_field(name="Price:", value="---", inline=True)
                e.add_field(name = chr(173), value = chr(173), inline=False)
                e.add_field(name="How to participate?", value="!bid " + str(price+auctions[str(c.id)]['increment']), inline=False)
                e.set_footer(text='Goodluck!')

                msg = await c.send(embed=e)

                auctions[str(c.id)]['embed'] = e.to_dict()
                auctions[str(c.id)]['msg_id'] = msg.id

                await ctx.send("Auction Created!")
            except: 
                if c:
                    await c.delete()
                raise

            save_auc_history()

            if looping == False:
                looping = True
                bot.loop.create_task(run_checks())

        else:
            await reply_error(ctx, "Auction channel already exists")
            
    else: 
        pass

#@create.error
#async def create_error(ctx, error):
#
#    if str(ctx.channel.id) != COMMAND_CHANNEL:
#        pass
#    else:
#        if isinstance(error, commands.MissingRequiredArgument):
#            message = f"Missing a required argument. Use '!help create' to view arguments"
#        else: 
#            message = "Something went wrong while running the command. Please re-look at it and try again(use '!help create' to get info)"
#
#        await ctx.message.reply(message)

@bot.command(name='bid', help='Creates a bid', usage='<price>')
async def bid(ctx, price: int):

    now = datetime.now()
    a_id = ctx.channel.id
    extended = False

    if str(a_id) in auctions_list:

        a = auctions[str(a_id)]

        if a['start'] < now and a['end'] > now:
            if (price >= (a['highBid'] + a['increment'])) or (a['bids'] == 0 and price >= a['price']):

                outBidId = a['highBidId']

                a['highBid'] = price
                a['highBidId'] = ctx.message.author.id
                a['highBidName'] = ctx.message.author.name
                a['bids'] = a['bids'] + 1

                if now > a['end'] - timedelta(minutes=1):
                    a['end'] = a['end'] + timedelta(minutes=1)
                    extended = True

                for field in a['embed']['fields']:
                    if field['name'] == 'Price:':
                        field['value'] = price
                    if field['name'] == 'Highest Bidder:':
                         field['value'] = ctx.message.author.name
                
                save_auc_history()

                bid_embed=discord.Embed(title=str(ctx.message.author.name) + " placed a new bid!", description="Price: "+str(price)+"ADA", color=0x00a113)
                bid_embed.add_field(name=chr(173), value="How to participate: !bid " + str(price+a['increment']), inline=False)
                bid_embed.set_footer(text=str(now))

                await ctx.send(embed=bid_embed)

                try:
                    if outBidId is not None:
                        user = await bot.fetch_user(int(outBidId))
                        await ctx.send(user.mention + ' You have been outbid')
                except:
                    print("Failed mention")

                if extended:
                    await ctx.send("Auction extended by 1 min! New end time: " + str(a['end']))

                org_embed_msg = await ctx.fetch_message(a['msg_id'])

                await org_embed_msg.edit(embed=discord.Embed.from_dict(a['embed']))
                
            else:
                if a['bids'] == 0:
                    await reply_error_delete(ctx, "Min bid is: " + str(a['price']) + "ADA")
                else:
                    await reply_error_delete(ctx, "Min bid is: " + str(a['highBid'] + a['increment']) + "ADA")


        elif a['start'] > now:
           await reply_error_delete(ctx, "This auction has not started yet")

        elif a['end'] < now:
            await reply_error_delete(ctx, "This auction has ended")
        
    else:
        pass

@bid.error
async def bid_error(ctx, error):
    if str(ctx.channel.id) not in auctions_list:
        pass
    else:
        if isinstance(error, commands.MissingRequiredArgument):
            message = f"Missing a required argument"
        else: 
            message = "Please re-look at your command(use '!help bid')"
    
        await ctx.message.reply(message, delete_after=5)
        await ctx.message.delete(delay=5)

if __name__ == "__main__":
    get_auc_history()
    bot.loop.create_task(run_checks())
    bot.run(TOKEN)

