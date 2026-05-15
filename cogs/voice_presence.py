import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import aiosqlite

class VoicePresence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "hunter.db"
        self.voice_ghosts = {}  # {channel_id: {user_id: {'username': str, 'left_at': datetime, 'message_id': int}}}
        self.cleanup_task.start()
        
    async def cog_load(self):
        """إعداد قاعدة البيانات عند تحميل الـ cog"""
        await self.init_db()
        print("✅ Voice Presence (User was here) loaded successfully")
    
    def cog_unload(self):
        """إيقاف المهام عند إلغاء تحميل الـ cog"""
        self.cleanup_task.cancel()
    
    async def init_db(self):
        """إنشاء جداول قاعدة البيانات"""
        async with aiosqlite.connect(self.db_path) as db:
            # جدول تتبع الـ voice presence
            await db.execute("""
                CREATE TABLE IF NOT EXISTS voice_presence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    user_id INTEGER,
                    username TEXT,
                    left_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    message_id INTEGER
                )
            """)
            
            # جدول إعدادات الـ voice presence لكل سيرفر
            await db.execute("""
                CREATE TABLE IF NOT EXISTS voice_presence_settings (
                    guild_id INTEGER PRIMARY KEY,
                    enabled BOOLEAN DEFAULT 1,
                    duration_minutes INTEGER DEFAULT 30,
                    show_in_channel BOOLEAN DEFAULT 1,
                    ghost_message_format TEXT DEFAULT '{username} was here'
                )
            """)
            
            await db.commit()
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """تتبع دخول وخروج الأعضاء من Voice Channels"""
        if member.bot:
            return
        
        # التحقق من تفعيل الميزة في السيرفر
        if not await self.is_enabled(member.guild.id):
            return
        
        # إذا خرج من voice channel
        if before.channel and not after.channel:
            await self.add_voice_ghost(before.channel, member)
        
        # إذا دخل voice channel (إزالة الـ ghost إذا كان موجود)
        elif after.channel and not before.channel:
            await self.remove_voice_ghost(after.channel, member)
        
        # إذا انتقل بين channels
        elif before.channel and after.channel and before.channel != after.channel:
            await self.add_voice_ghost(before.channel, member)
            await self.remove_voice_ghost(after.channel, member)
    
    async def add_voice_ghost(self, channel, member):
        """إضافة ghost message عند مغادرة voice channel"""
        try:
            # الحصول على إعدادات السيرفر
            settings = await self.get_guild_settings(member.guild.id)
            
            if not settings['show_in_channel']:
                return
            
            # البحث عن قناة نصية مرتبطة بالـ voice channel
            text_channel = await self.find_linked_text_channel(channel)
            
            if not text_channel:
                return
            
            # تنسيق الرسالة
            ghost_message = settings['ghost_message_format'].format(
                username=member.display_name,
                user=member.mention,
                channel=channel.name
            )
            
            # إرسال الـ ghost message
            embed = discord.Embed(
                description=f"👻 {ghost_message}",
                color=0x747F8D,  # رمادي فاتح
                timestamp=datetime.now()
            )
            embed.set_author(
                name=member.display_name,
                icon_url=member.avatar.url if member.avatar else member.default_avatar.url
            )
            
            message = await text_channel.send(embed=embed)
            
            # حفظ معلومات الـ ghost
            if channel.id not in self.voice_ghosts:
                self.voice_ghosts[channel.id] = {}
            
            self.voice_ghosts[channel.id][member.id] = {
                'username': member.display_name,
                'left_at': datetime.now(),
                'message_id': message.id,
                'text_channel_id': text_channel.id
            }
            
            # حفظ في قاعدة البيانات
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO voice_presence 
                    (guild_id, channel_id, user_id, username, message_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (member.guild.id, channel.id, member.id, member.display_name, message.id))
                await db.commit()
                
        except Exception as e:
            print(f"[VOICE GHOST ERROR] {e}")
    
    async def remove_voice_ghost(self, channel, member):
        """إزالة ghost message عند دخول voice channel"""
        try:
            if channel.id in self.voice_ghosts and member.id in self.voice_ghosts[channel.id]:
                ghost_info = self.voice_ghosts[channel.id][member.id]
                
                # حذف الرسالة
                try:
                    text_channel = self.bot.get_channel(ghost_info['text_channel_id'])
                    if text_channel:
                        message = await text_channel.fetch_message(ghost_info['message_id'])
                        await message.delete()
                except:
                    pass
                
                # إزالة من الذاكرة
                del self.voice_ghosts[channel.id][member.id]
                
                # إزالة من قاعدة البيانات
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute("""
                        DELETE FROM voice_presence 
                        WHERE channel_id = ? AND user_id = ?
                    """, (channel.id, member.id))
                    await db.commit()
                    
        except Exception as e:
            print(f"[VOICE GHOST REMOVE ERROR] {e}")
    
    async def find_linked_text_channel(self, voice_channel):
        """البحث عن قناة نصية مرتبطة بالـ voice channel"""
        guild = voice_channel.guild
        
        # أولوية البحث:
        # 1. قناة بنفس اسم الـ voice channel
        # 2. قناة في نفس الـ category
        # 3. قناة general أو عامة
        # 4. أول قناة متاحة
        
        # البحث عن قناة بنفس الاسم
        voice_name = voice_channel.name.lower().replace(" ", "-")
        for channel in guild.text_channels:
            if channel.name.lower() == voice_name:
                if channel.permissions_for(guild.me).send_messages:
                    return channel
        
        # البحث في نفس الـ category
        if voice_channel.category:
            for channel in voice_channel.category.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    return channel
        
        # البحث عن قناة general
        general_names = ["general", "عام", "chat", "main", "lobby"]
        for channel in guild.text_channels:
            if any(name in channel.name.lower() for name in general_names):
                if channel.permissions_for(guild.me).send_messages:
                    return channel
        
        # أول قناة متاحة
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                return channel
        
        return None
    
    async def is_enabled(self, guild_id):
        """التحقق من تفعيل الميزة في السيرفر"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT enabled FROM voice_presence_settings WHERE guild_id = ?
            """, (guild_id,))
            result = await cursor.fetchone()
            
            if result:
                return bool(result[0])
            else:
                # إنشاء إعدادات افتراضية
                await db.execute("""
                    INSERT INTO voice_presence_settings (guild_id) VALUES (?)
                """, (guild_id,))
                await db.commit()
                return True
    
    async def get_guild_settings(self, guild_id):
        """الحصول على إعدادات السيرفر"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT enabled, duration_minutes, show_in_channel, ghost_message_format
                FROM voice_presence_settings WHERE guild_id = ?
            """, (guild_id,))
            result = await cursor.fetchone()
            
            if result:
                return {
                    'enabled': bool(result[0]),
                    'duration_minutes': result[1],
                    'show_in_channel': bool(result[2]),
                    'ghost_message_format': result[3]
                }
            else:
                # إعدادات افتراضية
                default_settings = {
                    'enabled': True,
                    'duration_minutes': 30,
                    'show_in_channel': True,
                    'ghost_message_format': '{username} was here'
                }
                
                await db.execute("""
                    INSERT INTO voice_presence_settings 
                    (guild_id, enabled, duration_minutes, show_in_channel, ghost_message_format)
                    VALUES (?, ?, ?, ?, ?)
                """, (guild_id, True, 30, True, '{username} was here'))
                await db.commit()
                
                return default_settings
    
    @tasks.loop(minutes=5)
    async def cleanup_task(self):
        """تنظيف الـ ghost messages القديمة"""
        try:
            current_time = datetime.now()
            
            for channel_id, ghosts in list(self.voice_ghosts.items()):
                for user_id, ghost_info in list(ghosts.items()):
                    # التحقق من انتهاء المدة (30 دقيقة افتراضياً)
                    time_diff = current_time - ghost_info['left_at']
                    if time_diff.total_seconds() > 1800:  # 30 دقيقة
                        # حذف الرسالة
                        try:
                            text_channel = self.bot.get_channel(ghost_info['text_channel_id'])
                            if text_channel:
                                message = await text_channel.fetch_message(ghost_info['message_id'])
                                await message.delete()
                        except:
                            pass
                        
                        # إزالة من الذاكرة
                        del self.voice_ghosts[channel_id][user_id]
                
                # إزالة القناة إذا لم تعد تحتوي على ghosts
                if not self.voice_ghosts[channel_id]:
                    del self.voice_ghosts[channel_id]
            
            # تنظيف قاعدة البيانات
            async with aiosqlite.connect(self.db_path) as db:
                cutoff_time = current_time - timedelta(minutes=30)
                await db.execute("""
                    DELETE FROM voice_presence WHERE left_at < ?
                """, (cutoff_time,))
                await db.commit()
                
        except Exception as e:
            print(f"[VOICE GHOST CLEANUP ERROR] {e}")
    
    @cleanup_task.before_loop
    async def before_cleanup_task(self):
        """انتظار جاهزية البوت قبل بدء المهمة"""
        await self.bot.wait_until_ready()
    
    # ─── Commands ──────────────────────────────────────────────────────────
    
    @commands.group(name="voiceghost", aliases=["vg", "ghost"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def voice_ghost_settings(self, ctx):
        """إعدادات ميزة Voice Ghost (User was here)"""
        embed = discord.Embed(
            title="👻 Voice Ghost Settings",
            description="**إعدادات ميزة 'User was here' في Voice Channels**",
            color=0x747F8D
        )
        embed.add_field(
            name="📋 الأوامر المتاحة",
            value=(
                "`!voiceghost status` - حالة النظام\n"
                "`!voiceghost toggle` - تشغيل/إيقاف النظام\n"
                "`!voiceghost duration <minutes>` - مدة عرض الـ ghost\n"
                "`!voiceghost format <message>` - تخصيص رسالة الـ ghost\n"
                "`!voiceghost test` - اختبار النظام"
            ),
            inline=False
        )
        embed.add_field(
            name="ℹ️ كيف يعمل النظام",
            value=(
                "• عند مغادرة أي عضو لـ Voice Channel\n"
                "• يظهر رسالة 'User was here' في القناة النصية المرتبطة\n"
                "• تختفي الرسالة عند عودة العضو أو بعد 30 دقيقة\n"
                "• يساعد الأعضاء معرفة من كان موجود مؤخراً"
            ),
            inline=False
        )
        embed.set_footer(text="صلاحية Administrator مطلوبة")
        await ctx.send(embed=embed)
    
    @voice_ghost_settings.command(name="status")
    @commands.has_permissions(administrator=True)
    async def ghost_status(self, ctx):
        """عرض حالة نظام Voice Ghost"""
        settings = await self.get_guild_settings(ctx.guild.id)
        
        embed = discord.Embed(
            title="👻 حالة نظام Voice Ghost",
            color=discord.Color.green() if settings['enabled'] else discord.Color.red()
        )
        
        embed.add_field(
            name="🔐 الحالة",
            value="✅ مفعل" if settings['enabled'] else "❌ معطل",
            inline=True
        )
        
        embed.add_field(
            name="⏰ مدة العرض",
            value=f"{settings['duration_minutes']} دقيقة",
            inline=True
        )
        
        embed.add_field(
            name="💬 تنسيق الرسالة",
            value=f"`{settings['ghost_message_format']}`",
            inline=False
        )
        
        # عرض الـ ghosts النشطة
        active_ghosts = sum(len(ghosts) for ghosts in self.voice_ghosts.values())
        embed.add_field(
            name="👻 الـ Ghosts النشطة",
            value=f"{active_ghosts} ghost message",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @voice_ghost_settings.command(name="toggle")
    @commands.has_permissions(administrator=True)
    async def ghost_toggle(self, ctx):
        """تشغيل/إيقاف نظام Voice Ghost"""
        settings = await self.get_guild_settings(ctx.guild.id)
        new_status = not settings['enabled']
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE voice_presence_settings 
                SET enabled = ? WHERE guild_id = ?
            """, (new_status, ctx.guild.id))
            await db.commit()
        
        status = "تم تشغيل" if new_status else "تم إيقاف"
        color = discord.Color.green() if new_status else discord.Color.red()
        
        embed = discord.Embed(
            title=f"👻 {status} نظام Voice Ghost",
            description=f"ميزة 'User was here' **{'مفعلة' if new_status else 'معطلة'}** الآن",
            color=color
        )
        
        await ctx.send(embed=embed)
    
    @voice_ghost_settings.command(name="format")
    @commands.has_permissions(administrator=True)
    async def ghost_format(self, ctx, *, message_format: str):
        """تخصيص تنسيق رسالة الـ ghost"""
        # التحقق من صحة التنسيق
        if '{username}' not in message_format:
            return await ctx.send("❌ يجب أن يحتوي التنسيق على `{username}`")
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE voice_presence_settings 
                SET ghost_message_format = ? WHERE guild_id = ?
            """, (message_format, ctx.guild.id))
            await db.commit()
        
        embed = discord.Embed(
            title="✅ تم تحديث تنسيق الرسالة",
            description=f"التنسيق الجديد: `{message_format}`",
            color=discord.Color.green()
        )
        embed.add_field(
            name="📝 المتغيرات المتاحة",
            value="`{username}` - اسم المستخدم\n`{user}` - منشن المستخدم\n`{channel}` - اسم الـ voice channel",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @voice_ghost_settings.command(name="duration")
    @commands.has_permissions(administrator=True)
    async def ghost_duration(self, ctx, minutes: int):
        """تحديد مدة عرض الـ ghost messages"""
        if minutes < 5 or minutes > 120:
            return await ctx.send("❌ المدة يجب أن تكون بين 5 و 120 دقيقة")
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE voice_presence_settings 
                SET duration_minutes = ? WHERE guild_id = ?
            """, (minutes, ctx.guild.id))
            await db.commit()
        
        embed = discord.Embed(
            title="✅ تم تحديث مدة العرض",
            description=f"الـ ghost messages ستظهر لمدة **{minutes} دقيقة**",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @voice_ghost_settings.command(name="test")
    @commands.has_permissions(administrator=True)
    async def ghost_test(self, ctx):
        """اختبار نظام Voice Ghost"""
        if not ctx.author.voice:
            return await ctx.send("❌ يجب أن تكون في voice channel لاختبار النظام")
        
        # محاكاة مغادرة voice channel
        await self.add_voice_ghost(ctx.author.voice.channel, ctx.author)
        
        embed = discord.Embed(
            title="✅ تم اختبار النظام",
            description="تم إنشاء ghost message تجريبية. ستختفي خلال 30 ثانية.",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
        
        # حذف الـ ghost التجريبية بعد 30 ثانية
        await asyncio.sleep(30)
        await self.remove_voice_ghost(ctx.author.voice.channel, ctx.author)

async def setup(bot):
    await bot.add_cog(VoicePresence(bot))