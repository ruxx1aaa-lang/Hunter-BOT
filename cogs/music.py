import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from collections import deque

# لو في cookies كـ env variable، اكتبها في ملف مؤقت
_cookies_content = os.getenv("YOUTUBE_COOKIES", "")
COOKIES_FILE = None
if _cookies_content:
    COOKIES_FILE = "/tmp/cookies.txt"
    import base64
    try:
        # جرب base64 أول
        decoded = base64.b64decode(_cookies_content).decode("utf-8")
        with open(COOKIES_FILE, "w") as f:
            f.write(decoded)
    except Exception:
        # لو مش base64، اكتبه مباشرة
        with open(COOKIES_FILE, "w") as f:
            f.write(_cookies_content)
elif os.path.exists("cookies.txt"):
    COOKIES_FILE = "cookies.txt"

# إعدادات yt-dlp - بدون إعلانات وأسرع تحميل
YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "cookiefile": COOKIES_FILE,
    # تجاهل الإعلانات
    "postprocessors": [],
    "extract_flat": False,
}

# إعدادات FFmpeg - بدون تأخير
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn -bufsize 512k",
}


class MusicCog(commands.Cog, name="Music"):
    def __init__(self, bot):
        self.bot = bot
        # كل سيرفر عنده queue منفصل
        self.queues: dict[int, deque] = {}
        self.current: dict[int, dict] = {}
        self.loop_mode: dict[int, bool] = {}  # تكرار الأغنية الحالية

    def get_queue(self, guild_id: int) -> deque:
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        return self.queues[guild_id]

    async def search_and_extract(self, query: str) -> dict | None:
        """بيدور على الأغنية ويجيب الـ stream URL"""
        loop = asyncio.get_event_loop()

        def _extract():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                # لو مش رابط، يدور على يوتيوب
                if not query.startswith("http"):
                    info = ydl.extract_info(f"ytsearch:{query}", download=False)
                    if info and "entries" in info and info["entries"]:
                        info = info["entries"][0]
                else:
                    info = ydl.extract_info(query, download=False)
                    # لو playlist، ياخد أول أغنية
                    if "entries" in info:
                        info = info["entries"][0]
                return info

        try:
            info = await loop.run_in_executor(None, _extract)
            if not info:
                return None
            return {
                "url": info["url"],
                "title": info.get("title", "Unknown"),
                "duration": info.get("duration", 0),
                "webpage_url": info.get("webpage_url", ""),
                "thumbnail": info.get("thumbnail", ""),
                "uploader": info.get("uploader", "Unknown"),
            }
        except Exception as e:
            print(f"[Music] Error extracting: {e}")
            return None

    def format_duration(self, seconds: int) -> str:
        if not seconds:
            return "Live 🔴"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    async def play_next(self, ctx: commands.Context):
        """يشغل الأغنية الجاية في الـ queue"""
        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return

        # لو loop mode شغال، يعيد نفس الأغنية
        if self.loop_mode.get(guild_id) and guild_id in self.current:
            track = self.current[guild_id]
        elif queue:
            track = queue.popleft()
            self.current[guild_id] = track
        else:
            self.current.pop(guild_id, None)
            await ctx.send("✅ خلصت الـ queue، البوت هيفضل في الفويس.")
            return

        def after_playing(error):
            if error:
                print(f"[Music] Player error: {error}")
            asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

        try:
            source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTIONS)
            source = discord.PCMVolumeTransformer(source, volume=0.8)
            vc.play(source, after=after_playing)

            embed = discord.Embed(
                title="🎵 بيشتغل دلوقتي",
                description=f"**[{track['title']}]({track['webpage_url']})**",
                color=discord.Color.green(),
            )
            embed.add_field(name="⏱ المدة", value=self.format_duration(track["duration"]))
            embed.add_field(name="👤 القناة", value=track["uploader"])
            if track["thumbnail"]:
                embed.set_thumbnail(url=track["thumbnail"])
            embed.set_footer(text=f"Queue: {len(queue)} أغنية متبقية")
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"[Music] Playback error: {e}")
            await ctx.send(f"❌ حصل خطأ أثناء التشغيل: `{e}`")
            await self.play_next(ctx)

    # ─────────────────────────────────────────
    # Commands
    # ─────────────────────────────────────────

    @commands.command(name="p", aliases=["play", "شغل"])
    async def play(self, ctx: commands.Context, *, query: str):
        """يشغل أغنية أو يضيفها للـ queue | !p <اسم أو رابط>"""

        # لازم يكون في فويس شانل
        if not ctx.author.voice:
            return await ctx.send("❌ لازم تكون في فويس شانل الأول!")

        voice_channel = ctx.author.voice.channel
        vc = ctx.voice_client

        # يدخل الفويس لو مش فيه
        if not vc:
            vc = await voice_channel.connect()
        elif vc.channel != voice_channel:
            await vc.move_to(voice_channel)

        # رسالة انتظار
        loading_msg = await ctx.send("🔍 بدور على الأغنية...")

        track = await self.search_and_extract(query)
        await loading_msg.delete()

        if not track:
            return await ctx.send("❌ مش لاقي الأغنية دي، جرب رابط تاني أو اسم تاني.")

        queue = self.get_queue(ctx.guild.id)

        # لو مفيش حاجة بتشتغل، شغل على طول
        if not vc.is_playing() and not vc.is_paused():
            self.current[ctx.guild.id] = track
            await self.play_next_direct(ctx, track, vc)
        else:
            queue.append(track)
            embed = discord.Embed(
                title="➕ اتضافت للـ Queue",
                description=f"**[{track['title']}]({track['webpage_url']})**",
                color=discord.Color.blue(),
            )
            embed.add_field(name="⏱ المدة", value=self.format_duration(track["duration"]))
            embed.add_field(name="📋 موقعها في الـ Queue", value=f"#{len(queue)}")
            await ctx.send(embed=embed)

    async def play_next_direct(self, ctx, track, vc):
        """يشغل أغنية مباشرة (مش من الـ queue)"""
        def after_playing(error):
            if error:
                print(f"[Music] Player error: {error}")
            asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

        try:
            source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTIONS)
            source = discord.PCMVolumeTransformer(source, volume=0.8)
            vc.play(source, after=after_playing)

            embed = discord.Embed(
                title="🎵 بيشتغل دلوقتي",
                description=f"**[{track['title']}]({track['webpage_url']})**",
                color=discord.Color.green(),
            )
            embed.add_field(name="⏱ المدة", value=self.format_duration(track["duration"]))
            embed.add_field(name="👤 القناة", value=track["uploader"])
            if track["thumbnail"]:
                embed.set_thumbnail(url=track["thumbnail"])
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"❌ حصل خطأ: `{e}`")

    @commands.command(name="skip", aliases=["s", "سكيب"])
    async def skip(self, ctx: commands.Context):
        """يسكيب الأغنية الحالية"""
        vc = ctx.voice_client
        if not vc or not vc.is_playing():
            return await ctx.send("❌ مفيش حاجة بتشتغل دلوقتي.")
        vc.stop()
        await ctx.send("⏭ تم السكيب!")

    @commands.command(name="stop", aliases=["وقف"])
    async def stop(self, ctx: commands.Context):
        """يوقف الموسيقى ويمسح الـ queue"""
        vc = ctx.voice_client
        if not vc:
            return await ctx.send("❌ البوت مش في فويس شانل.")
        guild_id = ctx.guild.id
        self.queues[guild_id] = deque()
        self.current.pop(guild_id, None)
        self.loop_mode[guild_id] = False
        vc.stop()
        await ctx.send("⏹ تم إيقاف الموسيقى ومسح الـ queue.")

    @commands.command(name="pause", aliases=["بوز"])
    async def pause(self, ctx: commands.Context):
        """يوقف الأغنية مؤقتاً"""
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await ctx.send("⏸ تم الإيقاف المؤقت.")
        else:
            await ctx.send("❌ مفيش حاجة بتشتغل.")

    @commands.command(name="resume", aliases=["r", "كمل"])
    async def resume(self, ctx: commands.Context):
        """يكمل الأغنية بعد الإيقاف المؤقت"""
        vc = ctx.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await ctx.send("▶️ تم الاستكمال.")
        else:
            await ctx.send("❌ الأغنية مش متوقفة.")

    @commands.command(name="queue", aliases=["q", "قائمة"])
    async def show_queue(self, ctx: commands.Context):
        """يعرض الـ queue الحالي"""
        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)
        current = self.current.get(guild_id)

        if not current and not queue:
            return await ctx.send("📭 الـ queue فاضي.")

        embed = discord.Embed(title="🎶 قائمة الأغاني", color=discord.Color.purple())

        if current:
            loop_icon = "🔂 " if self.loop_mode.get(guild_id) else ""
            embed.add_field(
                name=f"{loop_icon}▶️ بيشتغل دلوقتي",
                value=f"**{current['title']}** ({self.format_duration(current['duration'])})",
                inline=False,
            )

        if queue:
            tracks_list = []
            for i, track in enumerate(list(queue)[:10], 1):
                tracks_list.append(f"`{i}.` {track['title']} ({self.format_duration(track['duration'])})")
            if len(queue) > 10:
                tracks_list.append(f"... و {len(queue) - 10} أغنية تانية")
            embed.add_field(name="📋 القادم", value="\n".join(tracks_list), inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="loop", aliases=["لوب"])
    async def loop(self, ctx: commands.Context):
        """يفعل/يوقف تكرار الأغنية الحالية"""
        guild_id = ctx.guild.id
        self.loop_mode[guild_id] = not self.loop_mode.get(guild_id, False)
        status = "🔂 تم تفعيل التكرار" if self.loop_mode[guild_id] else "➡️ تم إيقاف التكرار"
        await ctx.send(status)

    @commands.command(name="volume", aliases=["vol", "صوت"])
    async def volume(self, ctx: commands.Context, vol: int):
        """يغير الصوت (1-100) | !volume 80"""
        vc = ctx.voice_client
        if not vc or not vc.source:
            return await ctx.send("❌ مفيش حاجة بتشتغل.")
        if not 1 <= vol <= 100:
            return await ctx.send("❌ الصوت لازم يكون بين 1 و 100.")
        vc.source.volume = vol / 100
        await ctx.send(f"🔊 الصوت اتغير لـ {vol}%")

    @commands.command(name="join", aliases=["انضم"])
    async def join(self, ctx: commands.Context):
        """يدخل الفويس شانل بتاعك"""
        if not ctx.author.voice:
            return await ctx.send("❌ لازم تكون في فويس شانل الأول!")
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.send(f"✅ اتضمت لـ **{channel.name}**")

    @commands.command(name="leave", aliases=["dc", "امشي"])
    async def leave(self, ctx: commands.Context):
        """يخرج من الفويس شانل"""
        vc = ctx.voice_client
        if not vc:
            return await ctx.send("❌ البوت مش في فويس شانل.")
        guild_id = ctx.guild.id
        self.queues[guild_id] = deque()
        self.current.pop(guild_id, None)
        await vc.disconnect()
        await ctx.send("👋 خرجت من الفويس شانل.")

    @commands.command(name="nowplaying", aliases=["np", "شغال"])
    async def nowplaying(self, ctx: commands.Context):
        """يعرض الأغنية اللي بتشتغل دلوقتي"""
        current = self.current.get(ctx.guild.id)
        if not current:
            return await ctx.send("❌ مفيش حاجة بتشتغل دلوقتي.")
        embed = discord.Embed(
            title="🎵 بيشتغل دلوقتي",
            description=f"**[{current['title']}]({current['webpage_url']})**",
            color=discord.Color.green(),
        )
        embed.add_field(name="⏱ المدة", value=self.format_duration(current["duration"]))
        embed.add_field(name="👤 القناة", value=current["uploader"])
        if current["thumbnail"]:
            embed.set_thumbnail(url=current["thumbnail"])
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(MusicCog(bot))
