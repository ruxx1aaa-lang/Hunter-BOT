import discord
from discord.ext import commands
import aiosqlite
from datetime import timedelta
import config

class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_warnings(self, guild_id, user_id):
        async with aiosqlite.connect("hunter.db") as db:
            async with db.execute(
                "SELECT id, reason, moderator_id, timestamp FROM warnings WHERE guild_id=? AND user_id=? ORDER BY timestamp DESC",
                (guild_id, user_id)
            ) as cursor:
                return await cursor.fetchall()

    async def add_warning(self, guild_id, user_id, reason, moderator_id):
        async with aiosqlite.connect("hunter.db") as db:
            await db.execute(
                "INSERT INTO warnings (guild_id, user_id, reason, moderator_id) VALUES (?, ?, ?, ?)",
                (guild_id, user_id, reason, moderator_id)
            )
            await db.commit()

    @commands.command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason="لا يوجد سبب"):
        """تحذير عضو"""
        if member.bot:
            return await ctx.send("❌ مش هتقدر تحذر بوت.")

        await self.add_warning(ctx.guild.id, member.id, reason, ctx.author.id)
        warnings = await self.get_warnings(ctx.guild.id, member.id)
        count = len(warnings)

        embed = discord.Embed(title="⚠️ تحذير", color=discord.Color.yellow(), timestamp=discord.utils.utcnow())
        embed.add_field(name="العضو", value=str(member), inline=True)
        embed.add_field(name="المشرف", value=str(ctx.author), inline=True)
        embed.add_field(name="السبب", value=reason, inline=False)
        embed.add_field(name="عدد التحذيرات", value=f"{count}", inline=True)
        embed.set_footer(text="Hunter Security Bot")
        await ctx.send(embed=embed)

        # إجراء تلقائي بناءً على عدد التحذيرات
        if count >= config.WARN_BAN_THRESHOLD:
            await member.ban(reason=f"Hunter: وصل لـ {count} تحذيرات")
            await ctx.send(f"🔨 {member.mention} اتبان بسبب كثرة التحذيرات.")
        elif count >= config.WARN_KICK_THRESHOLD:
            await member.kick(reason=f"Hunter: وصل لـ {count} تحذيرات")
            await ctx.send(f"👢 {member.mention} اتكيك بسبب كثرة التحذيرات.")

    @commands.command(name="warnings")
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, ctx, member: discord.Member):
        """عرض تحذيرات عضو"""
        warns = await self.get_warnings(ctx.guild.id, member.id)
        if not warns:
            return await ctx.send(f"✅ {member.mention} مفيش عليه تحذيرات.")

        embed = discord.Embed(
            title=f"📋 تحذيرات {member.display_name}",
            color=discord.Color.orange()
        )
        for i, (wid, reason, mod_id, ts) in enumerate(warns[:10], 1):
            mod = ctx.guild.get_member(mod_id)
            embed.add_field(
                name=f"#{i} - {ts[:10]}",
                value=f"السبب: {reason}\nالمشرف: {mod or mod_id}",
                inline=False
            )
        embed.set_footer(text=f"إجمالي التحذيرات: {len(warns)} | Hunter Security Bot")
        await ctx.send(embed=embed)

    @commands.command(name="clearwarns")
    @commands.has_permissions(administrator=True)
    async def clear_warnings(self, ctx, member: discord.Member):
        """مسح تحذيرات عضو"""
        async with aiosqlite.connect("hunter.db") as db:
            await db.execute("DELETE FROM warnings WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
            await db.commit()
        await ctx.send(f"✅ تم مسح كل تحذيرات {member.mention}.")

    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, minutes: int = 10, *, reason="لا يوجد سبب"):
        """ميوت عضو"""
        duration = timedelta(minutes=minutes)
        await member.timeout(discord.utils.utcnow() + duration, reason=reason)
        embed = discord.Embed(title="🔇 ميوت", color=discord.Color.red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="العضو", value=str(member), inline=True)
        embed.add_field(name="المدة", value=f"{minutes} دقيقة", inline=True)
        embed.add_field(name="السبب", value=reason, inline=False)
        embed.set_footer(text="Hunter Security Bot")
        await ctx.send(embed=embed)

    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member):
        """رفع الميوت"""
        await member.timeout(None)
        await ctx.send(f"✅ تم رفع الميوت عن {member.mention}.")

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="لا يوجد سبب"):
        """كيك عضو"""
        await member.kick(reason=reason)
        await ctx.send(f"👢 تم كيك {member.mention}. السبب: {reason}")

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="لا يوجد سبب"):
        """باند عضو"""
        await member.ban(reason=reason)
        await ctx.send(f"🔨 تم باند {member.mention}. السبب: {reason}")

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int):
        """فك باند يوزر"""
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"✅ تم فك باند {user}.")

    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int = 10):
        """حذف رسائل"""
        await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"✅ تم حذف {amount} رسالة.", delete_after=3)

async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
