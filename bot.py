import discord
from discord.ext import commands
import aiosqlite
import asyncio
import config

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix=config.PREFIX, intents=intents, help_command=None)

async def init_db():
    async with aiosqlite.connect("hunter.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                reason TEXT,
                moderator_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS join_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                username TEXT,
                account_age_days INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

@bot.event
async def on_ready():
    await init_db()
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="🔍 Server | Hunter")
    )
    print(f"✅ Hunter is online as {bot.user}")
    print(f"📡 Monitoring {len(bot.guilds)} server(s)")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)

async def load_cogs():
    cogs = ["cogs.logging", "cogs.antispam", "cogs.antiraid", "cogs.moderation", "cogs.stats"]
    for cog in cogs:
        await bot.load_extension(cog)
        print(f"  ✔ Loaded {cog}")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(config.TOKEN)

asyncio.run(main())
