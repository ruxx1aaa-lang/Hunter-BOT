import discord
from discord.ext import commands
from datetime import datetime, timezone
import config

def get_log_channel(guild):
    return guild.get_channel(config.LOG_CHANNEL_ID)

def base_embed(title, color, user=None):
    embed = discord.Embed(title=title, color=color, timestamp=datetime.now(timezone.utc))
    if user:
        embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text="Hunter Security Bot")
    return embed

class LoggingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Member Events ---
    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            embed = discord.Embed(
                description=(
                    "```\n"
                    "  ██╗  ██╗██╗   ██╗███╗   ██╗████████╗███████╗██████╗ \n"
                    "  ██║  ██║██║   ██║████╗  ██║╚══██╔══╝██╔════╝██╔══██╗\n"
                    "  ███████║██║   ██║██╔██╗ ██║   ██║   █████╗  ██████╔╝\n"
                    "  ██╔══██║██║   ██║██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗\n"
                    "  ██║  ██║╚██████╔╝██║ ╚████║   ██║   ███████╗██║  ██║\n"
                    "  ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝\n"
                    "```"
                ),
                color=0x2b2d31
            )
            embed.add_field(
                name="👋  Welcome to Hunters Server  <3",
                value=(
                    f"Hey **{member.display_name}**, glad you made it!\n\n"
                    f"🏹  You've just joined **Hunters Server** — a place built for real ones.\n"
                    f"💜  **Werjo** is always here for you, don't hesitate to reach out.\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━"
                ),
                inline=False
            )
            embed.add_field(name="🔐  Security", value="This server is protected by **Hunter Bot**\nStay safe, stay clean.", inline=True)
            embed.add_field(name="📅  Joined", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_image(url="https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExbHJyMHQwc2U5Y205dmIzOHlwbGo3azJ6anU3bHl3NTRpNmVyamdhcSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/13bNOV0vthoFsgIt2F/giphy.gif")
            embed.set_footer(text="Hunters Server  •  We're happy to have you  :)", icon_url=member.guild.icon.url if member.guild.icon else None)
            embed.timestamp = datetime.now(timezone.utc)
            await member.send(embed=embed)
        except discord.Forbidden:
            pass

        ch = get_log_channel(member.guild)
        if not ch:
            return
        age = (datetime.now(timezone.utc) - member.created_at).days
        embed = base_embed("📥 عضو جديد انضم", discord.Color.green(), member)
        embed.add_field(name="الاسم", value=str(member), inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="عمر الأكونت", value=f"{age} يوم", inline=True)
        embed.add_field(name="تاريخ الإنشاء", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
        if age < config.NEW_ACCOUNT_DAYS:
            embed.add_field(name="⚠️ تحذير", value="أكونت جديد جداً!", inline=False)
            embed.color = discord.Color.orange()
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        ch = get_log_channel(member.guild)
        if not ch:
            return
        embed = base_embed("� عضو غادر السيرفر", discord.Color.red(), member)
        embed.add_field(name="الاسم", value=str(member), inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        ch = get_log_channel(after.guild)
        if not ch:
            return
        if before.nick != after.nick:
            embed = base_embed("✏️ تغيير النيك نيم", discord.Color.blue(), after)
            embed.add_field(name="قبل", value=before.nick or before.name, inline=True)
            embed.add_field(name="بعد", value=after.nick or after.name, inline=True)
            embed.add_field(name="ID", value=after.id, inline=False)
            await ch.send(embed=embed)
        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            if added or removed:
                embed = base_embed("🎭 تغيير الرول", discord.Color.purple(), after)
                embed.add_field(name="العضو", value=str(after), inline=True)
                if added:
                    embed.add_field(name="رول أضيف", value=", ".join(r.mention for r in added), inline=False)
                if removed:
                    embed.add_field(name="رول اتشال", value=", ".join(r.mention for r in removed), inline=False)
                await ch.send(embed=embed)

    # --- Message Events ---
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.guild:
            return
        ch = get_log_channel(message.guild)
        if not ch:
            return
        embed = base_embed("🗑️ رسالة اتحذفت", discord.Color.red(), message.author)
        embed.add_field(name="المرسل", value=str(message.author), inline=True)
        embed.add_field(name="القناة", value=message.channel.mention, inline=True)
        embed.add_field(name="المحتوى", value=message.content[:1024] or "*(لا يوجد نص)*", inline=False)
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content:
            return
        ch = get_log_channel(before.guild)
        if not ch:
            return
        embed = base_embed("� رسالة اتعدلت", discord.Color.yellow(), before.author)
        embed.add_field(name="المرسل", value=str(before.author), inline=True)
        embed.add_field(name="القناة", value=before.channel.mention, inline=True)
        embed.add_field(name="قبل", value=before.content[:512] or "*(فاضي)*", inline=False)
        embed.add_field(name="بعد", value=after.content[:512] or "*(فاضي)*", inline=False)
        embed.add_field(name="🔗 الرسالة", value=f"[اضغط هنا]({after.jump_url})", inline=False)
        await ch.send(embed=embed)

    # --- Moderation Events ---
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        ch = get_log_channel(guild)
        if not ch:
            return
        embed = base_embed("� عضو اتبان", discord.Color.dark_red(), user)
        embed.add_field(name="الاسم", value=str(user), inline=True)
        embed.add_field(name="ID", value=user.id, inline=True)
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        ch = get_log_channel(guild)
        if not ch:
            return
        embed = base_embed("✅ عضو اتفك بانه", discord.Color.green(), user)
        embed.add_field(name="الاسم", value=str(user), inline=True)
        embed.add_field(name="ID", value=user.id, inline=True)
        await ch.send(embed=embed)

    # --- Channel Events ---
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        ch = get_log_channel(channel.guild)
        if not ch:
            return
        embed = base_embed("📢 قناة جديدة اتعملت", discord.Color.green())
        embed.add_field(name="الاسم", value=channel.name, inline=True)
        embed.add_field(name="النوع", value=str(channel.type), inline=True)
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        ch = get_log_channel(channel.guild)
        if not ch:
            return
        embed = base_embed("🗑️ قناة اتحذفت", discord.Color.red())
        embed.add_field(name="الاسم", value=channel.name, inline=True)
        embed.add_field(name="النوع", value=str(channel.type), inline=True)
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        ch = get_log_channel(after.guild)
        if not ch:
            return
        if before.name != after.name:
            embed = base_embed("✏️ قناة اتعدل اسمها", discord.Color.blue())
            embed.add_field(name="قبل", value=before.name, inline=True)
            embed.add_field(name="بعد", value=after.name, inline=True)
            await ch.send(embed=embed)

    # --- Role Events ---
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        ch = get_log_channel(role.guild)
        if not ch:
            return
        embed = base_embed("🎭 رول جديد اتعمل", discord.Color.green())
        embed.add_field(name="الاسم", value=role.name, inline=True)
        embed.add_field(name="ID", value=role.id, inline=True)
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        ch = get_log_channel(role.guild)
        if not ch:
            return
        embed = base_embed("🗑️ رول اتحذف", discord.Color.red())
        embed.add_field(name="الاسم", value=role.name, inline=True)
        embed.add_field(name="ID", value=role.id, inline=True)
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        ch = get_log_channel(after.guild)
        if not ch:
            return
        if before.name != after.name:
            embed = base_embed("✏️ رول اتعدل", discord.Color.blue())
            embed.add_field(name="قبل", value=before.name, inline=True)
            embed.add_field(name="بعد", value=after.name, inline=True)
            await ch.send(embed=embed)

    # --- Invite Events ---
    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        ch = get_log_channel(invite.guild)
        if not ch:
            return
        embed = base_embed("🔗 Invite جديد اتعمل", discord.Color.blue(), invite.inviter)
        embed.add_field(name="المنشئ", value=str(invite.inviter), inline=True)
        embed.add_field(name="الكود", value=invite.code, inline=True)
        embed.add_field(name="القناة", value=invite.channel.mention if invite.channel else "N/A", inline=True)
        embed.add_field(name="الاستخدامات", value=f"{invite.max_uses or '∞'}", inline=True)
        embed.add_field(name="ينتهي", value=f"<t:{int(invite.expires_at.timestamp())}:R>" if invite.expires_at else "أبداً", inline=True)
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        ch = get_log_channel(invite.guild)
        if not ch:
            return
        embed = base_embed("❌ Invite اتحذف", discord.Color.red())
        embed.add_field(name="الكود", value=invite.code, inline=True)
        embed.add_field(name="القناة", value=invite.channel.mention if invite.channel else "N/A", inline=True)
        await ch.send(embed=embed)

    # --- Emoji & Sticker Events ---
    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        ch = get_log_channel(guild)
        if not ch:
            return
        added = [e for e in after if e not in before]
        removed = [e for e in before if e not in after]
        if added:
            embed = base_embed("😀 إيموجي جديد أضيف", discord.Color.green())
            embed.add_field(name="الإيموجي", value=" ".join(str(e) for e in added), inline=False)
            await ch.send(embed=embed)
        if removed:
            embed = base_embed("🗑️ إيموجي اتحذف", discord.Color.red())
            embed.add_field(name="الاسم", value=", ".join(e.name for e in removed), inline=False)
            await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild, before, after):
        ch = get_log_channel(guild)
        if not ch:
            return
        added = [s for s in after if s not in before]
        removed = [s for s in before if s not in after]
        if added:
            embed = base_embed("🎨 ستيكر جديد أضيف", discord.Color.green())
            embed.add_field(name="الاسم", value=", ".join(s.name for s in added), inline=False)
            await ch.send(embed=embed)
        if removed:
            embed = base_embed("🗑️ ستيكر اتحذف", discord.Color.red())
            embed.add_field(name="الاسم", value=", ".join(s.name for s in removed), inline=False)
            await ch.send(embed=embed)

    # --- Voice Events ---
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        ch = get_log_channel(member.guild)
        if not ch:
            return
        if before.channel is None and after.channel is not None:
            embed = base_embed("🔊 دخل Voice Channel", discord.Color.green(), member)
            embed.add_field(name="العضو", value=str(member), inline=True)
            embed.add_field(name="القناة", value=after.channel.name, inline=True)
            await ch.send(embed=embed)
        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            embed = base_embed("� غير Voice Channel", discord.Color.blue(), member)
            embed.add_field(name="العضو", value=str(member), inline=True)
            embed.add_field(name="من", value=before.channel.name, inline=True)
            embed.add_field(name="إلى", value=after.channel.name, inline=True)
            await ch.send(embed=embed)

    # --- Server Events ---
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        ch = get_log_channel(after)
        if not ch:
            return
        if before.name != after.name:
            embed = base_embed("🏠 اسم السيرفر اتغير", discord.Color.blue())
            embed.add_field(name="قبل", value=before.name, inline=True)
            embed.add_field(name="بعد", value=after.name, inline=True)
            await ch.send(embed=embed)

    # --- Thread Events ---
    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        ch = get_log_channel(thread.guild)
        if not ch:
            return
        embed = base_embed("🧵 Thread جديد اتعمل", discord.Color.green())
        embed.add_field(name="الاسم", value=thread.name, inline=True)
        embed.add_field(name="القناة", value=thread.parent.mention if thread.parent else "N/A", inline=True)
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread):
        ch = get_log_channel(thread.guild)
        if not ch:
            return
        embed = base_embed("🗑️ Thread اتحذف", discord.Color.red())
        embed.add_field(name="الاسم", value=thread.name, inline=True)
        await ch.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LoggingCog(bot))
