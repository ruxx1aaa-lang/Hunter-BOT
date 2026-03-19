import discord
from discord.ext import commands
import re
import base64
import json
from datetime import datetime
import logging

# إعداد التسجيل (Logging)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TokenAnalyzer")

class TokenAnalyzer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # نمط للكشف عن توكنات Discord
        self.token_pattern = re.compile(r'([a-zA-Z0-9_-]{24}\.[a-zA-Z0-9_-]{6}\.[a-zA-Z0-9_-]{27})')
        self.extracted_tokens = []
        logger.info("TokenAnalyzer cog initialized")

    # --- الأمر الرئيسي: تحليل التوكنات ---
    @commands.command(name="analyze_tokens", aliases=["check_tokens", "token_scan"])
    @commands.has_permissions(administrator=True)  # يقتصر على الأدمن فقط
    async def analyze_tokens(self, ctx, *, text: str = None):
        """
        يستخرج ويعالج التوكنات من النص المقدم.
        الاستخدام: !analyze_tokens <نص يحتوي على التوكن>
        """
        if not text:
            await ctx.send("⚠️ **خطأ:** يرجى توفير نص يحتوي على التوكنات لتحليلها.")
            return

        tokens = self.extract_tokens(text)

        if not tokens:
            await ctx.send("🔍 لم يتم العثور على أي توكنات Discord في النص.")
            return

        # تحليل كل توكن
        analysis_results = []
        for token in tokens:
            token_info = self.analyze_token(token)
            analysis_results.append(token_info)
            self.extracted_tokens.append(token_info)  # حفظ للسجل

        # إنشاء Embed للنتائج
        embed = discord.Embed(
            title="🔐 نتائج تحليل التوكنات",
            description=f"تم العثور على {len(tokens)} توكن(ات)",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"تم التحليل بواسطة: {ctx.author}")

        for i, result in enumerate(analysis_results, 1):
            embed.add_field(
                name=f"التوكن #{i}",
                value=f"**البادئة (Prefix):** `{result['prefix']}`\n"
                      f"**المعرف (User ID):** `{result['user_id']}`\n"
                      f"**الحالة:** `{result['status']}`",
                inline=False
            )

        await ctx.send(embed=embed)
        
        # تسجيل الجلسة
        logger.info(f"Analysis performed by {ctx.author} in guild {ctx.guild.id}: {len(tokens)} tokens found")

    # --- أمر لحفظ التوكنات في ملف ---
    @commands.command(name="save_token_log")
    @commands.has_permissions(administrator=True)
    async def save_token_log(self, ctx, filename: str = None):
        """حفظ السجل المخزن في ملف JSON"""
        if not self.extracted_tokens:
            await ctx.send("⚠️ لا توجد توكنات مخزنة لحفظها. استخدم !analyze_tokens أولاً.")
            return

        filename = filename or f"token_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "analyst": str(ctx.author),
            "guild": ctx.guild.name,
            "tokens": self.extracted_tokens
        }

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            await ctx.send(f"✅ تم حفظ السجل في الملف: `{filename}`")
        except Exception as e:
            await ctx.send(f"❌ فشل الحفظ: {e}")

    # --- أمر لمسح السجل المؤقت ---
    @commands.command(name="clear_token_log")
    @commands.has_permissions(administrator=True)
    async def clear_token_log(self, ctx):
        """مسح التوكنات المخزنة مؤقتاً"""
        self.extracted_tokens.clear()
        await ctx.send("🗑️ تم مسح سجل التوكنات المؤقت.")

    # --- دوال مساعدة ---
    def extract_tokens(self, text: str) -> list:
        """استخراج التوكنات باستخدام Regex"""
        tokens = self.token_pattern.findall(text)
        return list(set(tokens))  # إزالة التكرار

    def analyze_token(self, token: str) -> dict:
        """تحليل هيكل التوكن"""
        parts = token.split('.')
        status = "Valid Format" if len(parts) == 3 else "Invalid Format"
        
        user_id = "Unknown"
        if len(parts) > 1:
            try:
                # محاولة فك تشفير الجزء الأوسط (Payload)
                payload = parts[1]
                # إضافة padding إذا لزم الأمر
                padding = 4 - len(payload) % 4
                if padding != 4:
                    payload += '=' * padding
                decoded_bytes = base64.urlsafe_b64decode(payload)
                user_id = decoded_bytes.decode('utf-8', errors='ignore')
            except:
                user_id = "Cannot Decode"

        return {
            "prefix": parts[0] if len(parts) > 0 else "Unknown",
            "user_id": user_id,
            "signature": parts[2] if len(parts) > 2 else "Unknown",
            "status": status
        }

    # --- مستمع الرسائل (للكشف عن التوكنات في الشات) ---
    @commands.Cog.listener()
    async def on_message(self, message):
        # تجاهل رسائل البوتات
        if message.author.bot:
            return

        # الكشف عن التوكنات في الرسائل العادية (للتأمين)
        tokens = self.extract_tokens(message.content)
        if tokens:
            # يمكن إضافة تنبيه هنا إذا أردت
            logger.warning(f"Potential tokens detected in message from {message.author} in guild {message.guild.id}")

# دالة التحميل المطلوبة للـ Cog
async def setup(bot):
    await bot.add_cog(TokenAnalyzer(bot))