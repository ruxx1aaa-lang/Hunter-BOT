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
        """الحصول على embed الملخص الرئيسي"""
        if not self.activities:
            embed = discord.Embed(
                title="📭 لا توجد أنشطة جديدة",
                description=f"لم تفتك أي أنشطة منذ آخر زيارة لك",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"آخر نشاط: {self.since_time.strftime('%Y-%m-%d %H:%M')}")
            return embed
        
        embed = discord.Embed(
            title="📋 What You Missed - ملخص",
            description=f"الأنشطة منذ آخر زيارة لك ({self.since_time.strftime('%Y-%m-%d %H:%M')})",
            color=0x5865F2
        )
        
        # عرض الانضمامات
        if self.activity_groups["join"]:
            joins = self.activity_groups["join"][:5]
            join_text = "\n".join([
                f"• **{act[2]}** انضم للسيرفر" 
                for act in joins
            ])
            if len(self.activity_groups["join"]) > 5:
                join_text += f"\n... و {len(self.activity_groups['join']) - 5} آخرين"
            embed.add_field(name="👋 انضمامات جديدة", value=join_text, inline=False)
        
        # عرض المغادرات
        if self.activity_groups["leave"]:
            leaves = self.activity_groups["leave"][:5]
            leave_text = "\n".join([
                f"• **{act[2]}** غادر السيرفر" 
                for act in leaves
            ])
            if len(self.activity_groups["leave"]) > 5:
                leave_text += f"\n... و {len(self.activity_groups['leave']) - 5} آخرين"
            embed.add_field(name="👋 مغادرات", value=leave_text, inline=False)
        
        # عرض الرسائل المهمة
        if self.activity_groups["message"]:
            messages = self.activity_groups["message"][:3]
            msg_text = "\n".join([
                f"• **{act[2]}** {act[3]}" 
                for act in messages
            ])
            if len(self.activity_groups["message"]) > 3:
                msg_text += f"\n... و {len(self.activity_groups['message']) - 3} رسائل أخرى"
            embed.add_field(name="💬 رسائل مهمة", value=msg_text, inline=False)
        
        # عرض أنشطة الصوت
        voice_activities = self.activity_groups["voice_join"] + self.activity_groups["voice_leave"]
        if voice_activities:
            voice_text = "\n".join([
                f"• **{act[2]}** {act[3]}" 
                for act in voice_activities[:3]
            ])
            if len(voice_activities) > 3:
                voice_text += f"\n... و {len(voice_activities) - 3} أنشطة أخرى"
            embed.add_field(name="🔊 أنشطة صوتية", value=voice_text, inline=False)
        
        # عرض الألعاب
        if self.activity_groups["game_start"]:
            games = self.activity_groups["game_start"][:3]
            game_text = "\n".join([
                f"• **{act[2]}** {act[3]}" 
                for act in games
            ])
            if len(self.activity_groups["game_start"]) > 3:
                game_text += f"\n... و {len(self.activity_groups['game_start']) - 3} ألعاب أخرى"
            embed.add_field(name="🎮 ألعاب جديدة", value=game_text, inline=False)
        
        # إحصائيات
        total_activities = len(self.activities)
        embed.add_field(
            name="📊 الإحصائيات",
            value=f"إجمالي الأنشطة: **{total_activities}**\nاستخدم الأزرار للتفاصيل",
            inline=True
        )
        
        embed.set_footer(text="استخدم الأزرار أدناه للتنقل والتفاصيل")
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
    
    @discord.ui.button(label="📋 ملخص", style=discord.ButtonStyle.primary, row=0)
    async def summary_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """عرض الملخص الرئيسي"""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ هذا الأمر خاص بك فقط", ephemeral=True)
        
        embed = self.get_summary_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="📝 تفاصيل", style=discord.ButtonStyle.secondary, row=0)
    async def details_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """عرض التفاصيل مع التنقل"""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ هذا الأمر خاص بك فقط", ephemeral=True)
        
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
    
    @discord.ui.button(label="🔄 تحديث", style=discord.ButtonStyle.success, row=2)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """تحديث البيانات"""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ هذا الأمر خاص بك فقط", ephemeral=True)
        
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
    
    @discord.ui.button(label="❌ إغلاق", style=discord.ButtonStyle.danger, row=2)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """إغلاق الواجهة"""
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ هذا الأمر خاص بك فقط", ephemeral=True)
        
        embed = discord.Embed(
            title="✅ تم إغلاق What You Missed",
            description="شكراً لاستخدام نظام تتبع الأنشطة!",
            color=discord.Color.green()
        )
        embed.set_footer(text="يمكنك استخدام !missed مرة أخرى")
        await interaction.response.edit_message(embed=embed, view=None)

async def setup(bot):
    pass  # هذا الملف يحتوي على View فقط