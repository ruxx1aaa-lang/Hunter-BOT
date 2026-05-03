import discord
from discord.ext import commands
import aiosqlite
from datetime import datetime, timezone
import json

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_welcome_settings(self, guild_id: int) -> dict:
        """جيب إعدادات الترحيب للسيرفر"""
        async with aiosqlite.connect("hunter.db") as db:
            cursor = await db.execute("""
                SELECT welcome_enabled, welcome_channel_id, welcome_message, welcome_image_url, 
                       welcome_embed_color, welcome_title, welcome_description
                FROM welcome_settings WHERE guild_id = ?
            """, (guild_id,))
            result = await cursor.fetchone()
            
            if result:
                return {
                    'enabled': bool(result[0]),
                    'channel_id': result[1],
                    'message': result[2],
                    'image_url': result[3],
                    'embed_color': result[4] or 0x2B2D31,
                    'title': result[5],
                    'description': result[6]
                }
            else:
                # الإعدادات الافتراضية
                return {
                    'enabled': False,
                    'channel_id': None,
                    'message': None,
                    'image_url': None,
                    'embed_color': 0x2B2D31,
                    'title': None,
                    'description': None
                }

    async def save_welcome_settings(self, guild_id: int, settings: dict):
        """حفظ إعدادات الترحيب"""
        async with aiosqlite.connect("hunter.db") as db:
            await db.execute("""
                INSERT OR REPLACE INTO welcome_settings 
                (guild_id, welcome_enabled, welcome_channel_id, welcome_message, 
                 welcome_image_url, welcome_embed_color, welcome_title, welcome_description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                guild_id,
                settings.get('enabled', False),
                settings.get('channel_id'),
                settings.get('message'),
                settings.get('image_url'),
                settings.get('embed_color', 0x2B2D31),
                settings.get('title'),
                settings.get('description')
            ))
            await db.commit()

    def create_welcome_embed(self, member: discord.Member, settings: dict) -> discord.Embed:
        """إنشاء embed الترحيب"""
        # استبدال المتغيرات في النصوص
        replacements = {
            '{user}': member.display_name,
            '{mention}': member.mention,
            '{server}': member.guild.name,
            '{member_count}': str(member.guild.member_count),
            '{user_id}': str(member.id),
            '{server_id}': str(member.guild.id)
        }
        
        # العنوان الافتراضي
        title = settings.get('title') or f"Hello {member.display_name} ❤️ You Are Welcome To"
        for old, new in replacements.items():
            title = title.replace(old, new)
        
        # الوصف الافتراضي
        description = settings.get('description') or f"**{member.guild.name}'s server!**"
        for old, new in replacements.items():
            description = description.replace(old, new)
        
        # إنشاء الـ embed
        embed = discord.Embed(
            title=title,
            description=description,
            color=settings.get('embed_color', 0x2B2D31),
            timestamp=datetime.now(timezone.utc)
        )
        
        # إضافة صورة العضو
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # إضافة الصورة المخصصة إذا كانت موجودة
        if settings.get('image_url'):
            embed.set_image(url=settings['image_url'])
        
        # إضافة معلومات إضافية
        embed.add_field(
            name="👤 Member Info",
            value=f"**Name:** {member.display_name}\n**ID:** {member.id}\n**Joined:** <t:{int(member.joined_at.timestamp())}:R>",
            inline=True
        )
        
        embed.add_field(
            name="🏠 Server Info", 
            value=f"**Members:** {member.guild.member_count}\n**Created:** <t:{int(member.guild.created_at.timestamp())}:D>",
            inline=True
        )
        
        # Footer
        embed.set_footer(
            text=f"Welcome to {member.guild.name} • Werjo Bot",
            icon_url=member.guild.icon.url if member.guild.icon else None
        )
        
        return embed

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """عند انضمام عضو جديد"""
        if member.bot:
            return
            
        settings = await self.get_welcome_settings(member.guild.id)
        
        if not settings['enabled'] or not settings['channel_id']:
            return
            
        channel = member.guild.get_channel(settings['channel_id'])
        if not channel:
            return
            
        try:
            # إرسال رسالة نصية إضافية إذا كانت موجودة
            if settings.get('message'):
                message = settings['message']
                replacements = {
                    '{user}': member.display_name,
                    '{mention}': member.mention,
                    '{server}': member.guild.name,
                    '{member_count}': str(member.guild.member_count)
                }
                for old, new in replacements.items():
                    message = message.replace(old, new)
                await channel.send(message)
            
            # إرسال الـ embed
            embed = self.create_welcome_embed(member, settings)
            await channel.send(embed=embed)
            
        except discord.Forbidden:
            pass
        except Exception as e:
            print(f"[Welcome] Error sending welcome message: {e}")

    @commands.group(name="welcome", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx):
        """إدارة نظام الترحيب"""
        embed = discord.Embed(
            title="👋 Welcome System",
            description="**نظام ترحيب متطور وقابل للتخصيص**",
            color=0x5865F2
        )
        embed.add_field(
            name="📋 الأوامر الأساسية",
            value=(
                "`!welcome setup #channel` - إعداد قناة الترحيب\n"
                "`!welcome toggle` - تشغيل/إيقاف النظام\n"
                "`!welcome status` - حالة النظام\n"
                "`!welcome test` - اختبار الرسالة"
            ),
            inline=False
        )
        embed.add_field(
            name="🎨 التخصيص",
            value=(
                "`!welcome title <text>` - تغيير العنوان\n"
                "`!welcome description <text>` - تغيير الوصف\n"
                "`!welcome message <text>` - رسالة إضافية\n"
                "`!welcome image <url>` - صورة مخصصة\n"
                "`!welcome color <hex>` - لون الـ embed"
            ),
            inline=False
        )
        embed.add_field(
            name="🔧 المتغيرات المتاحة",
            value=(
                "`{user}` - اسم العضو\n"
                "`{mention}` - منشن العضو\n"
                "`{server}` - اسم السيرفر\n"
                "`{member_count}` - عدد الأعضاء"
            ),
            inline=False
        )
        embed.set_footer(text="صلاحية Administrator مطلوبة")
        await ctx.send(embed=embed)

    @welcome.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def welcome_setup(self, ctx, channel: discord.TextChannel):
        """إعداد قناة الترحيب"""
        settings = await self.get_welcome_settings(ctx.guild.id)
        settings['enabled'] = True
        settings['channel_id'] = channel.id
        
        # إعداد افتراضي جميل
        if not settings.get('title'):
            settings['title'] = "Hello {user} ❤️ You Are Welcome To"
        if not settings.get('description'):
            settings['description'] = "**{server}'s server!**"
        
        await self.save_welcome_settings(ctx.guild.id, settings)
        
        embed = discord.Embed(
            title="✅ تم إعداد نظام الترحيب",
            description=f"قناة الترحيب: {channel.mention}",
            color=discord.Color.green()
        )
        embed.add_field(
            name="💡 نصيحة",
            value="استخدم `!welcome test` لمعاينة الرسالة",
            inline=False
        )
        await ctx.send(embed=embed)

    @welcome.command(name="toggle")
    @commands.has_permissions(administrator=True)
    async def welcome_toggle(self, ctx):
        """تشغيل/إيقاف نظام الترحيب"""
        settings = await self.get_welcome_settings(ctx.guild.id)
        settings['enabled'] = not settings.get('enabled', False)
        await self.save_welcome_settings(ctx.guild.id, settings)
        
        status = "تم تشغيل" if settings['enabled'] else "تم إيقاف"
        color = discord.Color.green() if settings['enabled'] else discord.Color.red()
        
        embed = discord.Embed(
            title=f"👋 {status} نظام الترحيب",
            description=f"نظام الترحيب **{'مفعل' if settings['enabled'] else 'معطل'}** الآن",
            color=color
        )
        await ctx.send(embed=embed)

    @welcome.command(name="status")
    @commands.has_permissions(administrator=True)
    async def welcome_status(self, ctx):
        """عرض حالة نظام الترحيب"""
        settings = await self.get_welcome_settings(ctx.guild.id)
        
        embed = discord.Embed(
            title="👋 حالة نظام الترحيب",
            color=discord.Color.green() if settings['enabled'] else discord.Color.red()
        )
        
        # الحالة الأساسية
        embed.add_field(
            name="🔐 الحالة",
            value="✅ مفعل" if settings['enabled'] else "❌ معطل",
            inline=True
        )
        
        # القناة
        channel = ctx.guild.get_channel(settings['channel_id']) if settings['channel_id'] else None
        embed.add_field(
            name="📢 القناة",
            value=channel.mention if channel else "❌ غير محددة",
            inline=True
        )
        
        # الإعدادات
        embed.add_field(name="🎨 العنوان", value=settings.get('title') or "افتراضي", inline=False)
        embed.add_field(name="📝 الوصف", value=settings.get('description') or "افتراضي", inline=False)
        
        if settings.get('message'):
            embed.add_field(name="💬 رسالة إضافية", value=settings['message'][:100] + "..." if len(settings['message']) > 100 else settings['message'], inline=False)
        
        if settings.get('image_url'):
            embed.add_field(name="🖼️ صورة مخصصة", value="✅ محددة", inline=True)
        
        await ctx.send(embed=embed)

    @welcome.command(name="title")
    @commands.has_permissions(administrator=True)
    async def welcome_title(self, ctx, *, title: str):
        """تغيير عنوان الترحيب"""
        settings = await self.get_welcome_settings(ctx.guild.id)
        settings['title'] = title
        await self.save_welcome_settings(ctx.guild.id, settings)
        
        embed = discord.Embed(
            title="✅ تم تحديث العنوان",
            description=f"العنوان الجديد: **{title}**",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @welcome.command(name="description")
    @commands.has_permissions(administrator=True)
    async def welcome_description(self, ctx, *, description: str):
        """تغيير وصف الترحيب"""
        settings = await self.get_welcome_settings(ctx.guild.id)
        settings['description'] = description
        await self.save_welcome_settings(ctx.guild.id, settings)
        
        embed = discord.Embed(
            title="✅ تم تحديث الوصف",
            description=f"الوصف الجديد: **{description}**",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @welcome.command(name="message")
    @commands.has_permissions(administrator=True)
    async def welcome_message(self, ctx, *, message: str = None):
        """تغيير الرسالة الإضافية"""
        settings = await self.get_welcome_settings(ctx.guild.id)
        settings['message'] = message
        await self.save_welcome_settings(ctx.guild.id, settings)
        
        if message:
            embed = discord.Embed(
                title="✅ تم تحديث الرسالة الإضافية",
                description=f"الرسالة: **{message}**",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="✅ تم حذف الرسالة الإضافية",
                color=discord.Color.green()
            )
        await ctx.send(embed=embed)

    @welcome.command(name="image")
    @commands.has_permissions(administrator=True)
    async def welcome_image(self, ctx, url: str = None):
        """تغيير صورة الترحيب"""
        settings = await self.get_welcome_settings(ctx.guild.id)
        settings['image_url'] = url
        await self.save_welcome_settings(ctx.guild.id, settings)
        
        if url:
            embed = discord.Embed(
                title="✅ تم تحديث صورة الترحيب",
                color=discord.Color.green()
            )
            embed.set_image(url=url)
        else:
            embed = discord.Embed(
                title="✅ تم حذف صورة الترحيب",
                color=discord.Color.green()
            )
        await ctx.send(embed=embed)

    @welcome.command(name="color")
    @commands.has_permissions(administrator=True)
    async def welcome_color(self, ctx, color: str):
        """تغيير لون الـ embed"""
        try:
            # تحويل الـ hex color
            if color.startswith('#'):
                color = color[1:]
            color_int = int(color, 16)
            
            settings = await self.get_welcome_settings(ctx.guild.id)
            settings['embed_color'] = color_int
            await self.save_welcome_settings(ctx.guild.id, settings)
            
            embed = discord.Embed(
                title="✅ تم تحديث لون الـ embed",
                description=f"اللون الجديد: #{color}",
                color=color_int
            )
            await ctx.send(embed=embed)
            
        except ValueError:
            await ctx.send("❌ لون غير صحيح! استخدم hex color مثل: `#FF0000` أو `FF0000`")

    @welcome.command(name="test")
    @commands.has_permissions(administrator=True)
    async def welcome_test(self, ctx):
        """اختبار رسالة الترحيب"""
        settings = await self.get_welcome_settings(ctx.guild.id)
        
        if not settings['enabled']:
            return await ctx.send("❌ نظام الترحيب معطل! استخدم `!welcome toggle` لتشغيله")
        
        # إرسال رسالة نصية إضافية إذا كانت موجودة
        if settings.get('message'):
            message = settings['message']
            replacements = {
                '{user}': ctx.author.display_name,
                '{mention}': ctx.author.mention,
                '{server}': ctx.guild.name,
                '{member_count}': str(ctx.guild.member_count)
            }
            for old, new in replacements.items():
                message = message.replace(old, new)
            await ctx.send(f"**رسالة إضافية:** {message}")
        
        # إرسال الـ embed
        embed = self.create_welcome_embed(ctx.author, settings)
        embed.title = "🧪 " + embed.title + " (اختبار)"
        await ctx.send(embed=embed)

async def setup(bot):
    # إنشاء جدول إعدادات الترحيب
    async with aiosqlite.connect("hunter.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS welcome_settings (
                guild_id INTEGER PRIMARY KEY,
                welcome_enabled BOOLEAN DEFAULT FALSE,
                welcome_channel_id INTEGER,
                welcome_message TEXT,
                welcome_image_url TEXT,
                welcome_embed_color INTEGER DEFAULT 0x2B2D31,
                welcome_title TEXT,
                welcome_description TEXT
            )
        """)
        await db.commit()
    
    await bot.add_cog(WelcomeCog(bot))