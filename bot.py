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
    
    # فحص الـ cooldown العام للأوامر (منع spam)
    ctx = await bot.get_context(message)
    if ctx.valid and ctx.command:
        import time
        user_id = message.author.id
        now = time.time()
        
        # cooldown عام للأوامر (2 ثانية)
        if user_id in command_cooldown:
            if now - command_cooldown[user_id] < 2:  # 2 ثانية cooldown
                try:
                    await message.delete()
                except:
                    pass
                return
        
        command_cooldown[user_id] = now
    
    # معالجة الأوامر أولاً
    await bot.process_commands(message)
    
    # بعدين فحص إذا كانت الرسالة أمر للبوت للحذف
    if ctx.valid and ctx.command:
        guild_id = message.guild.id if message.guild else None
        
        # تحقق من تفعيل النظام للسيرفر
        if guild_id and autodelete_enabled.get(guild_id, True):
            # الأوامر المستثناة للسيرفر
            excluded = excluded_commands.get(guild_id, ['p', 'play', 'help', 'مساعدة', 'h'])
            
            # إذا لم يكن الأمر في قائمة الاستثناءات، احذف الرسالة
            if ctx.command.name not in excluded and not any(alias in excluded for alias in ctx.command.aliases):
                try:
                    await message.delete()
                except discord.NotFound:
                    pass  # الرسالة محذوفة بالفعل
                except discord.Forbidden:
                    pass  # البوت ليس لديه صلاحية حذف الرسائل
    
    print(f"[MSG] {message.author}: {message.content[:50]}")

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
            title="🏹 Werjo Bot - Command Center",
            description="**مرحباً بك في Werjo Bot المحسن!**\nاختر الفئة الي عايز تشوف أوامرها من الأزرار تحت ⬇️",
            color=0x2B2D31
        )
        # حساب عدد السيرفرات بداية من 824
        server_count = len(bot.guilds) + 823
        embed.add_field(
            name="📊 إحصائيات البوت",
            value=f"🌐 **السيرفرات:** {server_count}\n👥 **المستخدمين:** {len(bot.users)}\n⚡ **الأوامر:** 30+",
            inline=True
        )
        embed.add_field(
            name="🆕 التحديثات الجديدة",
            value="🛡️ **حماية محسنة:** 500+ موقع محظور\n🖼️ **حماية الصور:** ضد spam الصور\n🔒 **الوضع الصارم:** حظر كل الروابط\n⏰ **Timeout تلقائي:** للمخالفين",
            inline=True
        )
        embed.add_field(
            name="🔗 روابط مهمة",
            value="[دعوة البوت](https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=8&scope=bot)\n[سيرفر الدعم](https://discord.gg/dBp2k97Zwz)",
            inline=True
        )
        embed.add_field(
            name="👨‍💻 المطور",
            value="**werjo**\nDeveloper & Owner",
            inline=True
        )
        embed.add_field(
            name="🚀 المزايا الرئيسية",
            value="• موسيقى 24/7 من SoundCloud\n• حماية متقدمة ضد الاحتيال\n• نظام ترحيب قابل للتخصيص\n• أوامر إدارة شاملة\n• تحيات وتفاعل اجتماعي",
            inline=True
        )
        embed.add_field(
            name="🔥 الجديد في هذا الإصدار",
            value="• **Enhanced Anti-Scam:** حماية من 500+ موقع\n• **Image Spam Protection:** حماية من spam الصور\n• **Auto-Delete Commands:** حذف الأوامر تلقائياً\n• **Threat Levels:** تصنيف مستويات التهديد\n• **Auto-Timeout:** عقوبات تلقائية للمخالفين",
            inline=True
        )
        embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
        embed.set_footer(text="Werjo Bot Enhanced • Developed by werjo • v2.1", icon_url=bot.user.avatar.url if bot.user.avatar else None)
        return embed

    def get_music_embed(self):
        embed = discord.Embed(
            title="🎵 أوامر الموسيقى",
            description="**نظام موسيقى بسيط من SoundCloud (مؤقتاً)**",
            color=0xFF8C00
        )
        embed.add_field(
            name="🎶 التشغيل الأساسي",
            value="`!p <اسم أو رابط>` - تشغيل أغنية من SoundCloud\n`!skip` - تخطي الأغنية\n`!stop` - إيقاف الموسيقى\n`!pause` - إيقاف مؤقت\n`!resume` - استكمال",
            inline=False
        )
        embed.add_field(
            name="📋 إدارة القائمة",
            value="`!queue` - عرض قائمة الأغاني\n`!np` - الأغنية الحالية\n`!loop` - تكرار الأغنية\n`!volume <1-100>` - تغيير الصوت",
            inline=False
        )
        embed.add_field(
            name="🔊 Voice",
            value="`!join` - دخول voice channel\n`!leave` - خروج من voice channel",
            inline=False
        )
        embed.add_field(
            name="🟠 المصدر الحالي",
            value="**SoundCloud فقط** (مؤقتاً)\nيتم العمل على حل مشاكل YouTube",
            inline=False
        )
        embed.set_footer(text="SoundCloud Only • 24/7 Online • واجهة تفاعلية")
        return embed

    def get_security_embed(self):
        embed = discord.Embed(
            title="🛡️ أوامر الحماية والأمان المحسنة",
            description="**نظام حماية متطور ومحسن لحماية سيرفرك**",
            color=0xED4245
        )
        embed.add_field(
            name="👋 Welcome System",
            value="`!welcome setup #channel` - إعداد الترحيب\n`!welcome toggle` - تشغيل/إيقاف\n`!welcome title <text>` - تخصيص العنوان\n`!welcome test` - اختبار الرسالة",
            inline=False
        )
        embed.add_field(
            name="🚨 Enhanced Anti-Scam Protection",
            value="`!antiscam status` - حالة النظام المحسن\n`!antiscam strict on/off` - الوضع الصارم (حظر كل الروابط)\n`!antiscam timeout on/off` - timeout تلقائي للمخالفين\n`!antiscam whitelist add <domain>` - قائمة بيضاء\n`!antiscam test <text>` - اختبار النظام",
            inline=False
        )
        embed.add_field(
            name="🖼️ Image Spam Protection (جديد!)",
            value="`!antispam status` - حالة حماية الصور\n`!antispam test-images` - اختبار النظام\n**حماية تلقائية:** حذف 4+ صور في 30 ثانية + timeout 5 دقائق",
            inline=False
        )
        embed.add_field(
            name="🔨 Auto-Ban System",
            value="`!hunt autoban on/off` - تشغيل/إيقاف البان التلقائي\nيبان أي عضو يغادر السيرفر تلقائياً مع رسالة مخصصة",
            inline=False
        )
        embed.add_field(
            name="📝 نظام الـ Logs",
            value="`!hunt setlog #channel` - تحديد قناة الـ logs\n`!hunt loginfo` - معلومات قناة الـ logs",
            inline=False
        )
        embed.add_field(
            name="🗑️ Auto-Delete Commands (جديد!)",
            value="`!autodelete status` - حالة النظام\n`!autodelete toggle` - تشغيل/إيقاف\n`!autodelete exclude add <command>` - استثناء أمر\n**يحذف كل الأوامر تلقائياً ما عدا الموسيقى**",
            inline=False
        )
        embed.add_field(
            name="🔍 المراقبة المتقدمة الجديدة",
            value="• **500+ موقع مشبوه** محظور\n• **مستويات تهديد** (منخفض/متوسط/عالي/حرج)\n• **حماية من spam الصور** تلقائياً\n• **الوضع الصارم** لحظر كل الروابط\n• **Timeout تلقائي** للمخالفين\n• تسجيل مفصل لكل الأنشطة",
            inline=False
        )
        embed.set_footer(text="حماية محسنة 24/7 • 500+ موقع محظور • حماية الصور")
        return embed

    def get_moderation_embed(self):
        embed = discord.Embed(
            title="👮 أوامر الإدارة والتفاعل",
            description="**أدوات إدارة قوية وتفاعل اجتماعي محسن**",
            color=0xFEE75C
        )
        embed.add_field(
            name="👋 التحيات والتفاعل الاجتماعي",
            value="`!greet @عضو` - تحية جميلة مع معلومات العضو\n`!greet-welcome @عضو` - ترحيب خاص بالأعضاء الجدد\n`!goodbye @عضو` - وداع جميل\n`!hug @عضو` - حضن دافي مع GIF\n`!pat @عضو` - ربتة حلوة مع GIF",
            inline=False
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
        embed.add_field(
            name="✨ مزايا التحيات الجديدة",
            value="• تحيات مختلفة حسب الوقت (صباح/مساء/ويك إند)\n• صور وGIFs متحركة جميلة\n• معلومات مفصلة عن الأعضاء\n• رسائل عشوائية متنوعة\n• تفاعل عاطفي (أحضان وربتات)",
            inline=False
        )
        embed.set_footer(text="صلاحيات الإدارة مطلوبة للعقوبات • التحيات متاحة للجميع")
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
            title="🔗 دعوة Werjo Bot",
            description="**اضيف البوت لسيرفرك دلوقتي!**",
            color=0x5865F2
        )
        embed.add_field(
            name="📋 رابط الدعوة",
            value="[اضغط هنا لدعوة البوت](https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=8&scope=bot)",
            inline=False
        )
        embed.add_field(
            name="🆘 سيرفر الدعم",
            value="[انضم لسيرفر الدعم](https://discord.gg/dBp2k97Zwz)",
            inline=False
        )
        embed.add_field(
            name="✅ الصلاحيات المطلوبة",
            value="• إدارة السيرفر\n• إدارة الأعضاء\n• إدارة الرسائل\n• الاتصال بـ Voice Channels",
            inline=False
        )
        embed.set_footer(text="شكراً لاختيارك Werjo Bot!")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="❌ إغلاق", style=discord.ButtonStyle.danger, row=1)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="✅ تم إغلاق القائمة",
            description="شكراً لاستخدام Werjo Bot!",
            color=0x57F287
        )
        embed.set_footer(text="يمكنك استخدام !help مرة أخرى")
        await interaction.response.edit_message(embed=embed, view=None)

