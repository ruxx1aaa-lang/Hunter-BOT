import discord
from discord.ext import commands
import requests
import json
import os

class IPInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # IP Info function
    def get_ip_info(self, ip_address=None):
        try:
            if ip_address is None:
                # Get current machine's public IP (bot's server IP)
                ip_response = requests.get("https://api.ipify.org?format=json")
                ip_address = ip_response.json()["ip"]
            
            # Get location info for the IP
            url = f"https://ipinfo.io/{ip_address}/json"
            response = requests.get(url)
            data = response.json()
            
            return {
                "ip": data.get("ip", "N/A"),
                "city": data.get("city", "N/A"),
                "region": data.get("region", "N/A"),
                "country": data.get("country", "N/A"),
                "location": data.get("loc", "N/A"),  # lat,lon format
                "org": data.get("org", "N/A"),
                "timezone": data.get("timezone", "N/A")
            }
        except Exception as e:
            return {"error": str(e)}

    @commands.command(name="ipinfo")
    async def ip_info(self, ctx, ip_address=None):
        """
        ده الكوماند الرئيسي. بيفي ','.get_location與location و IP المعلومات.
        
        الاستخدام:
        !ipinfo                  -> حاتعرف الـ IP والـ location للسيرفر نفسه.
        !ipinfo 1.2.3.4          -> حاتعرف الـ IP والـ location لعنوان IP محدد.
        !ipinfo @username        -> حاتعرف الـ IP والـ location لعنوان IP المستخدم.
        """
        await ctx.send("🧐 جاري البحث في IP و الـ location...")
        
        # If the user provides a mention, use it (اذا كان في mention للمستخدم)
        if ip_address and ip_address.startswith("<@"):
            # Extract user ID from mention
            user_id = ip_address.strip("<@!>")
            try:
                member = ctx.guild.get_member(int(user_id))
                if member:
                    # In a real scenario, you'd need to track user IPs (this is not real without additional setup)
                    await ctx.send(f"❌ لا يمكن الحصول على IP الخاص بـ {member.mention} مباشرةً.")
                    return
            except:
                pass

        # Get IP info
        info = self.get_ip_info(ip_address)

        if "error" in info:
            await ctx.send(f"❌ حدث خطأ: {info['error']}")
            return

        # Build the response message
        response = f"🌐 **IP Information**\n"
        response += f"**IP Address:** `{info['ip']}`\n"
        response += f"**Country:** `{info['country']}`\n"
        response += f"**City:** `{info['city']}`\n"
        response += f"**Region:** `{info['region']}`\n"
        response += f"**Coordinates:** `{info['location']}`\n"
        response += f"**Organization:** `{info['org']}`\n"
        response += f"**Timezone:** `{info['timezone']}`\n"
        
        # Add map link if coordinates are available
        if info['location'] and info['location'] != "N/A":
            coords = info['location'].split(',')
            if len(coords) == 2:
                map_url = f"https://www.google.com/maps?q={coords[0]},{coords[1]}"
                response += f"\n**Map:** {map_url}"

        # Send the message
        await ctx.send(response)

    @commands.command(name="botip")
    async def bot_ip(self, ctx):
        """يعرض الـ IP والـ location للـ bot server."""
        info = self.get_ip_info()
        if "error" in info:
            await ctx.send(f"❌ حدث خطأ: {info['error']}")
            return

        response = f"🤖 **Server IP Information**\n"
        response += f"**IP Address:** `{info['ip']}`\n"
        response += f"**Country:** `{info['country']}`\n"
        response += f"**City:** `{info['city']}`\n"
        response += f"**Region:** `{info['region']}`\n"
        response += f"**Organization:** `{info['org']}`\n"
        
        await ctx.send(response)

# Setup function to load the Cog
async def setup(bot):
    await bot.add_cog(IPInfo(bot))