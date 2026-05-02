import discord
from discord.ext import commands
import aiosqlite
import asyncio
import config
import os
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

def get_prefix(bot, message):
    # يقبل الـ prefix الأصلي (مثلاً "!hunt ") و "!" كمان
    prefixes = [config.PREFIX, "!"]
    return commands.when_mentioned_or(*prefixes)(bot, message)

bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)

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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                log_channel_id INTEGER
            )
        """)
        await db.commit()

@bot.event
async def on_ready():
    await init_db()
    # حساب عدد السيرفرات بداية من 824
    server_count = len(bot.guilds) + 823  # لو البوت في سيرفر واحد يطلع 824
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=f"{server_count} Servers online | By werjo")
    )
    print(f"✅ Hunter is online as {bot.user}")
    print(f"📡 Monitoring {len(bot.guilds)} server(s)")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    print(f"[MSG] {message.author}: {message.content[:50]}")
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    print(f"[CMD ERROR] {ctx.command} | {error}")

# ─── Help Command GUI ──────────────────────────────────────────────────────
class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.current_page = "main"

    def get_main_embed(self):
        embed = discord.Embed(
            title="🏹 Hunter Bot - Command Center",
            description="**مرحباً بك في Hunter Bot!**\nاختر الفئة الي عايز تشوف أوامرها من الأزرار تحت ⬇️",
            color=0x2B2D31
        )
        embed.add_field(
            name="📊 إحصائيات البوت",
            value=f"🌐 **السيرفرات:** {len(bot.guilds)}\n👥 **المستخدمين:** {len(bot.users)}\n⚡ **الأوامر:** 25+",
            inline=True
        )
        embed.add_field(
            name="🔗 روابط مهمة",
            value="[دعوة البوت](https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=8&scope=bot)\n[سيرفر الدعم](https://discord.gg/support)",
            inline=True
        )
        embed.add_field(
            name="👨‍💻 المطور",
            value="**werjo**\nDeveloper & Owner",
            inline=True
        )
        embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
        embed.set_footer(text="Hunter Bot • Developed by werjo", icon_url=bot.user.avatar.url if bot.user.avatar else None)
        return embed

    def get_music_embed(self):
        embed = discord.Embed(
            title="🎵 أوامر الموسيقى",
            description="**نظام موسيقى متطور مع دعم SoundCloud و YouTube**",
            color=0x5865F2
        )
        embed.add_field(
            name="🎶 التشغيل الأساسي",
            value="`!p <اسم/رابط>` - تشغيل أغنية\n`!skip` - تخطي الأغنية\n`!stop` - إيقاف الموسيقى\n`!pause` - إيقاف مؤقت\n`!resume` - استكمال",
            inline=False
        )
        embed.add_field(
            name="📋 إدارة القائمة",
            value="`!queue` - عرض قائمة الأغاني\n`!np` - الأغنية الحالية\n`!loop` - تكرار الأغنية\n`!volume <1-100>` - تغيير الصوت",
            inline=False
        )
        embed.add_field(
            name="🎵 Playlists",
            value="`!pl create <اسم>` - إنشاء playlist\n`!pl add <اسم> <أغنية>` - إضافة أغنية\n`!pl play <اسم>` - تشغيل playlist\n`!pl list` - عرض playlists",
            inline=False
        )
        embed.add_field(
            name="🔊 Voice",
            value="`!join` - دخول voice channel\n`!leave` - خروج من voice channel",
            inline=False
        )
        embed.set_footer(text="يدعم SoundCloud و YouTube • 24/7 Online")
        return embed

    def get_security_embed(self):
        embed = discord.Embed(
            title="🛡️ أوامر الحماية والأمان",
            description="**نظام حماية متطور لحماية سيرفرك**",
            color=0xED4245
        )
        embed.add_field(
            name="🔨 Auto-Ban System",
            value="`!hunt autoban on/off` - تشغيل/إيقاف البان التلقائي\nيبان أي عضو يغادر السيرفر تلقائياً",
            inline=False
        )
        embed.add_field(
            name="📝 نظام الـ Logs",
            value="`!hunt setlog #channel` - تحديد قناة الـ logs\n`!hunt loginfo` - معلومات قناة الـ logs",
            inline=False
        )
        embed.add_field(
            name="👮 أوامر الإدارة",
            value="`!ban <عضو> [سبب]` - بان عضو\n`!kick <عضو> [سبب]` - طرد عضو\n`!warn <عضو> <سبب>` - إنذار عضو\n`!mute <عضو>` - كتم عضو",
            inline=False
        )
        embed.add_field(
            name="🔍 المراقبة",
            value="• مراقبة دخول/خروج الأعضاء\n• تسجيل تعديل/حذف الرسائل\n• مراقبة تغييرات الأدوار والقنوات\n• تتبع الـ Voice Channels",
            inline=False
        )
        embed.set_footer(text="حماية 24/7 لسيرفرك")
        return embed

    def get_moderation_embed(self):
        embed = discord.Embed(
            title="👮 أوامر الإدارة",
            description="**أدوات إدارة قوية للمشرفين**",
            color=0xFEE75C
        )
        embed.add_field(
            name="🔨 العقوبات",
            value="`!ban <عضو> [سبب]` - بان دائم\n`!tempban <عضو> <وقت> [سبب]` - بان مؤقت\n`!unban <ID>` - إلغاء البان\n`!kick <عضو> [سبب]` - طرد من السيرفر",
            inline=False
        )
        embed.add_field(
            name="🔇 الكتم",
            value="`!mute <عضو> [وقت]` - كتم عضو\n`!unmute <عضو>` - إلغاء الكتم\n`!timeout <عضو> <وقت>` - timeout",
            inline=False
        )
        embed.add_field(
            name="⚠️ الإنذارات",
            value="`!warn <عضو> <سبب>` - إعطاء إنذار\n`!warnings <عضو>` - عرض إنذارات العضو\n`!clearwarns <عضو>` - مسح الإنذارات",
            inline=False
        )
        embed.add_field(
            name="🧹 تنظيف الرسائل",
            value="`!clear <عدد>` - حذف رسائل\n`!purge <عضو> <عدد>` - حذف رسائل عضو معين",
            inline=False
        )
        embed.set_footer(text="صلاحيات الإدارة مطلوبة")
        return embed

    def get_stats_embed(self):
        embed = discord.Embed(
            title="📊 أوامر الإحصائيات",
            description="**معلومات وإحصائيات مفصلة**",
            color=0x57F287
        )
        embed.add_field(
            name="📈 إحصائيات السيرفر",
            value="`!serverinfo` - معلومات السيرفر\n`!membercount` - عدد الأعضاء\n`!channelcount` - عدد القنوات\n`!rolecount` - عدد الأدوار",
            inline=False
        )
        embed.add_field(
            name="👤 إحصائيات الأعضاء",
            value="`!userinfo <عضو>` - معلومات العضو\n`!avatar <عضو>` - صورة العضو\n`!joindate <عضو>` - تاريخ الانضمام",
            inline=False
        )
        embed.add_field(
            name="🤖 إحصائيات البوت",
            value="`!botinfo` - معلومات البوت\n`!ping` - سرعة الاستجابة\n`!uptime` - مدة التشغيل",
            inline=False
        )
        embed.set_footer(text="إحصائيات محدثة لحظياً")
        return embed

    @discord.ui.button(label="🎵 موسيقى", style=discord.ButtonStyle.primary, row=0)
    async def music_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.get_music_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🛡️ حماية", style=discord.ButtonStyle.danger, row=0)
    async def security_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.get_security_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="👮 إدارة", style=discord.ButtonStyle.secondary, row=0)
    async def moderation_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.get_moderation_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="📊 إحصائيات", style=discord.ButtonStyle.success, row=0)
    async def stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.get_stats_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🏠 الرئيسية", style=discord.ButtonStyle.primary, row=1)
    async def home_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.get_main_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🔗 دعوة البوت", style=discord.ButtonStyle.secondary, row=1)
    async def invite_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔗 دعوة Hunter Bot",
            description="**اضيف البوت لسيرفرك دلوقتي!**",
            color=0x5865F2
        )
        embed.add_field(
            name="📋 رابط الدعوة",
            value="[اضغط هنا لدعوة البوت](https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=8&scope=bot)",
            inline=False
        )
        embed.add_field(
            name="✅ الصلاحيات المطلوبة",
            value="• إدارة السيرفر\n• إدارة الأعضاء\n• إدارة الرسائل\n• الاتصال بـ Voice Channels",
            inline=False
        )
        embed.set_footer(text="شكراً لاختيارك Hunter Bot!")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="❌ إغلاق", style=discord.ButtonStyle.danger, row=1)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="✅ تم إغلاق القائمة",
            description="شكراً لاستخدام Hunter Bot!",
            color=0x57F287
        )
        embed.set_footer(text="يمكنك استخدام !help مرة أخرى")
        await interaction.response.edit_message(embed=embed, view=None)

@bot.command(name="help", aliases=["مساعدة", "h"])
async def help_command(ctx):
    """عرض قائمة الأوامر التفاعلية"""
    view = HelpView()
    embed = view.get_main_embed()
    await ctx.send(embed=embed, view=view)

@bot.event
async def on_command(ctx):
    print(f"[CMD] {ctx.author} used: {ctx.message.content[:50]}")

async def load_cogs():
    cogs = ["cogs.logging", "cogs.antispam", "cogs.antiraid", "cogs.moderation", "cogs.stats", "cogs.music"]
    for cog in cogs:
        await bot.load_extension(cog)
        print(f"  ✔ Loaded {cog}")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(config.TOKEN)

asyncio.run(main())
