# bot.py
import os
import time
import random
import discord
from datetime import datetime
from discord.ext import commands

TOKEN = os.getenv('TOKEN')

auctions = {}

auctionsList = []

bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


@bot.command(name='create', help='Creates a new auction', usage='<name> <price> <start(yyyy-MM-ddTHH:mm:ss)> <end(yyyy-MM-ddTHH:mm:ss)> <image-url>')
async def create(ctx, name, price: int, start, end, url):

    print("checking")
    if (ctx.channel.name == "create-auction"): 
        print("executing")

        auctionName = "auction-" + name.lower()

        print("Creating auction: " + auctionName)

        guild = ctx.guild
        existing_channel = discord.utils.get(guild.channels, name=auctionName)
        
        if not existing_channel:
            print("Creating channel")

            await guild.create_text_channel(auctionName, category=discord.utils.get(guild.categories, name='Auctions'))

            newChannel = discord.utils.get(guild.channels, name=auctionName)
            
            auctions[newChannel.id] = {
                'id': newChannel.id,
                'price': price,
                'highBid': price,
                'highBidUser': None,
                'start': datetime.strptime(start, "%Y-%m-%dT%H:%M:%S"),
                'end': datetime.strptime(end, "%Y-%m-%dT%H:%M:%S")
            }

            auctionsList.append(newChannel.id)

            await ctx.send("Auction Created!")

            print('created new channel')

            embed=discord.Embed(title="Auction: " + name, description="A new auction for " + name, color=0xFF5733)

            embed.set_thumbnail(url=url)

            embed.add_field(name="Reserve Price:", value=str(price)+"ADA", inline=False)
            embed.add_field(name="Start time", value=datetime.strptime(start, "%Y-%m-%dT%H:%M:%S"), inline=True)
            embed.add_field(name="End Time", value=datetime.strptime(end, "%Y-%m-%dT%H:%M:%S"), inline=True)
            embed.add_field(name="How to participate?", value="!bid " + str(price+10), inline=False)

            embed.set_footer(text='Goodluck!')

            auctions[newChannel.id]['embed'] = embed
            await newChannel.send(embed=embed)

            print('sent embed')

        else:
            print("channel already exists")
            ctx.send("Auction channel already exists")
            
    else: 
        print("Use correct channel")


@bot.command(name='bid', help='Creates a bid', usage='!bid <price>')
async def bid(ctx, price: int):

    now = datetime.now()

    a_id = ctx.channel.id
    if a_id in auctionsList:

        a = auctions[a_id]

        if a['start'] < now and a['end'] > now:
            if price > a['highBid']:
                print('Accepted')

                a['highBid'] = price
                a['highBidUser'] = ctx.message.author.id

                embed=discord.Embed(title="Bid Accepted!", description=ctx.message.author.name + " placed a bid", color=0x00a113)
                embed.add_field(name="Price:", value=str(price)+"ADA")

                await ctx.send(embed=embed)
            else:
                await ctx.message.delete()
        elif a['start'] > now:
            msg = await ctx.send("Auction has not started yet")
            time.sleep(2)
            await ctx.message.delete()
            await msg.delete()

        elif a['end'] < now:
            msg = await ctx.send("Auction has already ended")
            time.sleep(2)
            await ctx.message.delete()
            await msg.delete()
        
    else:
        await ctx.send("This auction is no longer valid")

bot.run(TOKEN)





