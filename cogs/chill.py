import discord
from discord.ext import commands
import re
import json
import base64
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TokenAnalyzer(commands.Cog):
    """Token Analysis and Security Monitoring Tool for authorized security testing"""
    
    def __init__(self, bot):
        self.bot = bot
        self.token_pattern = re.compile(r'[a-zA-Z0-9_-]{24}\.[a-zA-Z0-9_-]{6}\.[a-zA-Z0-9_-]{27}')
        self.extracted_tokens = []
        
    @commands.command(name='analyze_tokens')
    async def analyze_tokens(self, ctx, *, text: str = None):
        """
        Extract and analyze Discord tokens from provided text for security assessment
        Usage: !analyze_tokens <text_with_tokens>
        """
        if not text:
            await ctx.send("⚠️ Please provide text containing tokens to analyze.")
            return
            
        tokens = self.extract_tokens(text)
        
        if not tokens:
            await ctx.send("🔍 No Discord tokens found in the provided text.")
            return
            
        analysis_results = []
        for token in tokens:
            token_info = self.analyze_token(token)
            analysis_results.append(token_info)
            
        # Store for monitoring
        self.extracted_tokens.extend(analysis_results)
        
        # Send results
        embed = discord.Embed(
            title="🔐 Token Analysis Results",
            description=f"Found {len(tokens)} token(s) for analysis",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        for i, result in enumerate(analysis_results, 1):
            embed.add_field(
                name=f"Token #{i}",
                value=f"**Prefix:** `{result['prefix']}`\n"
                      f"**User ID:** `{result.get('user_id', 'Unknown')}`\n"
                      f"**Status:** `{result['status']}`",
                inline=False
            )
            
        await ctx.send(embed=embed)
        
        # Log for security audit
        logger.info(f"Token analysis performed by {ctx.author}: {len(tokens)} token(s) found")
        
    @commands.command(name='save_tokens')
    async def save_tokens(self, ctx, filename: str = None):
        """Save extracted tokens to a JSON file for security audit"""
        if not self.extracted_tokens:
            await ctx.send("⚠️ No tokens extracted yet. Use `!analyze_tokens` first.")
            return
            
        filename = filename or f"token_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = {
            "audit_timestamp": datetime.utcnow().isoformat(),
            "analyst": str(ctx.author),
            "tokens": self.extracted_tokens
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
            
        await ctx.send(f"✅ Token audit saved to `{filename}`")
        
    @commands.command(name='clear_tokens')
    async def clear_tokens(self, ctx):
        """Clear stored token data"""
        self.extracted_tokens.clear()
        await ctx.send("🗑️ Cleared all extracted token data.")
        
    def extract_tokens(self, text: str) -> list:
        """Extract potential Discord tokens using regex pattern"""
        tokens = self.token_pattern.findall(text)
        return list(set(tokens))  # Remove duplicates
        
    def analyze_token(self, token: str) -> dict:
        """Analyze token structure and format"""
        parts = token.split('.')
        
        return {
            "prefix": parts[0] if len(parts) > 0 else "Unknown",
            "user_id": self.decode_payload(parts[1]) if len(parts) > 1 else "Unknown",
            "signature": parts[2] if len(parts) > 2 else "Unknown",
            "status": "Valid Format" if len(parts) == 3 else "Invalid Format",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    def decode_payload(self, payload: str) -> str:
        """Decode base64 payload to extract user ID"""
        try:
            # Add padding if needed
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            return str(decoded)
        except Exception:
            return "Invalid Payload"
            
    @commands.Cog.listener()
    async def on_message(self, message):
        """Monitor messages for tokens (for security assessment only)"""
        if message.author.bot:
            return
            
        tokens = self.extract_tokens(message.content)
        
        if tokens:
            logger.warning(f"Tokens detected in message from {message.author}")
            # For security audit purposes, we log the detection
            # In production, this would trigger security alerts
            
def setup(bot):
    bot.add_cog(TokenAnalyzer(bot))