import discord
from discord.ext import commands, tasks
import aiosqlite
import asyncio
from datetime import datetime, timedelta
import json
import activity_config as config

class ActivityTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = config.DATABASE_PATH
        self.voice_notifications = {}  # {user_id: {guild_id: last_notification_time}}
        self.auto_notification_task.start()  # بدء المهمة التلقائية
        
    async def cog_load(self):
        """إعداد قاعدة البيانات عند تحميل الـ cog"""
        await self.init_db()
        print("✅ Activity Tracker loaded successfully")
    
    def cog_unload(self):
        """إيقاف المهام عند إلغاء تحميل الـ cog"""
        self.auto_notification_task.cancel()
    
    async def init_db(self):
        """إنشاء جداول قاعدة البيانات"""
        async with aiosqlite.connect(self.db_path) as db:
            # جدول تتبع آخر نشاط للأعضاء
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_activity (
                    user_id INTEGER,
                    guild_id INTEGER,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, guild_id)
                )
            """)
            
            # جدول الأنشطة المهمة
            await db.execute("""
                CREATE TABLE IF NOT EXISTS missed_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    activity_type TEXT,
                    user_id INTEGER,
                    username TEXT,
                    description TEXT,
                    channel_id INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    data TEXT
                )
            """)
            
            # جدول إعدادات التتبع لكل سيرفر
            await db.execute("""
                CREATE TABLE IF NOT EXISTS activity_settings (
                    guild_id INTEGER PRIMARY KEY,
                    enabled BOOLEAN DEFAULT 1,
                    track_joins BOOLEAN DEFAULT 1,
                    track_leaves BOOLEAN DEFAULT 1,
                    track_messages BOOLEAN DEFAULT 1,
                    track_voice BOOLEAN DEFAULT 1,
                    track_games BOOLEAN DEFAULT 1,
                    max_activities INTEGER DEFAULT 50,
                    activity_hours INTEGER DEFAULT 24,
                    auto_notifications BOOLEAN DEFAULT 1,
                    notification_cooldown INTEGER DEFAULT 30,
                    min_activities_for_notification INTEGER DEFAULT 3
                )
            """)
            
            await db.commit()
    
    async def update_user_activity(self, user_id: int, guild_id: int):
        """تحديث آخر نشاط للمستخدم"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO user_activity (user_id, guild_id, last_seen)
                VALUES (?, ?, ?)
            """, (user_id, guild_id, datetime.now()))
            await db.commit()
    
    async def log_activity(self, guild_id: int, activity_type: str, user_id: int, 
                          username: str, description: str, channel_id: int = None, data: dict = None):
        """تسجيل نشاط جديد"""
        async with aiosqlite.connect(self.db_path) as db:
            data_json = json.dumps(data) if data else None
            await db.execute("""
                INSERT INTO missed_activities 
                (guild_id, activity_type, user_id, username, description, channel_id, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (guild_id, activity_type, user_id, username, description, channel_id, data_json))
            await db.commit()
    
    async def get_missed_activities(self, user_id: int, guild_id: int, hours: int = 24):
        """الحصول على الأنشطة المفقودة للمستخدم"""
        async with aiosqlite.connect(self.db_path) as db:
            # الحصول على آخر نشاط للمستخدم
            cursor = await db.execute("""
                SELECT last_seen FROM user_activity 
                WHERE user_id = ? AND guild_id = ?
            """, (user_id, guild_id))
            result = await cursor.fetchone()
            
            if not result:
                # إذا لم يكن هناك سجل، استخدم آخر 24 ساعة
                since_time = datetime.now() - timedelta(hours=hours)
            else:
                since_time = datetime.fromisoformat(result[0])
            
            # الحصول على الأنشطة منذ آخر نشاط
            cursor = await db.execute("""
                SELECT activity_type, user_id, username, description, channel_id, timestamp, data
                FROM missed_activities 
                WHERE guild_id = ? AND timestamp > ? AND user_id != ?
                ORDER BY timestamp DESC
                LIMIT 50
            """, (guild_id, since_time, user_id))
            
            activities = await cursor.fetchall()
            return activities, since_time
    
    async def cleanup_old_activities(self, guild_id: int, hours: int = 168):  # أسبوع افتراضي
        """تنظيف الأنشطة القديمة"""
        async with aiosqlite.connect(self.db_path) as db:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            await db.execute("""
                DELETE FROM missed_activities 
                WHERE guild_id = ? AND timestamp < ?
            """, (guild_id, cutoff_time))
            await db.commit()
    
    # ─── Event Listeners ───────────────────────────────────────────────────
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """تتبع الرسائل"""
        if message.author.bot or not message.guild:
            return
        
        # تحديث آخر نشاط للمستخدم
        await self.update_user_activity(message.author.id, message.guild.id)
        
        # تسجيل الرسالة كنشاط (للرسائل المهمة فقط)
        if len(message.content) > 50 or message.attachments:
            description = f"sent a message in #{message.channel.name}"
            if message.attachments:
                description += f" with {len(message.attachments)} attachment(s)"
            
            await self.log_activity(
                message.guild.id, "message", message.author.id,
                message.author.display_name, description, message.channel.id,
                {"content_length": len(message.content), "has_attachments": bool(message.attachments)}
            )
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """تتبع انضمام الأعضاء"""
        description = f"joined the server"
        account_age = (datetime.now() - member.created_at).days
        
        await self.log_activity(
            member.guild.id, "join", member.id, member.display_name, 
            description, None, {"account_age_days": account_age}
        )
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """تتبع مغادرة الأعضاء"""
        description = f"left the server"
        
        await self.log_activity(
            member.guild.id, "leave", member.id, member.display_name, 
            description, None, {"roles_count": len(member.roles) - 1}
        )
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """تتبع أنشطة الصوت وإرسال إشعارات تلقائية"""
        if member.bot:
            return
        
        # تحديث آخر نشاط
        await self.update_user_activity(member.id, member.guild.id)
        
        # تسجيل نشاط الصوت
        if before.channel != after.channel:
            if after.channel and not before.channel:
                # دخل voice channel - تسجيل النشاط
                description = f"joined {after.channel.name}"
                await self.log_activity(
                    member.guild.id, "voice_join", member.id, member.display_name,
                    description, after.channel.id, {"channel_name": after.channel.name}
                )
                
                # إرسال What You Missed تلقائياً عند دخول Voice Channel
                await self.send_auto_what_you_missed(member, after.channel)
                
            elif before.channel and not after.channel:
                # خرج من voice channel
                description = f"left {before.channel.name}"
                await self.log_activity(
                    member.guild.id, "voice_leave", member.id, member.display_name,
                    description, before.channel.id, {"channel_name": before.channel.name}
                )
            elif before.channel and after.channel and before.channel != after.channel:
                # انتقل بين voice channels
                description = f"moved to {after.channel.name}"
                await self.log_activity(
                    member.guild.id, "voice_join", member.id, member.display_name,
                    description, after.channel.id, {"channel_name": after.channel.name}
                )
    
    async def send_auto_what_you_missed(self, member, voice_channel):
        """إرسال What You Missed تلقائياً عند دخول Voice Channel"""
        try:
            # التحقق من عدم إرسال إشعار مؤخراً (كل 30 دقيقة كحد أقصى)
            now = datetime.now()
            user_notifications = self.voice_notifications.get(member.id, {})
            last_notification = user_notifications.get(member.guild.id)
            
            if last_notification and (now - last_notification).total_seconds() < 1800:  # 30 دقيقة
                return
            
            # الحصول على الأنشطة المفقودة
            activities, since_time = await self.get_missed_activities(member.id, member.guild.id, 24)
            
            if len(activities) < 3:  # لا ترسل إشعار إذا كان أقل من 3 أنشطة
                return
            
            # إنشاء embed مبسط للإشعار التلقائي
            embed = await self.create_auto_notification_embed(member, activities, since_time, voice_channel)
            
            # البحث عن قناة نصية مناسبة للإرسال
            text_channel = await self.find_suitable_text_channel(member.guild, voice_channel)
            
            if text_channel:
                # إرسال الإشعار
                message = await text_channel.send(f"👋 {member.mention}", embed=embed)
                
                # حذف الرسالة بعد 60 ثانية لعدم الإزعاج
                await asyncio.sleep(60)
                try:
                    await message.delete()
                except:
                    pass
                
                # تسجيل وقت الإشعار
                if member.id not in self.voice_notifications:
                    self.voice_notifications[member.id] = {}
                self.voice_notifications[member.id][member.guild.id] = now
                
        except Exception as e:
            print(f"[AUTO NOTIFICATION ERROR] {e}")
    
    async def create_auto_notification_embed(self, member, activities, since_time, voice_channel):
        """إنشاء embed للإشعار التلقائي بنفس شكل الصورة"""
        # تجميع الأنشطة
        activity_groups = {
            "join": [],
            "leave": [],
            "message": [],
            "voice_join": [],
            "voice_leave": [],
            "game_start": []
        }
        
        for activity in activities:
            activity_type = activity[0]
            if activity_type in activity_groups:
                activity_groups[activity_type].append(activity)
        
        embed = discord.Embed(
            title="What You Missed",
            color=0x36393F  # لون رمادي داكن مثل Discord
        )
        
        # عرض الأنشطة بنفس تنسيق الصورة
        activity_text = ""
        
        # ترتيب الأنشطة حسب الوقت (الأحدث أولاً)
        sorted_activities = sorted(activities, key=lambda x: x[5], reverse=True)
        
        for activity in sorted_activities[:10]:  # أول 10 أنشطة
            activity_type, user_id, username, description, channel_id, timestamp, data = activity
            activity_time = datetime.fromisoformat(timestamp)
            
            # حساب الوقت المنقضي
            time_diff = datetime.now() - activity_time
            
            if time_diff.days > 0:
                time_str = f"{time_diff.days}d ago"
            elif time_diff.seconds > 3600:
                hours = time_diff.seconds // 3600
                time_str = f"{hours}h ago"
            elif time_diff.seconds > 60:
                minutes = time_diff.seconds // 60
                time_str = f"{minutes}m ago"
            else:
                time_str = "now"
            
            # تحديد النص حسب نوع النشاط
            if activity_type == "voice_join":
                activity_text += f"🟢 **{username}** was here\n{time_str}\n\n"
            elif activity_type == "voice_leave":
                activity_text += f"🔴 **{username}** left voice\n{time_str}\n\n"
            elif activity_type == "join":
                activity_text += f"👋 **{username}** joined server\n{time_str}\n\n"
            elif activity_type == "leave":
                activity_text += f"👋 **{username}** left server\n{time_str}\n\n"
            elif activity_type == "message":
                activity_text += f"💬 **{username}** sent message\n{time_str}\n\n"
            elif activity_type == "game_start":
                activity_text += f"🎮 **{username}** started playing\n{time_str}\n\n"
        
        if activity_text:
            embed.description = activity_text
        else:
            embed.description = "No recent activities"
        
        embed.set_footer(
            text=f"Welcome to {voice_channel.name} • Auto-delete in 60s",
            icon_url=member.avatar.url if member.avatar else None
        )
        
        return embed
    
    async def find_suitable_text_channel(self, guild, voice_channel):
        """البحث عن قناة نصية مناسبة للإرسال"""
        # أولوية البحث:
        # 1. قناة بنفس اسم الـ voice channel
        # 2. قناة general أو عامة
        # 3. أول قناة يمكن الكتابة فيها
        
        # البحث عن قناة بنفس الاسم
        voice_name = voice_channel.name.lower().replace(" ", "-")
        for channel in guild.text_channels:
            if channel.name.lower() == voice_name:
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
    
    @tasks.loop(minutes=30)
    async def auto_notification_task(self):
        """مهمة تلقائية لإرسال إشعارات دورية للأعضاء في Voice Channels"""
        try:
            for guild in self.bot.guilds:
                # البحث عن الأعضاء في Voice Channels
                for voice_channel in guild.voice_channels:
                    for member in voice_channel.members:
                        if member.bot:
                            continue
                        
                        # التحقق من وجود أنشطة مفقودة
                        activities, since_time = await self.get_missed_activities(member.id, guild.id, 6)  # آخر 6 ساعات
                        
                        if len(activities) >= 5:  # إذا كان هناك 5 أنشطة أو أكثر
                            # التحقق من عدم إرسال إشعار مؤخراً
                            now = datetime.now()
                            user_notifications = self.voice_notifications.get(member.id, {})
                            last_notification = user_notifications.get(guild.id)
                            
                            if not last_notification or (now - last_notification).total_seconds() > 3600:  # ساعة
                                await self.send_periodic_notification(member, voice_channel, activities, since_time)
        
        except Exception as e:
            print(f"[AUTO NOTIFICATION TASK ERROR] {e}")
    
    @auto_notification_task.before_loop
    async def before_auto_notification_task(self):
        """انتظار جاهزية البوت قبل بدء المهمة"""
        await self.bot.wait_until_ready()
    
    async def send_periodic_notification(self, member, voice_channel, activities, since_time):
        """إرسال إشعار دوري للأعضاء النشطين في Voice"""
        try:
            embed = discord.Embed(
                title="🔔 تحديث الأنشطة",
                description=f"**{member.display_name}**، هناك أنشطة جديدة في السيرفر!",
                color=0x00D4AA
            )
            
            embed.add_field(
                name="📊 الإحصائيات",
                value=f"🔥 **{len(activities)}** نشاط جديد منذ {since_time.strftime('%H:%M')}",
                inline=False
            )
            
            embed.add_field(
                name="💡 نصيحة",
                value="استخدم `!missed` لرؤية جميع التفاصيل",
                inline=False
            )
            
            embed.set_footer(text="إشعار تلقائي • سيتم حذفه خلال 30 ثانية")
            
            text_channel = await self.find_suitable_text_channel(member.guild, voice_channel)
            if text_channel:
                message = await text_channel.send(f"{member.mention}", embed=embed)
                
                # حذف بعد 30 ثانية
                await asyncio.sleep(30)
                try:
                    await message.delete()
                except:
                    pass
                
                # تسجيل وقت الإشعار
                if member.id not in self.voice_notifications:
                    self.voice_notifications[member.id] = {}
                self.voice_notifications[member.id][member.guild.id] = datetime.now()
        
        except Exception as e:
            print(f"[PERIODIC NOTIFICATION ERROR] {e}")
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """تتبع تحديثات الأعضاء (الألعاب، الحالة، إلخ)"""
        if before.bot:
            return
        
        # تحديث آخر نشاط
        await self.update_user_activity(after.id, after.guild.id)
        
        # تتبع تغيير الألعاب/الأنشطة
        if before.activities != after.activities:
            new_activities = [a for a in after.activities if a not in before.activities]
            for activity in new_activities:
                if activity.type == discord.ActivityType.playing:
                    description = f"started playing {activity.name}"
                    await self.log_activity(
                        after.guild.id, "game_start", after.id, after.display_name,
                        description, None, {"game_name": activity.name}
                    )
    
    # ─── Commands ──────────────────────────────────────────────────────────
    
    @commands.command(name="missed", aliases=["whatimissed", "wym"])
    async def what_you_missed(self, ctx, hours: int = 24):
        """Show activities you missed while away"""
        if hours > 168:  # أسبوع كحد أقصى
            hours = 168
        
        activities, since_time = await self.get_missed_activities(ctx.author.id, ctx.guild.id, hours)
        
        # استيراد الواجهة التفاعلية
        from cogs.missed_view import MissedActivitiesView
        
        # إنشاء الواجهة التفاعلية
        view = MissedActivitiesView(ctx.author.id, ctx.guild.id, activities, since_time)
        embed = view.get_summary_embed()
        
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name="recent", aliases=["latest"])
    async def recent_activities(self, ctx, limit: int = 10):
        """Show recent server activities quickly"""
        if limit > 20:
            limit = 20
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT activity_type, user_id, username, description, timestamp
                FROM missed_activities 
                WHERE guild_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (ctx.guild.id, limit))
            
            activities = await cursor.fetchall()
        
        if not activities:
            embed = discord.Embed(
                title="📭 No Recent Activities",
                description="No activities have been recorded recently",
                color=discord.Color.blue()
            )
            return await ctx.send(embed=embed)
        
        embed = discord.Embed(
            title="🕐 Recent Activities",
            description=f"Last {len(activities)} activities in the server",
            color=0x00D4AA
        )
        
        # أيقونات الأنشطة
        icons = {
            "join": "👋",
            "leave": "👋",
            "message": "💬",
            "voice_join": "🔊",
            "voice_leave": "🔇",
            "game_start": "🎮"
        }
        
        activity_text = ""
        for activity in activities:
            activity_type, user_id, username, description, timestamp = activity
            activity_time = datetime.fromisoformat(timestamp)
            time_str = activity_time.strftime('%H:%M')
            icon = icons.get(activity_type, "📝")
            
            activity_text += f"{icon} **{username}** {description} - `{time_str}`\n"
        
        embed.description += f"\n\n{activity_text}"
        embed.set_footer(text=f"Use !missed for more details")
        
        await ctx.send(embed=embed)
    
    @commands.group(name="activity", aliases=["نشاط"], invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def activity_settings(self, ctx):
        """إعدادات تتبع الأنشطة"""
        embed = discord.Embed(
            title="📊 Activity Tracker Settings",
            description="إعدادات نظام تتبع الأنشطة",
            color=0x2B2D31
        )
        embed.add_field(
            name="📋 الأوامر المتاحة",
            value=(
                "`!activity status` - حالة النظام\n"
                "`!activity toggle` - تشغيل/إيقاف النظام\n"
                "`!activity cleanup` - تنظيف الأنشطة القديمة\n"
                "`!activity stats` - إحصائيات النظام"
            ),
            inline=False
        )
        embed.set_footer(text="صلاحية Administrator مطلوبة")
        await ctx.send(embed=embed)
    
    @activity_settings.command(name="status")
    @commands.has_permissions(administrator=True)
    async def activity_status(self, ctx):
        """عرض حالة نظام تتبع الأنشطة"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM activity_settings WHERE guild_id = ?
            """, (ctx.guild.id,))
            settings = await cursor.fetchone()
            
            if not settings:
                # إنشاء إعدادات افتراضية
                await db.execute("""
                    INSERT INTO activity_settings (guild_id) VALUES (?)
                """, (ctx.guild.id,))
                await db.commit()
                settings = (ctx.guild.id, 1, 1, 1, 1, 1, 1, 50, 24)
        
        embed = discord.Embed(
            title="📊 حالة نظام تتبع الأنشطة",
            color=discord.Color.green() if settings[1] else discord.Color.red()
        )
        
        embed.add_field(
            name="🔐 الحالة العامة",
            value="✅ مفعل" if settings[1] else "❌ معطل",
            inline=True
        )
        
        embed.add_field(
            name="📋 الأنشطة المتتبعة",
            value=(
                f"👋 الانضمام/المغادرة: {'✅' if settings[2] and settings[3] else '❌'}\n"
                f"💬 الرسائل: {'✅' if settings[4] else '❌'}\n"
                f"🔊 الصوت: {'✅' if settings[5] else '❌'}\n"
                f"🎮 الألعاب: {'✅' if settings[6] else '❌'}"
            ),
            inline=True
        )
        
        embed.add_field(
            name="⚙️ الإعدادات",
            value=f"حد الأنشطة: {settings[7]}\nفترة التتبع: {settings[8]} ساعة",
            inline=True
        )
        
        await ctx.send(embed=embed)
    
    @activity_settings.command(name="cleanup")
    @commands.has_permissions(administrator=True)
    async def activity_cleanup(self, ctx, hours: int = 168):
        """تنظيف الأنشطة القديمة"""
        if hours < 24:
            return await ctx.send("❌ لا يمكن حذف أنشطة أقل من 24 ساعة")
        
        await self.cleanup_old_activities(ctx.guild.id, hours)
        
        embed = discord.Embed(
            title="🧹 تم تنظيف الأنشطة",
            description=f"تم حذف الأنشطة الأقدم من {hours} ساعة",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @activity_settings.command(name="notifications")
    @commands.has_permissions(administrator=True)
    async def activity_notifications(self, ctx, action: str = None):
        """تشغيل/إيقاف الإشعارات التلقائية"""
        if action not in ["on", "off", "status"]:
            embed = discord.Embed(
                title="⚙️ إعدادات الإشعارات التلقائية",
                description="إدارة الإشعارات التلقائية في Voice Channels",
                color=0x2B2D31
            )
            embed.add_field(
                name="📋 الأوامر المتاحة",
                value=(
                    "`!activity notifications on` - تشغيل الإشعارات\n"
                    "`!activity notifications off` - إيقاف الإشعارات\n"
                    "`!activity notifications status` - حالة الإشعارات"
                ),
                inline=False
            )
            embed.add_field(
                name="ℹ️ كيف تعمل الإشعارات",
                value=(
                    "• تُرسل تلقائياً عند دخول Voice Channel\n"
                    "• تُظهر الأنشطة المفقودة منذ آخر زيارة\n"
                    "• تُحذف تلقائياً بعد دقيقة واحدة\n"
                    "• cooldown 30 دقيقة بين كل إشعار"
                ),
                inline=False
            )
            return await ctx.send(embed=embed)
        
        async with aiosqlite.connect(self.db_path) as db:
            if action == "status":
                cursor = await db.execute("""
                    SELECT auto_notifications, notification_cooldown, min_activities_for_notification 
                    FROM activity_settings WHERE guild_id = ?
                """, (ctx.guild.id,))
                settings = await cursor.fetchone()
                
                if not settings:
                    settings = (1, 30, 3)  # القيم الافتراضية
                
                embed = discord.Embed(
                    title="📊 حالة الإشعارات التلقائية",
                    color=discord.Color.green() if settings[0] else discord.Color.red()
                )
                embed.add_field(
                    name="🔐 الحالة",
                    value="✅ مفعلة" if settings[0] else "❌ معطلة",
                    inline=True
                )
                embed.add_field(
                    name="⏰ Cooldown",
                    value=f"{settings[1]} دقيقة",
                    inline=True
                )
                embed.add_field(
                    name="📊 الحد الأدنى للأنشطة",
                    value=f"{settings[2]} أنشطة",
                    inline=True
                )
                
                return await ctx.send(embed=embed)
            
            elif action in ["on", "off"]:
                enabled = action == "on"
                
                # تحديث الإعدادات
                await db.execute("""
                    INSERT OR REPLACE INTO activity_settings 
                    (guild_id, auto_notifications) VALUES (?, ?)
                    ON CONFLICT(guild_id) DO UPDATE SET auto_notifications = ?
                """, (ctx.guild.id, enabled, enabled))
                await db.commit()
                
                status = "تم تشغيل" if enabled else "تم إيقاف"
                color = discord.Color.green() if enabled else discord.Color.red()
                
                embed = discord.Embed(
                    title=f"🔔 {status} الإشعارات التلقائية",
                    description=f"الإشعارات التلقائية **{'مفعلة' if enabled else 'معطلة'}** الآن",
                    color=color
                )
                
                if enabled:
                    embed.add_field(
                        name="✅ تم التفعيل",
                        value="سيتم إرسال إشعارات تلقائية عند دخول Voice Channels",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="❌ تم الإيقاف", 
                        value="لن يتم إرسال إشعارات تلقائية",
                        inline=False
                    )
                
                await ctx.send(embed=embed)
    
    @activity_settings.command(name="stats")
    @commands.has_permissions(administrator=True)
    async def activity_stats(self, ctx):
        """إحصائيات نظام الأنشطة"""
        async with aiosqlite.connect(self.db_path) as db:
            # إجمالي الأنشطة
            cursor = await db.execute("""
                SELECT COUNT(*) FROM missed_activities WHERE guild_id = ?
            """, (ctx.guild.id,))
            total_activities = (await cursor.fetchone())[0]
            
            # الأنشطة حسب النوع
            cursor = await db.execute("""
                SELECT activity_type, COUNT(*) FROM missed_activities 
                WHERE guild_id = ? GROUP BY activity_type
            """, (ctx.guild.id,))
            activity_types = await cursor.fetchall()
            
            # المستخدمين النشطين
            cursor = await db.execute("""
                SELECT COUNT(DISTINCT user_id) FROM user_activity WHERE guild_id = ?
            """, (ctx.guild.id,))
            active_users = (await cursor.fetchone())[0]
            
            # إحصائيات الإشعارات
            cursor = await db.execute("""
                SELECT auto_notifications FROM activity_settings WHERE guild_id = ?
            """, (ctx.guild.id,))
            notifications_enabled = await cursor.fetchone()
            notifications_status = notifications_enabled[0] if notifications_enabled else 1
        
        embed = discord.Embed(
            title="📊 إحصائيات نظام الأنشطة",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📈 الإحصائيات العامة",
            value=f"إجمالي الأنشطة: **{total_activities}**\nالمستخدمين النشطين: **{active_users}**",
            inline=False
        )
        
        embed.add_field(
            name="🔔 حالة الإشعارات",
            value="✅ مفعلة" if notifications_status else "❌ معطلة",
            inline=True
        )
        
        if activity_types:
            type_text = "\n".join([
                f"• {activity_type}: {count}" 
                for activity_type, count in activity_types
            ])
            embed.add_field(
                name="📋 الأنشطة حسب النوع",
                value=type_text,
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ActivityTracker(bot))