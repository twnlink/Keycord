import discord
from discord.ext import commands
from quart import Quart, render_template, request, abort, jsonify
import asyncio
import asyncpg
import aiohttp
import json

async def run():
    global db
    db = await asyncpg.create_pool(user='creatable', database='keycord', host='127.0.0.1')

bot = commands.Bot(command_prefix =".")
app = Quart(__name__, static_url_path='')

@app.errorhandler(404)
async def page_not_found(e):
    return await render_template('404.html'), 404

@app.route('/')
async def root():
    return await render_template('index.html')

@app.route('/about')
async def about():
    return await render_template('about.html')

@app.route('/user')
async def user():
    if 'id' in request.args:
        try:
            id = int(request.args['id'])
        except:
            abort(404)
        user = await db.fetchrow("SELECT * FROM users WHERE id = $1", id)
        if not user:
            abort(404)
        else:
            member = bot.get_user(user["id"])
            message = (await bot.get_channel(658331377602920471).fetch_message(user["proofs"])).content
            return await render_template('user.html', user = member.name + f"#{member.discriminator}", proof = message, messageid = user["proofs"])
    else:
        abort(404)

@app.route('/new-proof')
async def new_proof():
    if ('kb' in request.args) and ('id' in request.args) and ('token' in request.args) and ('kb_ua' in request.args):
        if len(request.args['kb']) < 17 and len(request.args['id']) == 18:
            return await render_template('newproof.html', proof = json.dumps({'keybase_username': request.args['kb'], 'discord_id': request.args['id'], 'sig_hash': request.args['token']}))
    else:
        abort(404)

@app.route('/keybase-proofs.json')
async def proof_url():
    if 'id' in request.args:
        try:
            id = int(request.args['id'])
        except:
            abort(404)
        user = await db.fetchrow("SELECT * FROM users WHERE id = $1", id)
        if not user:
            abort(404)
        else:
            proof = (await bot.get_channel(658331377602920471).fetch_message(user["proofs"])).content
            try: 
                proof = json.loads(proof)
            except:
                abort(404)
            return jsonify({"signatures": [{"kb_username": proof["keybase_username"], "sig_hash": proof["sig_hash"]}]})
    else:
        abort(404)
@bot.event
async def on_ready():
    print('------\nLogged in as:')
    print(bot.user.name)
    print("With the ID: %s\n------" % bot.user.id)

@bot.event
async def on_message(ctx):
    if ctx.author.bot:
        return
    if ctx.channel.id == 658331377602920471:
        proofs = await db.fetchrow("SELECT * FROM users WHERE id = $1", ctx.author.id)
        if not proofs:
            try:
                kbinfo = json.loads(ctx.content)
                if ("keybase_username" in kbinfo) and ("discord_id" in kbinfo) and ("sig_hash" in kbinfo):
                    # This may not *actually* work if Keybase ever adds your instance. I couldn't get it to function myself without it being added so usually I would just comment it out.
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f'https://keybase.io/_/api/1.0/sig/proof_valid.json?domain=localhost&kb_username={kbinfo["keybase_username"]}&username={kbinfo["discord_id"]}&sig_hash={kbinfo["sig_hash"]}') as response:
                            valid = json.loads(await response.text())
                            if valid["proof_valid"] == True:
                                await ctx.add_reaction('✅')
                                try:
                                    await ctx.author.send(""">>> Here's a link to your Keycord profile:
http://localhost/user?id=""" + str(ctx.author.id))
                                except:
                                    pass
                                await db.execute("INSERT INTO users (id, proofs) VALUES ($1, $2)", ctx.author.id, ctx.id)
                            else:
                                await ctx.delete()
                else:
                    await ctx.delete()
            except:
                await ctx.delete()
        else:
            await ctx.delete()
    else:
        await bot.process_commands(ctx)

@bot.event
async def on_raw_message_delete(ctx):
    if ctx.channel_id == 658331377602920471:
        proofs = await db.fetchrow("SELECT * FROM users WHERE proofs = $1", ctx.message_id)
        if proofs:
            await db.execute("DELETE FROM users WHERE proofs = $1", ctx.message_id)

@bot.event
async def on_raw_message_edit(ctx):
    if ctx.channel_id == 658331377602920471:
        proofs = await db.fetchrow("SELECT * FROM users WHERE proofs = $1", ctx.message_id)
        if proofs:
            await db.execute("DELETE FROM users WHERE proofs = $1", ctx.message_id)
            message = (await bot.get_channel(ctx.channel_id).fetch_message(ctx.message_id))
            await message.delete()
            

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    botprocess = loop.create_task(bot.start("NO BOT TOKEN PUBLISHING FOR ME"))
    postgres = loop.create_task(run())
    web = loop.create_task(app.run(port=3000, loop=loop))
    gathered = asyncio.gather(botprocess, web)
    try:
        loop.run_until_complete(gathered)
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(bot.logout())
        loop.close()
