import discord
from discord.ext import commands
from datetime import datetime, timezone
from collections import defaultdict

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # {guild_id: {user_id: count}}
        self.message_counts = defaultdict(lambda: defaultdict(int))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        self.message_counts[message.guild.id][message.author.id] += 1


    @commands.command(name="serverstats")
    @commands.has_permissions(manage_guild=True)
    async def server_stats(self, ctx):
        """إحصائيات السيرفر"""
        guild = ctx.guild
        total = guild.member_count
        bots = sum(1 for m in guild.members if m.bot)
        humans = total - bots
        online = sum(1 for m in guild.members if m.status != discord.Status.offline and not m.bot)

        embed = discord.Embed(
            title=f"📊 إحصائيات {guild.name}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="👥 إجمالي الأعضاء", value=total, inline=True)
        embed.add_field(name="🧑 بشر", value=humans, inline=True)
        embed.add_field(name="🤖 بوتات", value=bots, inline=True)
        embed.add_field(name="🟢 أونلاين", value=online, inline=True)
        embed.add_field(name="📢 القنوات", value=len(guild.channels), inline=True)
        embed.add_field(name="🎭 الرولات", value=len(guild.roles), inline=True)
        embed.add_field(name="😀 الإيموجيات", value=len(guild.emojis), inline=True)
        embed.add_field(name="📅 تاريخ الإنشاء", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.set_footer(text="Hunter Security Bot")
        await ctx.send(embed=embed)

    @commands.command(name="topusers")
    @commands.has_permissions(manage_guild=True)
    async def top_users(self, ctx):
        """أكتر الأعضاء كلاماً (منذ تشغيل البوت)"""
        guild_counts = self.message_counts.get(ctx.guild.id, {})
        if not guild_counts:
            return await ctx.send("📭 مفيش إحصائيات لسه.")

        sorted_users = sorted(guild_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        embed = discord.Embed(
            title="🏆 أكتر الأعضاء كلاماً",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        medals = ["🥇", "🥈", "🥉"] + ["🔹"] * 7
        for i, (user_id, count) in enumerate(sorted_users):
            member = ctx.guild.get_member(user_id)
            name = str(member) if member else f"ID: {user_id}"
            embed.add_field(name=f"{medals[i]} {name}", value=f"{count} رسالة", inline=False)

        embed.set_footer(text="Hunter Security Bot | منذ آخر تشغيل")
        await ctx.send(embed=embed)

    @commands.command(name="userinfo")
    async def user_info(self, ctx, member: discord.Member = None):
        """معلومات عضو"""
        member = member or ctx.author
        age = (datetime.now(timezone.utc) - member.created_at).days
        joined_age = (datetime.now(timezone.utc) - member.joined_at).days if member.joined_at else "?"

        embed = discord.Embed(
            title=f"👤 معلومات {member.display_name}",
            color=member.color,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="الاسم الكامل", value=str(member), inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="بوت؟", value="✅" if member.bot else "❌", inline=True)
        embed.add_field(name="تاريخ إنشاء الأكونت", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="عمر الأكونت", value=f"{age} يوم", inline=True)
        embed.add_field(name="انضم للسيرفر", value=f"منذ {joined_age} يوم", inline=True)
        roles = [r.mention for r in member.roles if r.name != "@everyone"]
        embed.add_field(name=f"الرولات ({len(roles)})", value=" ".join(roles) or "لا يوجد", inline=False)
        embed.set_footer(text="Hunter Security Bot")
        await ctx.send(embed=embed)

    @commands.command(name="help")
    async def help_command(self, ctx):
        """قائمة الأوامر"""
        embed = discord.Embed(
            title="🔍 Hunter Bot - قائمة الأوامر",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="🛡️ المراقبة", value="`!raidstatus` `!raidoff`", inline=False)
        embed.add_field(name="⚠️ التحذيرات", value="`!warn @عضو [سبب]`\n`!warnings @عضو`\n`!clearwarns @عضو`", inline=False)
        embed.add_field(name="🔨 الإدارة", value="`!mute @عضو [دقايق] [سبب]`\n`!unmute @عضو`\n`!kick @عضو [سبب]`\n`!ban @عضو [سبب]`\n`!unban [ID]`\n`!purge [عدد]`", inline=False)
        embed.add_field(name="📊 الإحصائيات", value="`!serverstats`\n`!topusers`\n`!userinfo [@عضو]`", inline=False)
        embed.set_footer(text="Hunter Security Bot")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(StatsCog(bot))
