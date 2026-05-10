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
        # {user_id: [timestamps]} - للصور
        self.image_tracker = defaultdict(list)

    def get_log_channel(self, guild):
        return guild.get_channel(config.LOG_CHANNEL_ID)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        await self.check_spam(message)
        await self.check_image_spam(message)
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

    async def check_image_spam(self, message):
        """فحص spam الصور - حذف أي 4 صور أو أكتر في وقت قصير"""
        # تحقق من وجود صور أو attachments
        if not message.attachments:
            return
        
        # تحقق من أن الـ attachments صور
        image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')
        has_images = any(
            attachment.filename.lower().endswith(image_extensions) 
            for attachment in message.attachments
        )
        
        if not has_images:
            return
        
        user_id = message.author.id
        now = datetime.now(timezone.utc).timestamp()
        
        # إضافة timestamp للصورة الحالية
        self.image_tracker[user_id].append(now)
        
        # إزالة الـ timestamps القديمة (أكتر من 30 ثانية)
        self.image_tracker[user_id] = [
            t for t in self.image_tracker[user_id]
            if now - t < 30  # 30 ثانية
        ]
        
        # إذا وصل لـ 4 صور أو أكتر في 30 ثانية
        if len(self.image_tracker[user_id]) >= 4:
            self.image_tracker[user_id] = []  # مسح الـ tracker
            await self.handle_image_spam(message)

    async def handle_image_spam(self, message):
        """التعامل مع spam الصور"""
        member = message.author
        guild = message.guild
        ch = self.get_log_channel(guild)
        
        # حذف الرسالة الحالية
        try:
            await message.delete()
        except discord.Forbidden:
            pass
        
        # حذف آخر 10 رسائل من نفس المستخدم تحتوي على صور
        try:
            def check_user_images(m):
                return (m.author == member and 
                        m.attachments and 
                        any(att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp')) 
                            for att in m.attachments))
            
            await message.channel.purge(limit=20, check=check_user_images)
        except discord.Forbidden:
            pass
        
        # timeout للعضو
        try:
            duration = discord.utils.utcnow() + timedelta(minutes=5)  # 5 دقائق timeout
            await member.timeout(duration, reason="Image spam - Werjo Bot")
        except discord.Forbidden:
            pass
        
        # تحذير في القناة
        try:
            warn_embed = discord.Embed(
                title="🖼️ Image Spam Detected",
                description=f"**{member.mention}** تم حذف الصور وإعطاء timeout لمدة 5 دقائق بسبب spam الصور.",
                color=discord.Color.red()
            )
            warn_embed.add_field(
                name="⚠️ تحذير",
                value="تجنب إرسال أكثر من 3 صور في وقت قصير",
                inline=False
            )
            warn_embed.set_footer(text="Werjo Bot - Anti-Spam Protection")
            
            warn_msg = await message.channel.send(embed=warn_embed)
            await asyncio.sleep(10)
            await warn_msg.delete()
        except discord.Forbidden:
            pass
        
        # تسجيل في الـ log
        if ch:
            embed = discord.Embed(
                title="🖼️ Image Spam Detected",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="العضو", value=f"{member} ({member.id})", inline=True)
            embed.add_field(name="القناة", value=message.channel.mention, inline=True)
            embed.add_field(name="عدد الصور", value="4+ صور في 30 ثانية", inline=True)
            embed.add_field(name="الإجراء", value="حذف الصور + timeout 5 دقائق", inline=False)
            embed.set_footer(text="Werjo Bot Security System")
            
            try:
                await ch.send(embed=embed)
            except discord.Forbidden:
                pass

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

    @commands.group(name="antispam", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def antispam(self, ctx):
        """إدارة نظام مكافحة السبام"""
        embed = discord.Embed(
            title="🛡️ Anti-Spam System",
            description="**نظام حماية متطور ضد السبام**",
            color=0x2B2D31
        )
        embed.add_field(
            name="📋 الأوامر المتاحة",
            value=(
                "`!antispam status` - حالة النظام\n"
                "`!antispam test-images` - اختبار حماية الصور\n"
                "`!antispam clear-tracker @user` - مسح tracker مستخدم"
            ),
            inline=False
        )
        embed.add_field(
            name="🖼️ حماية الصور الجديدة",
            value=(
                "• حذف تلقائي عند إرسال **4+ صور في 30 ثانية**\n"
                "• Timeout للمخالف لمدة **5 دقائق**\n"
                "• حذف آخر الصور المرسلة من نفس المستخدم\n"
                "• تسجيل مفصل في الـ logs"
            ),
            inline=False
        )
        embed.add_field(
            name="🔍 أنواع الملفات المحمية",
            value="PNG, JPG, JPEG, GIF, WEBP, BMP",
            inline=False
        )
        embed.set_footer(text="صلاحية Administrator مطلوبة • Werjo Bot")
        await ctx.send(embed=embed)

    @antispam.command(name="status")
    @commands.has_permissions(administrator=True)
    async def antispam_status(self, ctx):
        """عرض حالة نظام مكافحة السبام"""
        embed = discord.Embed(
            title="🛡️ حالة نظام Anti-Spam المحسن",
            color=discord.Color.green()
        )
        
        # إحصائيات الرسائل
        total_tracked_users = len(self.message_tracker)
        total_image_tracked = len(self.image_tracker)
        
        embed.add_field(
            name="📊 إحصائيات عامة", 
            value=f"**المستخدمين المتتبعين:** {total_tracked_users}\n**متتبعي الصور:** {total_image_tracked}", 
            inline=False
        )
        embed.add_field(name="🖼️ حماية الصور", value="✅ مفعلة", inline=True)
        embed.add_field(name="📏 حد الصور", value="4 صور", inline=True)
        embed.add_field(name="⏰ الوقت المسموح", value="30 ثانية", inline=True)
        embed.add_field(name="⏱️ مدة Timeout", value="5 دقائق", inline=True)
        embed.add_field(name="🗑️ حذف تلقائي", value="✅ مفعل", inline=True)
        embed.add_field(name="📝 التسجيل", value="✅ مفعل", inline=True)
        
        # معلومات إضافية
        embed.add_field(
            name="🔧 آلية العمل",
            value="النظام يتتبع كل صورة يرسلها المستخدم ويحذف الرسائل عند تجاوز الحد المسموح",
            inline=False
        )
        
        embed.set_footer(text="Werjo Bot Enhanced Anti-Spam System")
        await ctx.send(embed=embed)

    @antispam.command(name="test-images")
    @commands.has_permissions(administrator=True)
    async def test_images(self, ctx):
        """اختبار نظام حماية الصور"""
        embed = discord.Embed(
            title="🧪 اختبار حماية الصور",
            description="**معلومات النظام الحالي:**",
            color=discord.Color.blue()
        )
        
        user_images = len(self.image_tracker.get(ctx.author.id, []))
        
        embed.add_field(
            name="📊 حالتك الحالية", 
            value=f"الصور المرسلة مؤخراً: **{user_images}/4**", 
            inline=False
        )
        embed.add_field(
            name="⚠️ تحذير", 
            value="إذا أرسلت **4 صور في 30 ثانية** ستحصل على timeout لمدة 5 دقائق", 
            inline=False
        )
        embed.add_field(
            name="🔧 الإعدادات الحالية", 
            value="**الحد الأقصى:** 4 صور\n**الوقت المسموح:** 30 ثانية\n**Timeout:** 5 دقائق\n**حذف الصور:** تلقائي", 
            inline=False
        )
        embed.add_field(
            name="💡 نصيحة",
            value="لاختبار النظام، جرب إرسال 4 صور بسرعة (سيتم حذفها وإعطاؤك timeout)",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @antispam.command(name="clear-tracker")
    @commands.has_permissions(administrator=True)
    async def clear_tracker(self, ctx, member: discord.Member = None):
        """مسح tracker مستخدم معين أو الكل"""
        if member:
            # مسح tracker مستخدم معين
            if member.id in self.image_tracker:
                del self.image_tracker[member.id]
            if member.id in self.message_tracker:
                del self.message_tracker[member.id]
            
            embed = discord.Embed(
                title="✅ تم مسح Tracker",
                description=f"تم مسح tracker الصور والرسائل لـ **{member.display_name}**",
                color=discord.Color.green()
            )
        else:
            # مسح كل الـ trackers
            self.image_tracker.clear()
            self.message_tracker.clear()
            
            embed = discord.Embed(
                title="✅ تم مسح جميع Trackers",
                description="تم مسح جميع trackers الصور والرسائل لكل المستخدمين",
                color=discord.Color.green()
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AntiSpamCog(bot))
