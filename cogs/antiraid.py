import discord
from discord.ext import commands
from collections import deque
from datetime import datetime, timezone
import aiosqlite
import config

class AntiRaidCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # {guild_id: deque of join timestamps}
        self.join_tracker = {}
        self.raid_mode = {}  # {guild_id: bool}

    def get_log_channel(self, guild):
        return guild.get_channel(config.LOG_CHANNEL_ID)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        now = datetime.now(timezone.utc).timestamp()

        # نسجل في قاعدة البيانات
        age = (datetime.now(timezone.utc) - member.created_at).days
        async with aiosqlite.connect("hunter.db") as db:
            await db.execute(
                "INSERT INTO join_log (guild_id, user_id, username, account_age_days) VALUES (?, ?, ?, ?)",
                (guild.id, member.id, str(member), age)
            )
            await db.commit()

        # نتابع الانضمامات
        if guild.id not in self.join_tracker:
            self.join_tracker[guild.id] = deque()

        self.join_tracker[guild.id].append(now)

        # نشيل القديم
        while self.join_tracker[guild.id] and now - self.join_tracker[guild.id][0] > config.RAID_TIME_WINDOW:
            self.join_tracker[guild.id].popleft()

        # فحص الريد
        if len(self.join_tracker[guild.id]) >= config.RAID_JOIN_LIMIT:
            await self.activate_raid_mode(guild)

        # فحص الأكونت الجديد جداً
        if age < config.NEW_ACCOUNT_DAYS and not self.raid_mode.get(guild.id):
            await self.handle_new_account(member, age)

    async def activate_raid_mode(self, guild):
        if self.raid_mode.get(guild.id):
            return  # ريد مود شغال أصلاً

        self.raid_mode[guild.id] = True
        ch = self.get_log_channel(guild)

        # نعمل lockdown - نمنع الأعضاء الجدد من الكلام
        try:
            for channel in guild.text_channels:
                overwrite = channel.overwrites_for(guild.default_role)
                overwrite.send_messages = False
                await channel.set_permissions(guild.default_role, overwrite=overwrite, reason="Hunter: Raid Mode Activated")
        except discord.Forbidden:
            pass

        if ch:
            embed = discord.Embed(
                title="🚨 RAID MODE ACTIVATED",
                description="تم اكتشاف هجوم على السيرفر!\nتم تفعيل وضع الطوارئ وإيقاف الكلام مؤقتاً.",
                color=discord.Color.dark_red(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="السبب", value=f"انضم {config.RAID_JOIN_LIMIT}+ أعضاء في {config.RAID_TIME_WINDOW} ثانية", inline=False)
            embed.add_field(name="الإجراء", value="استخدم `!raidoff` لإيقاف وضع الطوارئ", inline=False)
            embed.set_footer(text="Hunter Security Bot")
            await ch.send(embed=embed)

    async def handle_new_account(self, member, age):
        ch = self.get_log_channel(member.guild)
        if not ch:
            return
        embed = discord.Embed(
            title="⚠️ أكونت جديد جداً",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="العضو", value=str(member), inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="عمر الأكونت", value=f"{age} يوم فقط", inline=True)
        embed.set_footer(text="Hunter Security Bot")
        await ch.send(embed=embed)

    @commands.command(name="raidoff")
    @commands.has_permissions(administrator=True)
    async def raid_off(self, ctx):
        """إيقاف وضع الطوارئ"""
        guild = ctx.guild
        self.raid_mode[guild.id] = False

        try:
            for channel in guild.text_channels:
                overwrite = channel.overwrites_for(guild.default_role)
                overwrite.send_messages = None
                await channel.set_permissions(guild.default_role, overwrite=overwrite, reason="Hunter: Raid Mode Deactivated")
        except discord.Forbidden:
            pass

        embed = discord.Embed(
            title="✅ تم إيقاف وضع الطوارئ",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="Hunter Security Bot")
        await ctx.send(embed=embed)

    @commands.command(name="raidstatus")
    @commands.has_permissions(manage_guild=True)
    async def raid_status(self, ctx):
        """عرض حالة وضع الطوارئ"""
        status = self.raid_mode.get(ctx.guild.id, False)
        color = discord.Color.red() if status else discord.Color.green()
        embed = discord.Embed(
            title="🛡️ حالة Raid Mode",
            description=f"الحالة: {'🔴 مفعّل' if status else '🟢 موقف'}",
            color=color
        )
        embed.set_footer(text="Hunter Security Bot")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AntiRaidCog(bot))
