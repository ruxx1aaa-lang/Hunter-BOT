import discord
from discord.ext import commands
import aiosqlite
from datetime import datetime, timedelta
import json

class MissedActivitiesView(discord.ui.View):
    def __init__(self, user_id: int, guild_id: int, activities: list, since_time: datetime):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.guild_id = guild_id
        self.activities = activities
        self.since_time = since_time
        self.current_page = 0
        self.items_per_page = 10
        
        # تجميع الأنشطة حسب النوع
        self.activity_groups = {
            "join": [],
            "leave": [],
            "message": [],
            "voice_join": [],
            "voice_leave": [],
            "game_start": []
        }
        
        for activity in activities:
            activity_type = activity[0]
            if activity_type in self.activity_groups:
                self.activity_groups[activity_type].append(activity)
        
        self.update_buttons()
    
    def update_buttons(self):
        """تحديث حالة الأزرار"""
        total_pages = max(1, (len(self.activities) + self.items_per_page - 1) // self.items_per_page)
        
        # تعطيل/تفعيل أزرار التنقل
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= total_pages - 1
        
        # تحديث تسمية الصفحة
        self.page_button.label = f"صفحة {self.current_page + 1}/{total_pages}"
    
    def get_summary_embed(self):
        """الحصول على embed الملخص الرئيسي بنفس شكل الصورة"""
        if not self.activities:
            embed = discord.Embed(
                title="What You Missed",
                description="No recent activities",
                color=0x36393F
            )
            embed.set_footer(text=f"Last seen: {self.since_time.strftime('%Y-%m-%d %H:%M')}")
            return embed
        
        embed = discord.Embed(
            title="What You Missed",
            color=0x36393F  # لون رمادي داكن مثل Discord
        )
        
        # عرض الأنشطة بنفس تنسيق الصورة
        activity_text = ""
        
        # ترتيب الأنشطة حسب الوقت (الأحدث أولاً)
        sorted_activities = sorted(self.activities, key=lambda x: x[5], reverse=True)
        
        for activity in sorted_activities[:15]:  # أول 15 نشاط
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
        
        embed.set_footer(text="Use buttons below for more details")
        return embed
    
    def get_detailed_embed(self):
        """الحصول على embed التفاصيل مع التنقل"""
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_activities = self.activities[start_idx:end_idx]
        
        embed = discord.Embed(
            title="📋 What You Missed - التفاصيل",
            description=f"صفحة {self.current_page + 1} من الأنشطة التفصيلية",
            color=0x5865F2
        )
        
        for i, activity in enumerate(page_activities, start_idx + 1):
            activity_type, user_id, username, description, channel_id, timestamp, data = activity
            
            # تحويل الوقت
            activity_time = datetime.fromisoformat(timestamp)
            time_str = activity_time.strftime('%H:%M')
            
            # أيقونة حسب نوع النشاط
            icons = {
                "join": "👋",
                "leave": "👋",
                "message": "💬",
                "voice_join": "🔊",
                "voice_leave": "🔇",
                "game_start": "🎮"
            }
            
            icon = icons.get(activity_type, "📝")
            
            embed.add_field(
                name=f"{icon} {username} - {time_str}",
                value=description,
                inline=False
            )
        
        total_pages = max(1, (len(self.activities) + self.items_per_page - 1) // self.items_per_page)
        embed.set_footer(text=f"صفحة {self.current_page + 1}/{total_pages} • إجمالي: {len(self.activities)} نشاط")
        
        return embed
    
    @discord.ui.button(label="📋 Summary", style=discord.ButtonStyle.primary, row=0)
    async def summary_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """عرض الملخص الرئيسي"""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This command is for you only", ephemeral=True)
        
        embed = self.get_summary_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="📝 Details", style=discord.ButtonStyle.secondary, row=0)
    async def details_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """عرض التفاصيل مع التنقل"""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This command is for you only", ephemeral=True)
        
        embed = self.get_detailed_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary, row=1)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """الصفحة السابقة"""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ هذا الأمر خاص بك فقط", ephemeral=True)
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.get_detailed_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="صفحة 1/1", style=discord.ButtonStyle.secondary, row=1, disabled=True)
    async def page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """عرض رقم الصفحة (غير تفاعلي)"""
        await interaction.response.defer()
    
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary, row=1)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """الصفحة التالية"""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ هذا الأمر خاص بك فقط", ephemeral=True)
        
        total_pages = max(1, (len(self.activities) + self.items_per_page - 1) // self.items_per_page)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.get_detailed_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.success, row=2)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """تحديث البيانات"""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This command is for you only", ephemeral=True)
        
        # إعادة تحميل البيانات
        from cogs.activity_tracker import ActivityTracker
        tracker = ActivityTracker(interaction.client)
        
        activities, since_time = await tracker.get_missed_activities(self.user_id, self.guild_id)
        self.activities = activities
        self.since_time = since_time
        
        # إعادة تجميع الأنشطة
        self.activity_groups = {
            "join": [],
            "leave": [],
            "message": [],
            "voice_join": [],
            "voice_leave": [],
            "game_start": []
        }
        
        for activity in activities:
            activity_type = activity[0]
            if activity_type in self.activity_groups:
                self.activity_groups[activity_type].append(activity)
        
        self.current_page = 0
        self.update_buttons()
        
        embed = self.get_summary_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.danger, row=2)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """إغلاق الواجهة"""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ This command is for you only", ephemeral=True)
        
        embed = discord.Embed(
            title="✅ What You Missed Closed",
            description="Thanks for using the activity tracker!",
            color=discord.Color.green()
        )
        embed.set_footer(text="You can use !missed again anytime")
        await interaction.response.edit_message(embed=embed, view=None)

async def setup(bot):
    pass  # هذا الملف يحتوي على View فقط