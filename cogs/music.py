import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
import base64
import shutil
from collections import deque

# ─── Cookies ───────────────────────────────────────────────────────────────
_cookies_content = os.getenv("YOUTUBE_COOKIES", "")
COOKIES_FILE = None
if _cookies_content:
    COOKIES_FILE = "/tmp/cookies.txt"
    try:
        decoded = base64.b64decode(_cookies_content).decode("utf-8")
        with open(COOKIES_FILE, "w") as f:
            f.write(decoded)
    except Exception:
        with open(COOKIES_FILE, "w") as f:
            f.write(_cookies_content)
elif os.path.exists("cookies.txt"):
    COOKIES_FILE = "cookies.txt"

import subprocess

# ─── Install ffmpeg if not found ───────────────────────────────────────────
def ensure_ffmpeg():
    path = shutil.which("ffmpeg")
    if path:
        return path
    print("[Music] ffmpeg not found, installing via apt...")
    try:
        subprocess.run(["apt-get", "install", "-y", "ffmpeg"], check=True, capture_output=True)
        path = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
        print(f"[Music] ffmpeg installed at {path}")
        return path
    except Exception as e:
        print(f"[Music] apt install failed: {e}")
    return "ffmpeg"

# ─── FFmpeg path ───────────────────────────────────────────────────────────
FFMPEG_PATH = ensure_ffmpeg()
print(f"[Music] FFmpeg path: {FFMPEG_PATH}")

# ─── yt-dlp options ────────────────────────────────────────────────────────
YDL_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "default_search": "scsearch",  # SoundCloud بدل YouTube
    "source_address": "0.0.0.0",
    "extract_flat": False,
}

FFMPEG_OPTIONS = {
    "executable": FFMPEG_PATH,
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn -bufsize 512k",
}


