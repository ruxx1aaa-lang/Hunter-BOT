import discord
from discord.ext import commands
import random
from datetime import datetime, timezone

class GreetingsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # قائمة التحيات المختلفة
    GREETINGS = [
        {
            "title": "👋 أهلاً وسهلاً!",
            "message": "مرحباً {mention}! 🌟\nأهلاً بيك في السيرفر، نورت المكان! ✨",
            "color": 0x00FF7F,
            "emoji": "🌟"
        },
        {
            "title": "🎉 أهلاً بالحبيب!",
            "message": "يا أهلاً {mention}! 🎊\nمنور السيرفر بوجودك الجميل! 💫",
            "color": 0xFF69B4,
            "emoji": "🎊"
        },
        {
            "title": "🔥 مرحباً بالأسطورة!",
            "message": "أهلاً {mention}! 🚀\nوحشتنا يا غالي، نورت المكان! 🌈",
            "color": 0xFF4500,
            "emoji": "🚀"
        },
        {
            "title": "💎 أهلاً بالملك!",
            "message": "مرحباً {mention}! 👑\nشرفت السيرفر بحضورك الكريم! ✨",
            "color": 0x9932CC,
            "emoji": "👑"
        },
        {
            "title": "🌟 أهلاً بالنجم!",
            "message": "يا هلا {mention}! ⭐\nنورت السيرفر، أهلاً وسهلاً بيك! 🎯",
            "color": 0x1E90FF,
            "emoji": "⭐"
        },
        {
            "title": "🎈 مرحباً بالحبيب!",
            "message": "أهلاً {mention}! 🎪\nوحشنا شوفتك، نورت المكان! 🎨",
            "color": 0x32CD32,
            "emoji": "🎪"
        },
        {
            "title": "🌺 أهلاً بالغالي!",
            "message": "مرحباً {mention}! 🌸\nأهلاً وسهلاً، منور السيرفر! 🦋",
            "color": 0xFF1493,
            "emoji": "🌸"
        },
        {
            "title": "⚡ أهلاً بالبطل!",
            "message": "يا أهلاً {mention}! 💪\nوصل البطل! نورت السيرفر يا غالي! 🏆",
            "color": 0xFFD700,
            "emoji": "💪"
        }
    ]

    # تحيات خاصة للمناسبات
    SPECIAL_GREETINGS = {
        "morning": {
            "title": "🌅 صباح الخير!",
            "message": "صباح الخير {mention}! ☀️\nيوم جميل عليك يا غالي! 🌻",
            "color": 0xFFA500,
            "emoji": "☀️"
        },
        "evening": {
            "title": "🌙 مساء الخير!",
            "message": "مساء الخير {mention}! 🌟\nمساء جميل عليك! 🌃",
            "color": 0x4B0082,
            "emoji": "🌙"
        },
        "weekend": {
            "title": "🎉 ويك إند سعيد!",
            "message": "أهلاً {mention}! 🎊\nويك إند سعيد، استمتع بوقتك! 🏖️",
            "color": 0xFF6347,
            "emoji": "🎊"
        }
    }

    def get_time_based_greeting(self):
        """جيب تحية حسب الوقت"""
        now = datetime.now()
        hour = now.hour
        
        if 5 <= hour < 12:
            return self.SPECIAL_GREETINGS["morning"]
        elif 17 <= hour < 22:
            return self.SPECIAL_GREETINGS["evening"]
        elif now.weekday() >= 5:  # السبت والأحد
            return self.SPECIAL_GREETINGS["weekend"]
        else:
            return random.choice(self.GREETINGS)

    @commands.command(name="greet", aliases=["تحية", "سلام"])
    async def greet_user(self, ctx, member: discord.Member = None):
        """يرسل تحية جميلة لعضو | !greet @عضو"""
        if member is None:
            return await ctx.send("❌ لازم تمنشن العضو الي عايز تسلم عليه!\nمثال: `!greet @العضو`")
        
        if member.bot:
            return await ctx.send("🤖 البوتات مش محتاجة تحية، هما مش بيحسوا! 😄")
        
        if member == ctx.author:
            return await ctx.send("😅 مش محتاج تسلم على نفسك يا حبيبي!")

        # اختيار تحية حسب الوقت أو عشوائية
        greeting = self.get_time_based_greeting()
        
        # إنشاء الـ embed
        embed = discord.Embed(
            title=greeting["title"],
            description=greeting["message"].format(mention=member.mention),
            color=greeting["color"],
            timestamp=datetime.now(timezone.utc)
        )
        
        # إضافة معلومات العضو
        embed.add_field(
            name="👤 العضو",
            value=f"**{member.display_name}**\n`{member.name}`",
            inline=True
        )
        
        embed.add_field(
            name="📅 انضم للسيرفر",
            value=f"<t:{int(member.joined_at.timestamp())}:R>",
            inline=True
        )
        
        embed.add_field(
            name="🎭 الرول الأعلى",
            value=member.top_role.mention if member.top_role.name != "@everyone" else "لا يوجد",
            inline=True
        )
        
        # إضافة صورة العضو
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # إضافة صورة جميلة للتحية
        greeting_gifs = [
            "https://media.tenor.com/images/2c8b5c7e8f5a4d3c9b1a2e3f4g5h6i7j/tenor.gif",
            "https://media.giphy.com/media/hvRJCLFzcasrR4ia7z/giphy.gif",
            "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif"
        ]
        embed.set_image(url=random.choice(greeting_gifs))
        
        # Footer مع معلومات المرسل
        embed.set_footer(
            text=f"تحية من {ctx.author.display_name} • Werjo Bot",
            icon_url=ctx.author.display_avatar.url
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="welcome", aliases=["ترحيب"])
    async def welcome_user(self, ctx, member: discord.Member = None):
        """ترحيب خاص بالأعضاء الجدد | !welcome @عضو"""
        if member is None:
            return await ctx.send("❌ لازم تمنشن العضو الي عايز ترحب بيه!\nمثال: `!welcome @العضو`")
        
        if member.bot:
            return await ctx.send("🤖 البوتات مش محتاجة ترحيب!")

        # حساب عمر العضوية في السيرفر
        days_in_server = (datetime.now(timezone.utc) - member.joined_at).days
        
        embed = discord.Embed(
            title="🎉 مرحباً بالعضو الجديد!",
            description=f"**أهلاً وسهلاً {member.mention}!** 🌟\n\nمرحباً بيك في **{ctx.guild.name}**، نورت السيرفر! ✨",
            color=0x00FF7F,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="👤 معلومات العضو",
            value=f"**الاسم:** {member.display_name}\n**ID:** `{member.id}`",
            inline=True
        )
        
        embed.add_field(
            name="📊 إحصائيات",
            value=f"**العضو رقم:** {len(ctx.guild.members)}\n**في السيرفر منذ:** {days_in_server} يوم",
            inline=True
        )
        
        embed.add_field(
            name="🎯 نصائح للبداية",
            value="• اقرأ القوانين 📋\n• تفاعل مع الأعضاء 💬\n• استمتع بوقتك! 🎉",
            inline=False
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url="https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif")
        
        embed.set_footer(
            text=f"ترحيب من {ctx.author.display_name} • {ctx.guild.name}",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="goodbye", aliases=["وداع"])
    async def goodbye_user(self, ctx, member: discord.Member = None):
        """وداع للأعضاء | !goodbye @عضو"""
        if member is None:
            return await ctx.send("❌ لازم تمنشن العضو الي عايز تودعه!\nمثال: `!goodbye @العضو`")
        
        if member.bot:
            return await ctx.send("🤖 البوتات مش محتاجة وداع!")

        embed = discord.Embed(
            title="👋 مع السلامة!",
            description=f"**وداعاً {member.mention}!** 😢\n\nهنفتقدك في **{ctx.guild.name}**، ربنا يوفقك! 🌟",
            color=0xFF6B6B,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="💔 سنفتقدك",
            value="كان وجودك نور في السيرفر\nنتمنى نشوفك تاني قريب! 🤗",
            inline=False
        )
        
        embed.add_field(
            name="📊 الذكريات",
            value=f"**وقت في السيرفر:** {(datetime.now(timezone.utc) - member.joined_at).days} يوم\n**آخر نشاط:** <t:{int(datetime.now().timestamp())}:R>",
            inline=True
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url="https://media.giphy.com/media/2WxWfiavndgcM/giphy.gif")
        
        embed.set_footer(
            text=f"وداع من {ctx.author.display_name} • {ctx.guild.name}",
            icon_url=ctx.author.display_avatar.url
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="hug", aliases=["حضن"])
    async def hug_user(self, ctx, member: discord.Member = None):
        """يعطي حضن لعضو | !hug @عضو"""
        if member is None:
            return await ctx.send("❌ مين الي عايز تحضنه؟\nمثال: `!hug @العضو`")
        
        if member.bot:
            return await ctx.send("🤖 البوتات مش بتحس بالأحضان!")
        
        if member == ctx.author:
            return await ctx.send("🤗 حضن لنفسك؟ خد حضن مني بدلاً من كده! *حضن*")

        hug_messages = [
            f"🤗 {ctx.author.mention} بيحضن {member.mention} حضن دافي!",
            f"💕 {member.mention} خد حضن جميل من {ctx.author.mention}!",
            f"🫂 حضن كبير من {ctx.author.mention} لـ {member.mention}!",
            f"❤️ {ctx.author.mention} بيرسل حضن مليان حب لـ {member.mention}!"
        ]

        embed = discord.Embed(
            title="🤗 حضن دافي!",
            description=random.choice(hug_messages),
            color=0xFFB6C1,
            timestamp=datetime.now(timezone.utc)
        )
        
        hug_gifs = [
            "https://media.giphy.com/media/3M4NpbLCTxBqU/giphy.gif",
            "https://media.giphy.com/media/lrr9rHuoJOE0w/giphy.gif",
            "https://media.giphy.com/media/EvYHHSntaIl5m/giphy.gif"
        ]
        
        embed.set_image(url=random.choice(hug_gifs))
        embed.set_footer(text="أحضان مجانية للجميع! 💕")
        
        await ctx.send(embed=embed)

    @commands.command(name="pat", aliases=["ربت"])
    async def pat_user(self, ctx, member: discord.Member = None):
        """يربت على راس عضو | !pat @عضو"""
        if member is None:
            return await ctx.send("❌ مين الي عايز تربت عليه؟\nمثال: `!pat @العضو`")
        
        if member.bot:
            return await ctx.send("🤖 البوتات مش بتحس بالربت!")
        
        if member == ctx.author:
            return await ctx.send("😅 بتربت على نفسك؟ *ربت ربت*")

        pat_messages = [
            f"😊 {ctx.author.mention} بيربت على راس {member.mention} بحنان!",
            f"🥰 {member.mention} خد ربتة حلوة من {ctx.author.mention}!",
            f"😌 ربتة لطيفة من {ctx.author.mention} لـ {member.mention}!",
            f"💆‍♀️ {ctx.author.mention} بيدلع {member.mention} بربتة حلوة!"
        ]

        embed = discord.Embed(
            title="😊 ربتة حلوة!",
            description=random.choice(pat_messages),
            color=0x98FB98,
            timestamp=datetime.now(timezone.utc)
        )
        
        pat_gifs = [
            "https://media.giphy.com/media/KztT2c4u8mYYUiMKdJ/giphy.gif",
            "https://media.giphy.com/media/3o6ZtpxSZbQRRnwCKQ/giphy.gif",
            "https://media.giphy.com/media/l2QDM9Jnim1YVILXa/giphy.gif"
        ]
        
        embed.set_image(url=random.choice(pat_gifs))
        embed.set_footer(text="ربتات مجانية للجميع! 😊")
        
        await ctx.send(embed=embed)

    @commands.command(name="greetings-help", aliases=["تحيات-مساعدة"])
    async def greetings_help(self, ctx):
        """عرض جميع أوامر التحيات"""
        embed = discord.Embed(
            title="👋 أوامر التحيات والتفاعل",
            description="**جميع أوامر التحية والتفاعل مع الأعضاء**",
            color=0x00CED1
        )
        
        embed.add_field(
            name="🎉 التحيات الأساسية",
            value="`!greet @عضو` - تحية جميلة\n`!welcome @عضو` - ترحيب بعضو جديد\n`!goodbye @عضو` - وداع عضو",
            inline=False
        )
        
        embed.add_field(
            name="💕 التفاعل العاطفي",
            value="`!hug @عضو` - حضن دافي\n`!pat @عضو` - ربتة حلوة",
            inline=False
        )
        
        embed.add_field(
            name="✨ مزايا خاصة",
            value="• تحيات مختلفة حسب الوقت\n• رسائل عشوائية متنوعة\n• صور وGIFs جميلة\n• معلومات العضو",
            inline=False
        )
        
        embed.add_field(
            name="🎯 أمثلة",
            value="`!greet @werjo` - تحية لـ werjo\n`!hug @صديق` - حضن لصديق\n`!welcome @عضو_جديد` - ترحيب",
            inline=False
        )
        
        embed.set_footer(text="استخدم الأوامر لنشر المحبة في السيرفر! 💕")
        await ctx.send(embed=embed)

    @greet_user.error
    async def greet_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ مش لاقي العضو ده! تأكد من الاسم أو المنشن.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ لازم تمنشن العضو!\nمثال: `!greet @العضو`")

async def setup(bot):
    await bot.add_cog(GreetingsCog(bot))