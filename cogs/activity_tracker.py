import discord
from discord.ext import commands
import aiosqlite
import asyncio
from datetime import datetime, timedelta
import json
import activity_config as config

class ActivityTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = config.DATABASE_PATH
        
    async def cog_load(self):
        """إعداد قاعدة البيانات عند تحميل الـ cog"""
        await self.init_db()
        print("✅ Activity Tracker loaded successfully")
    
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
                    activity_hours INTEGER DEFAULT 24
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
            description = f"كتب رسالة في #{message.channel.name}"
            if message.attachments:
                description += f" مع {len(message.attachments)} مرفق"
            
            await self.log_activity(
                message.guild.id, "message", message.author.id,
                message.author.display_name, description, message.channel.id,
                {"content_length": len(message.content), "has_attachments": bool(message.attachments)}
            )
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """تتبع انضمام الأعضاء"""
        description = f"انضم للسيرفر"
        account_age = (datetime.now() - member.created_at).days
        
        await self.log_activity(
            member.guild.id, "join", member.id, member.display_name, 
            description, None, {"account_age_days": account_age}
        )
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """تتبع مغادرة الأعضاء"""
        description = f"غادر السيرفر"
        
        await self.log_activity(
            member.guild.id, "leave", member.id, member.display_name, 
            description, None, {"roles_count": len(member.roles) - 1}
        )
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """تتبع أنشطة الصوت"""
        if member.bot:
            return
        
        # تحديث آخر نشاط
        await self.update_user_activity(member.id, member.guild.id)
        
        # تسجيل نشاط الصوت
        if before.channel != after.channel:
            if after.channel and not before.channel:
                # دخل voice channel
                description = f"دخل {after.channel.name}"
                await self.log_activity(
                    member.guild.id, "voice_join", member.id, member.display_name,
                    description, after.channel.id, {"channel_name": after.channel.name}
                )
            elif before.channel and not after.channel:
                # خرج من voice channel
                description = f"خرج من {before.channel.name}"
                await self.log_activity(
                    member.guild.id, "voice_leave", member.id, member.display_name,
                    description, before.channel.id, {"channel_name": before.channel.name}
                )
    
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
                    description = f"بدأ يلعب {activity.name}"
                    await self.log_activity(
                        after.guild.id, "game_start", after.id, after.display_name,
                        description, None, {"game_name": activity.name}
                    )
    
    # ─── Commands ──────────────────────────────────────────────────────────
    
    @commands.command(name="missed", aliases=["فاتني", "whatimissed"])
    async def what_you_missed(self, ctx, hours: int = 24):
        """عرض الأنشطة التي فاتتك"""
        if hours > 168:  # أسبوع كحد أقصى
            hours = 168
        
        activities, since_time = await self.get_missed_activities(ctx.author.id, ctx.guild.id, hours)
        
        # استيراد الواجهة التفاعلية
        from cogs.missed_view import MissedActivitiesView
        
        # إنشاء الواجهة التفاعلية
        view = MissedActivitiesView(ctx.author.id, ctx.guild.id, activities, since_time)
        embed = view.get_summary_embed()
        
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name="recent", aliases=["حديث", "اخر-نشاط"])
    async def recent_activities(self, ctx, limit: int = 10):
        """عرض آخر الأنشطة بشكل سريع"""
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
                title="📭 لا توجد أنشطة حديثة",
                description="لم يتم تسجيل أي أنشطة مؤخراً",
                color=discord.Color.blue()
            )
            return await ctx.send(embed=embed)
        
        embed = discord.Embed(
            title="🕐 آخر الأنشطة",
            description=f"آخر {len(activities)} نشاط في السيرفر",
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
        embed.set_footer(text=f"استخدم !missed للمزيد من التفاصيل")
        
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
        
        embed = discord.Embed(
            title="📊 إحصائيات نظام الأنشطة",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📈 الإحصائيات العامة",
            value=f"إجمالي الأنشطة: **{total_activities}**\nالمستخدمين النشطين: **{active_users}**",
            inline=False
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