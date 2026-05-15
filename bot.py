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
    
    # معالجة الأوامر مع حماية من التكرار
    ctx = await bot.get_context(message)
    if ctx.valid and ctx.command:
        import time
        user_id = message.author.id
        now = time.time()
        
        # منع spam الأوامر
        if user_id in command_cooldown:
            if now - command_cooldown[user_id] < 1:  # ثانية واحدة cooldown
                try:
                    await message.delete()
                except:
                    pass
                return
        
        command_cooldown[user_id] = now
        
        # معالجة الأمر مرة واحدة فقط
        await bot.process_commands(message)
        
        # حذف الأمر إذا مطلوب
        guild_id = message.guild.id if message.guild else None
        if guild_id and autodelete_enabled.get(guild_id, True):
            excluded = excluded_commands.get(guild_id, ['p', 'play', 'help', 'مساعدة', 'h'])
            
            if ctx.command.name not in excluded and not any(alias in excluded for alias in ctx.command.aliases):
                try:
                    await asyncio.sleep(0.5)  # انتظار قصير قبل الحذف
                    await message.delete()
                except:
                    pass
    else:
        # إذا مش أمر، معالج عادي
        await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    print(f"[CMD ERROR] {ctx.command} | {error}")

# ─── Help Command GUI ──────────────────────────────────────────────────────
class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.current_page = "main"
        self._interaction_lock = False  # منع التفاعلات المتعددة

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """فحص التفاعلات لمنع الـ spam"""
        if self._interaction_lock:
            await interaction.response.send_message("⏰ انتظر قليلاً...", ephemeral=True)
            return False
        
        self._interaction_lock = True
        # إلغاء القفل بعد ثانية واحدة
        asyncio.create_task(self._unlock_after_delay())
        return True
    
    async def _unlock_after_delay(self):
        """إلغاء قفل التفاعل بعد تأخير"""
        await asyncio.sleep(1)
        self._interaction_lock = False

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
            value="🛡️ **حماية محسنة:** 500+ موقع محظور\n🖼️ **حماية الصور:** ضد spam الصور\n🔒 **الوضع الصارم:** حظر كل الروابط\n⏰ **Timeout تلقائي:** للمخالفين\n📋 **What You Missed:** تتبع الأنشطة",
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
            value="• موسيقى 24/7 من SoundCloud\n• حماية متقدمة ضد الاحتيال\n• نظام ترحيب قابل للتخصيص\n• أوامر إدارة شاملة\n• تحيات وتفاعل اجتماعي\n• تتبع الأنشطة المفقودة",
            inline=True
        )
        embed.add_field(
            name="🔥 الجديد في هذا الإصدار",
            value="• **Enhanced Anti-Scam:** حماية من 500+ موقع\n• **Image Spam Protection:** حماية من spam الصور\n• **Auto-Delete Commands:** حذف الأوامر تلقائياً\n• **Threat Levels:** تصنيف مستويات التهديد\n• **Auto-Timeout:** عقوبات تلقائية للمخالفين\n• **What You Missed:** تتبع الأنشطة المفقودة",
            inline=True
        )
        embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
        embed.set_footer(text="Werjo Bot Enhanced • Developed by werjo • v2.2", icon_url=bot.user.avatar.url if bot.user.avatar else None)
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
            title="📊 أوامر الإحصائيات والأنشطة",
            description="**معلومات وإحصائيات مفصلة + تتبع الأنشطة**",
            color=0x57F287
        )
        embed.add_field(
            name="📋 What You Missed (جديد!)",
            value="`!missed` - عرض الأنشطة التي فاتتك\n`!missed <ساعات>` - تخصيص الفترة الزمنية\n`!فاتني` - الأمر بالعربية\n`!recent` - آخر الأنشطة بشكل سريع\n**يُظهر:** الانضمامات، المغادرات، الرسائل المهمة، الأنشطة الصوتية، الألعاب",
            inline=False
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
        embed.add_field(
            name="⚙️ إدارة تتبع الأنشطة (للإداريين)",
            value="`!activity status` - حالة النظام\n`!activity cleanup` - تنظيف الأنشطة القديمة\n`!activity stats` - إحصائيات النظام",
            inline=False
        )
        embed.add_field(
            name="✨ مزايا تتبع الأنشطة",
            value="• تتبع تلقائي لجميع الأنشطة المهمة\n• عرض مخصص حسب آخر زيارة\n• تجميع ذكي للأنشطة المتشابهة\n• تنظيف تلقائي للبيانات القديمة\n• واجهة جميلة وسهلة القراءة",
            inline=False
        )
        embed.set_footer(text="إحصائيات محدثة لحظياً • تتبع الأنشطة 24/7")
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
    
    # فحص الـ cooldown (10 ثواني بين كل help)
    user_id = ctx.author.id
    now = time.time()
    
    if user_id in help_cooldown:
        if now - help_cooldown[user_id] < 10:  # 10 ثواني cooldown
            remaining = 10 - (now - help_cooldown[user_id])
            embed = discord.Embed(
                title="⏰ Cooldown Active",
                description=f"انتظر **{remaining:.1f} ثانية** قبل استخدام الأمر مرة أخرى",
                color=discord.Color.orange()
            )
            embed.set_footer(text="لمنع spam الأوامر")
            await ctx.send(embed=embed, delete_after=5)
            return
    
    help_cooldown[user_id] = now
    
    # التأكد من عدم وجود رد سابق
    try:
        view = HelpView()
        embed = view.get_main_embed()
        await ctx.send(embed=embed, view=view)
    except Exception as e:
        print(f"[HELP ERROR] {e}")
        # رد بسيط في حالة الخطأ
        await ctx.send("❌ حدث خطأ في عرض القائمة، جرب مرة أخرى")

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

@bot.command(name="restart", aliases=["إعادة-تشغيل"])
@commands.is_owner()
async def restart_bot(ctx):
    """إعادة تشغيل البوت (للمطور فقط)"""
    embed = discord.Embed(
        title="🔄 إعادة تشغيل البوت",
        description="جاري إعادة تشغيل البوت...",
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)
    
    # مسح الـ cooldowns
    help_cooldown.clear()
    command_cooldown.clear()
    
    print("[RESTART] Bot restarting...")
    await bot.close()

@bot.command(name="clear-cooldowns", aliases=["مسح-كولداون"])
@commands.has_permissions(administrator=True)
async def clear_cooldowns(ctx):
    """مسح جميع الـ cooldowns"""
    help_cooldown.clear()
    command_cooldown.clear()
    
    embed = discord.Embed(
        title="✅ تم مسح الـ Cooldowns",
        description="تم مسح جميع cooldowns الأوامر والـ help",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.event
async def on_command(ctx):
    print(f"[CMD] {ctx.author} used: {ctx.message.content[:50]}")

async def load_cogs():
    cogs = ["cogs.logging", "cogs.antispam", "cogs.antiraid", "cogs.moderation", "cogs.stats", "cogs.music", "cogs.antiscam", "cogs.welcome", "cogs.greetings", "cogs.activity_tracker"]
    loaded_cogs = []
    
    for cog in cogs:
        try:
            if cog not in bot.extensions:  # تحقق من عدم تحميل الـ cog مسبقاً
                await bot.load_extension(cog)
                loaded_cogs.append(cog)
                print(f"  ✔ Loaded {cog}")
            else:
                print(f"  ⚠ {cog} already loaded, skipping")
        except Exception as e:
            print(f"  ❌ Failed to load {cog}: {e}")
    
    print(f"📦 Successfully loaded {len(loaded_cogs)} cogs")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(config.TOKEN)

asyncio.run(main())
