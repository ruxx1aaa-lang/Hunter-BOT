import discord
from discord.ext import commands
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import asyncio
import config

class AntiSpamCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # {user_id: [timestamps]}
        self.message_tracker = defaultdict(list)

    def get_log_channel(self, guild):
        return guild.get_channel(config.LOG_CHANNEL_ID)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        await self.check_spam(message)
        await self.check_forbidden_content(message)

    async def check_spam(self, message):
        user_id = message.author.id
        now = datetime.now(timezone.utc).timestamp()

        # نضيف الوقت الحالي ونشيل القديم
        self.message_tracker[user_id].append(now)
        self.message_tracker[user_id] = [
            t for t in self.message_tracker[user_id]
            if now - t < config.SPAM_TIME_WINDOW
        ]

        if len(self.message_tracker[user_id]) >= config.SPAM_MESSAGE_LIMIT:
            self.message_tracker[user_id] = []
            await self.handle_spam(message)

    async def handle_spam(self, message):
        member = message.author
        guild = message.guild
        ch = self.get_log_channel(guild)

        # نميوت العضو
        try:
            duration = discord.utils.utcnow() + timedelta(seconds=config.SPAM_MUTE_DURATION)
            await member.timeout(duration, reason="سبام تلقائي - Hunter Bot")
        except discord.Forbidden:
            pass

        # نحذف رسائله الأخيرة
        try:
            await message.channel.purge(limit=10, check=lambda m: m.author == member)
        except discord.Forbidden:
            pass

        # نبعت تحذير في القناة
        try:
            warn_msg = await message.channel.send(
                f"⚠️ {member.mention} اتعمله ميوت بسبب السبام لمدة {config.SPAM_MUTE_DURATION // 60} دقيقة."
            )
            await asyncio.sleep(5)
            await warn_msg.delete()
        except discord.Forbidden:
            pass

        # نسجل في اللوج
        if ch:
            embed = discord.Embed(
                title="🚫 سبام اكتُشف",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="العضو", value=str(member), inline=True)
            embed.add_field(name="ID", value=member.id, inline=True)
            embed.add_field(name="القناة", value=message.channel.mention, inline=True)
            embed.add_field(name="الإجراء", value=f"ميوت لمدة {config.SPAM_MUTE_DURATION // 60} دقيقة", inline=False)
            embed.set_footer(text="Hunter Security Bot")
            await ch.send(embed=embed)

    async def check_forbidden_content(self, message):
        content_lower = message.content.lower()
        ch = self.get_log_channel(message.guild)

        # فحص الكلمات الممنوعة
        for word in config.FORBIDDEN_WORDS:
            if word.lower() in content_lower:
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass
                if ch:
                    embed = discord.Embed(title="🤬 كلمة ممنوعة", color=discord.Color.red(), timestamp=discord.utils.utcnow())
                    embed.add_field(name="العضو", value=str(message.author), inline=True)
                    embed.add_field(name="القناة", value=message.channel.mention, inline=True)
                    embed.set_footer(text="Hunter Security Bot")
                    await ch.send(embed=embed)
                return

        # فحص اللينكات المشبوهة
        for link in config.SUSPICIOUS_LINKS:
            if link in content_lower:
                # نتجاهل لو الشخص عنده رول معين (زي الأدمن)
                if message.author.guild_permissions.manage_messages:
                    return
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass
                try:
                    await message.channel.send(
                        f"⚠️ {message.author.mention} مش مسموح بنشر اللينكات دي هنا.",
                        delete_after=5
                    )
                except discord.Forbidden:
                    pass
                if ch:
                    embed = discord.Embed(title="🔗 لينك مشبوه", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
                    embed.add_field(name="العضو", value=str(message.author), inline=True)
                    embed.add_field(name="القناة", value=message.channel.mention, inline=True)
                    embed.add_field(name="المحتوى", value=message.content[:200], inline=False)
                    embed.set_footer(text="Hunter Security Bot")
                    await ch.send(embed=embed)
                return

async def setup(bot):
    await bot.add_cog(AntiSpamCog(bot))