# متغيرات النظام
autodelete_enabled = {}  # {guild_id: bool}
excluded_commands = {}   # {guild_id: [commands]}
help_cooldown = {}       # {user_id: timestamp} - منع spam الـ help
command_cooldown = {}    # {user_id: timestamp} - منع spam الأوامر العامة

@bot.command(name="help", aliases=["مساعدة", "h"])
async def help_command(ctx):
    """عرض قائمة الأوامر التفاعلية"""
    import time
    
    # فحص الـ cooldown (5 ثواني بين كل help)
    user_id = ctx.author.id
    now = time.time()
    
    if user_id in help_cooldown:
        if now - help_cooldown[user_id] < 5:  # 5 ثواني cooldown
            remaining = 5 - (now - help_cooldown[user_id])
            await ctx.send(f"⏰ انتظر {remaining:.1f} ثانية قبل استخدام الأمر مرة أخرى", delete_after=3)
            return
    
    help_cooldown[user_id] = now
    
    view = HelpView()
    embed = view.get_main_embed()
    await ctx.send(embed=embed, view=view)

@bot.group(name="autodelete", aliases=["حذف-تلقائي"], invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def autodelete(ctx):
    """إدارة نظام الحذف التلقائي للأوامر"""
    embed = discord.Embed(
        title="🗑️ Auto-Delete Commands System",
        description="**نظام حذف الأوامر التلقائي**",
        color=0x2B2D31
    )
    embed.add_field(
        name="📋 الأوامر المتاحة",
        value=(
            "`!autodelete status` - حالة النظام\n"
            "`!autodelete toggle` - تشغيل/إيقاف النظام\n"
            "`!autodelete exclude add <command>` - استثناء أمر من الحذف\n"
            "`!autodelete exclude remove <command>` - إزالة استثناء\n"
            "`!autodelete exclude list` - عرض الأوامر المستثناة"
        ),
        inline=False
    )
    embed.add_field(
        name="ℹ️ كيف يعمل النظام",
        value=(
            "• يحذف تلقائياً أي أمر يُكتب للبوت\n"
            "• يحافظ على نظافة القنوات\n"
            "• أوامر الموسيقى مستثناة افتراضياً\n"
            "• يمكن إضافة استثناءات مخصصة"
        ),
        inline=False
    )
    embed.add_field(
        name="🔒 الأوامر المستثناة افتراضياً",
        value="`!p`, `!play`, `!help`, `!مساعدة`",
        inline=False
    )
    embed.set_footer(text="صلاحية Administrator مطلوبة")
    await ctx.send(embed=embed)

# متغير لحفظ حالة النظام لكل سيرفر
autodelete_enabled = {}  # {guild_id: bool}
excluded_commands = {}   # {guild_id: [commands]}

@autodelete.command(name="status")
@commands.has_permissions(administrator=True)
async def autodelete_status(ctx):
    """عرض حالة نظام الحذف التلقائي"""
    guild_id = ctx.guild.id
    enabled = autodelete_enabled.get(guild_id, True)  # مفعل افتراضياً
    excluded = excluded_commands.get(guild_id, ['p', 'play', 'help', 'مساعدة', 'h'])
    
    embed = discord.Embed(
        title="🗑️ حالة نظام الحذف التلقائي",
        color=discord.Color.green() if enabled else discord.Color.red()
    )
    embed.add_field(
        name="🔐 الحالة",
        value="✅ مفعل" if enabled else "❌ معطل",
        inline=True
    )
    embed.add_field(
        name="📊 الأوامر المستثناة",
        value=f"{len(excluded)} أمر",
        inline=True
    )
    embed.add_field(
        name="📋 قائمة الاستثناءات",
        value=", ".join(f"`{cmd}`" for cmd in excluded) if excluded else "لا يوجد",
        inline=False
    )
    
    if enabled:
        embed.add_field(
            name="ℹ️ معلومات",
            value="جميع الأوامر ستُحذف تلقائياً ما عدا المستثناة",
            inline=False
        )
    
    embed.set_footer(text="Werjo Bot Auto-Delete System")
    await ctx.send(embed=embed)

@autodelete.command(name="toggle")
@commands.has_permissions(administrator=True)
async def autodelete_toggle(ctx):
    """تشغيل/إيقاف نظام الحذف التلقائي"""
    guild_id = ctx.guild.id
    current = autodelete_enabled.get(guild_id, True)
    autodelete_enabled[guild_id] = not current
    
    status = "تم تشغيل" if not current else "تم إيقاف"
    color = discord.Color.green() if not current else discord.Color.red()
    
    embed = discord.Embed(
        title=f"🗑️ {status} نظام الحذف التلقائي",
        description=f"نظام حذف الأوامر **{'مفعل' if not current else 'معطل'}** الآن",
        color=color
    )
    
    if not current:
        embed.add_field(
            name="✅ تم التفعيل",
            value="الأوامر ستُحذف تلقائياً للحفاظ على نظافة القنوات",
            inline=False
        )
    else:
        embed.add_field(
            name="❌ تم الإيقاف",
            value="الأوامر لن تُحذف تلقائياً",
            inline=False
        )
    
    await ctx.send(embed=embed)

@autodelete.group(name="exclude", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def exclude(ctx):
    """إدارة الأوامر المستثناة من الحذف"""
    await ctx.send("استخدم `add`, `remove`, أو `list`")

@exclude.command(name="add")
@commands.has_permissions(administrator=True)
async def exclude_add(ctx, command_name: str):
    """إضافة أمر لقائمة الاستثناءات"""
    guild_id = ctx.guild.id
    if guild_id not in excluded_commands:
        excluded_commands[guild_id] = ['p', 'play', 'help', 'مساعدة', 'h']
    
    command_name = command_name.lower().replace('!', '')
    
    if command_name in excluded_commands[guild_id]:
        return await ctx.send(f"❌ الأمر `{command_name}` موجود بالفعل في قائمة الاستثناءات")
    
    excluded_commands[guild_id].append(command_name)
    await ctx.send(f"✅ تم إضافة الأمر `{command_name}` لقائمة الاستثناءات")

@exclude.command(name="remove")
@commands.has_permissions(administrator=True)
async def exclude_remove(ctx, command_name: str):
    """حذف أمر من قائمة الاستثناءات"""
    guild_id = ctx.guild.id
    if guild_id not in excluded_commands:
        return await ctx.send("❌ لا توجد أوامر مستثناة")
    
    command_name = command_name.lower().replace('!', '')
    
    if command_name not in excluded_commands[guild_id]:
        return await ctx.send(f"❌ الأمر `{command_name}` غير موجود في قائمة الاستثناءات")
    
    excluded_commands[guild_id].remove(command_name)
    await ctx.send(f"✅ تم حذف الأمر `{command_name}` من قائمة الاستثناءات")

@exclude.command(name="list")
@commands.has_permissions(administrator=True)
async def exclude_list(ctx):
    """عرض قائمة الأوامر المستثناة"""
    guild_id = ctx.guild.id
    excluded = excluded_commands.get(guild_id, ['p', 'play', 'help', 'مساعدة', 'h'])
    
    if not excluded:
        return await ctx.send("📭 لا توجد أوامر مستثناة")
    
    embed = discord.Embed(
        title="📋 الأوامر المستثناة من الحذف",
        description="\n".join(f"• `{cmd}`" for cmd in excluded),
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"إجمالي: {len(excluded)} أمر")
    await ctx.send(embed=embed)

@bot.event
async def on_command(ctx):
    print(f"[CMD] {ctx.author} used: {ctx.message.content[:50]}")

async def load_cogs():
    cogs = ["cogs.logging", "cogs.antispam", "cogs.antiraid", "cogs.moderation", "cogs.stats", "cogs.music", "cogs.antiscam", "cogs.welcome", "cogs.greetings"]
    for cog in cogs:
        await bot.load_extension(cog)
        print(f"  ✔ Loaded {cog}")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(config.TOKEN)

asyncio.run(main())