class MusicCog(commands.Cog, name="Music"):
    def __init__(self, bot):
        self.bot = bot
        self.queues: dict[int, deque] = {}
        self.current: dict[int, dict] = {}
        self.loop_mode: dict[int, bool] = {}

    def get_queue(self, guild_id: int) -> deque:
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        return self.queues[guild_id]

    async def search_and_extract(self, query: str) -> dict | None:
        loop = asyncio.get_event_loop()

        def _extract():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                # لو YouTube link، نجرب YouTube
                if "youtube.com" in query or "youtu.be" in query:
                    opts = YDL_OPTIONS.copy()
                    opts["cookiefile"] = COOKIES_FILE
                    opts["extractor_args"] = {"youtube": {"player_client": ["android", "web_creator"]}}
                    with yt_dlp.YoutubeDL(opts) as ydl2:
                        info = ydl2.extract_info(query, download=False)
                else:
                    # SoundCloud search
                    if not query.startswith("http"):
                        info = ydl.extract_info(f"scsearch:{query}", download=False)
                        if info and "entries" in info and info["entries"]:
                            info = info["entries"][0]
                    else:
                        info = ydl.extract_info(query, download=False)
                        if info and "entries" in info:
                            info = info["entries"][0]

                if not info:
                    return None

                url = None
                formats = info.get("formats", [])
                for f in reversed(formats):
                    if f.get("acodec") != "none" and f.get("vcodec") == "none":
                        url = f.get("url")
                        break
                if not url:
                    url = info.get("url")
                if not url and formats:
                    url = formats[-1].get("url")

                return {
                    "url": url,
                    "title": info.get("title", "Unknown"),
                    "duration": info.get("duration", 0),
                    "webpage_url": info.get("webpage_url", ""),
                    "thumbnail": info.get("thumbnail", ""),
                    "uploader": info.get("uploader", "Unknown"),
                }

        try:
            result = await loop.run_in_executor(None, _extract)
            print(f"[Music] Extract result: title={result.get('title') if result else None}, url={'OK' if result and result.get('url') else 'NONE'}")
            return result
        except Exception as e:
            print(f"[Music] Error: {e}")
            return None

    def fmt(self, s: int) -> str:
        if not s:
            return "Live 🔴"
        m, s = divmod(int(s), 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    async def play_next(self, ctx: commands.Context):
        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)
        vc = ctx.voice_client

        if not vc or not vc.is_connected():
            return

        if self.loop_mode.get(guild_id) and guild_id in self.current:
            track = self.current[guild_id]
        elif queue:
            track = queue.popleft()
            self.current[guild_id] = track
        else:
            self.current.pop(guild_id, None)
            await ctx.send("✅ خلصت الـ queue.")
            return

        def after(error):
            if error:
                print(f"[Music] Player error: {error}")
            asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

        try:
            source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTIONS)
            source = discord.PCMVolumeTransformer(source, volume=0.8)
            vc.play(source, after=after)

            embed = discord.Embed(
                title="🎵 بيشتغل دلوقتي",
                description=f"**[{track['title']}]({track['webpage_url']})**",
                color=discord.Color.green(),
            )
            embed.add_field(name="⏱ المدة", value=self.fmt(track["duration"]))
            embed.add_field(name="👤 القناة", value=track["uploader"])
            if track["thumbnail"]:
                embed.set_thumbnail(url=track["thumbnail"])
            embed.set_footer(text=f"Queue: {len(queue)} أغنية متبقية")
            await ctx.send(embed=embed)
        except Exception as e:
            print(f"[Music] Playback error: {e}")
            await ctx.send(f"❌ خطأ في التشغيل: `{e}`")
            await self.play_next(ctx)

    # ─── Commands ──────────────────────────────────────────────────────────

    @commands.command(name="p", aliases=["play", "شغل"])
    async def play(self, ctx: commands.Context, *, query: str):
        if not ctx.author.voice:
            return await ctx.send("❌ لازم تكون في فويس شانل الأول!")

        channel = ctx.author.voice.channel
        vc = ctx.voice_client

        if not vc:
            vc = await channel.connect()
        elif vc.channel != channel:
            await vc.move_to(channel)

        loading = await ctx.send("🔍 بدور على الأغنية...")
        track = await self.search_and_extract(query)
        await loading.delete()

        if not track or not track.get("url"):
            print(f"[Music] No track found for: {query} | track={track}")
            return await ctx.send("❌ مش لاقي الأغنية دي، جرب اسم تاني.")

        queue = self.get_queue(ctx.guild.id)

        if not vc.is_playing() and not vc.is_paused():
            self.current[ctx.guild.id] = track

            def after(error):
                if error:
                    print(f"[Music] Player error: {error}")
                asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.bot.loop)

            source = discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTIONS)
            source = discord.PCMVolumeTransformer(source, volume=0.8)
            vc.play(source, after=after)

            embed = discord.Embed(
                title="🎵 بيشتغل دلوقتي",
                description=f"**[{track['title']}]({track['webpage_url']})**",
                color=discord.Color.green(),
            )
            embed.add_field(name="⏱ المدة", value=self.fmt(track["duration"]))
            embed.add_field(name="👤 القناة", value=track["uploader"])
            if track["thumbnail"]:
                embed.set_thumbnail(url=track["thumbnail"])
            await ctx.send(embed=embed)
        else:
            queue.append(track)
            embed = discord.Embed(
                title="➕ اتضافت للـ Queue",
                description=f"**[{track['title']}]({track['webpage_url']})**",
                color=discord.Color.blue(),
            )
            embed.add_field(name="⏱ المدة", value=self.fmt(track["duration"]))
            embed.add_field(name="📋 موقعها", value=f"#{len(queue)}")
            await ctx.send(embed=embed)

    @commands.command(name="skip", aliases=["s", "سكيب"])
    async def skip(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_playing():
            return await ctx.send("❌ مفيش حاجة بتشتغل.")
        vc.stop()
        await ctx.send("⏭ تم السكيب!")

    @commands.command(name="stop", aliases=["وقف"])
    async def stop(self, ctx):
        vc = ctx.voice_client
        if not vc:
            return await ctx.send("❌ البوت مش في فويس شانل.")
        self.queues[ctx.guild.id] = deque()
        self.current.pop(ctx.guild.id, None)
        self.loop_mode[ctx.guild.id] = False
        vc.stop()
        await ctx.send("⏹ تم إيقاف الموسيقى.")

    @commands.command(name="pause", aliases=["بوز"])
    async def pause(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await ctx.send("⏸ تم الإيقاف المؤقت.")
        else:
            await ctx.send("❌ مفيش حاجة بتشتغل.")

    @commands.command(name="resume", aliases=["r", "كمل"])
    async def resume(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await ctx.send("▶️ تم الاستكمال.")
        else:
            await ctx.send("❌ الأغنية مش متوقفة.")

    @commands.command(name="queue", aliases=["q", "قائمة"])
    async def show_queue(self, ctx):
        queue = self.get_queue(ctx.guild.id)
        current = self.current.get(ctx.guild.id)
        if not current and not queue:
            return await ctx.send("📭 الـ queue فاضي.")
        embed = discord.Embed(title="🎶 قائمة الأغاني", color=discord.Color.purple())
        if current:
            embed.add_field(name="▶️ بيشتغل دلوقتي",
                value=f"**{current['title']}** ({self.fmt(current['duration'])})", inline=False)
        if queue:
            lines = [f"`{i}.` {t['title']} ({self.fmt(t['duration'])})"
                     for i, t in enumerate(list(queue)[:10], 1)]
            if len(queue) > 10:
                lines.append(f"... و {len(queue)-10} أغنية تانية")
            embed.add_field(name="📋 القادم", value="\n".join(lines), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="loop", aliases=["لوب"])
    async def loop(self, ctx):
        self.loop_mode[ctx.guild.id] = not self.loop_mode.get(ctx.guild.id, False)
        await ctx.send("🔂 تكرار شغال" if self.loop_mode[ctx.guild.id] else "➡️ تكرار وقف")

    @commands.command(name="volume", aliases=["vol", "صوت"])
    async def volume(self, ctx, vol: int):
        vc = ctx.voice_client
        if not vc or not vc.source:
            return await ctx.send("❌ مفيش حاجة بتشتغل.")
        if not 1 <= vol <= 100:
            return await ctx.send("❌ الصوت بين 1 و 100.")
        vc.source.volume = vol / 100
        await ctx.send(f"🔊 الصوت {vol}%")

    @commands.command(name="np", aliases=["nowplaying", "شغال"])
    async def nowplaying(self, ctx):
        current = self.current.get(ctx.guild.id)
        if not current:
            return await ctx.send("❌ مفيش حاجة بتشتغل.")
        embed = discord.Embed(
            title="🎵 بيشتغل دلوقتي",
            description=f"**[{current['title']}]({current['webpage_url']})**",
            color=discord.Color.green(),
        )
        embed.add_field(name="⏱ المدة", value=self.fmt(current["duration"]))
        if current["thumbnail"]:
            embed.set_thumbnail(url=current["thumbnail"])
        await ctx.send(embed=embed)

    @commands.command(name="join", aliases=["انضم"])
    async def join(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("❌ لازم تكون في فويس شانل الأول!")
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.send(f"✅ اتضمت لـ **{channel.name}**")

    @commands.command(name="leave", aliases=["dc", "امشي"])
    async def leave(self, ctx):
        vc = ctx.voice_client
        if not vc:
            return await ctx.send("❌ البوت مش في فويس شانل.")
        self.queues[ctx.guild.id] = deque()
        self.current.pop(ctx.guild.id, None)
        await vc.disconnect()
        await ctx.send("👋 خرجت من الفويس شانل.")


async def setup(bot):
    await bot.add_cog(MusicCog(bot))
