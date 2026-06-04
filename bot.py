import asyncio
import os
import random
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
import threading
import sys

# === FLASK FOR RENDER ===
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Multiple Bots Auto-Reaction Running"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# === CONFIGURATION ===
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")

# Multiple Bots Tokens (comma separated)
BOT_TOKENS = os.environ.get("BOT_TOKENS", "").split(',')

# 2 Groups Configuration
COMMAND_GROUP = os.environ.get("COMMAND_GROUP", "")
TARGET_GROUP = os.environ.get("TARGET_GROUP", "")

# Default settings
DEFAULT_REACTIONS = ["👍", "❤️", "🔥", "🎉", "😍", "👏", "💯", "⭐", "🤣", "😱", "🥳", "😎"]
DEFAULT_BOT_COUNT = 5

# Storage
user_settings = {}
bots_list = []
command_bot = None

print("=" * 60)
print("🤖 STARTING MULTIPLE BOTS AUTO-REACTION SYSTEM")
print("=" * 60)
print(f"Python version: {sys.version}")
print("=" * 60)

# === MULTIPLE BOTS MANAGER ===
class MultiBotReaction:
    def __init__(self):
        self.bots = []
        self.command_bot = None
        
    async def init_bots(self):
        """Initialize all bots"""
        print("\n📋 Initializing bots...")
        
        bot_count = 0
        valid_tokens = [t.strip() for t in BOT_TOKENS if t.strip()]
        
        print(f"📊 Total tokens found: {len(valid_tokens)}")
        
        for token in valid_tokens:
            try:
                bot = Client(f"bot_{bot_count}", api_id=API_ID, api_hash=API_HASH, bot_token=token, in_memory=True)
                await bot.start()
                
                bot_info = await bot.get_me()
                self.bots.append(bot)
                bot_count += 1
                print(f"✅ Bot {bot_count}: @{bot_info.username}")
                
            except Exception as e:
                print(f"❌ Failed: {str(e)[:50]}...")
            
            await asyncio.sleep(0.5)
        
        print(f"\n✅ Total bots initialized: {len(self.bots)}")
        print(f"📌 Command Group: {COMMAND_GROUP}")
        print(f"🎯 Target Group: {TARGET_GROUP}")
        
        if self.bots:
            self.command_bot = self.bots[0]
            return True
        return False
    
    async def add_reactions(self, message_id: int, chat_id: int, reactions_list: list, bot_count: int):
        """Add reactions using multiple bots"""
        try:
            available_bots = len(self.bots)
            actual_bots = min(bot_count, available_bots, len(reactions_list))
            
            if actual_bots == 0:
                return False
            
            selected_bots = random.sample(self.bots, actual_bots)
            selected_reactions = random.sample(reactions_list, actual_bots)
            
            success_count = 0
            for i, bot in enumerate(selected_bots):
                try:
                    message = await bot.get_messages(chat_id, message_id)
                    await message.react(selected_reactions[i])
                    success_count += 1
                    await asyncio.sleep(0.3)
                except Exception as e:
                    print(f"Reaction error: {e}")
            
            print(f"✅ Added {success_count}/{actual_bots} reactions")
            return success_count > 0
            
        except Exception as e:
            print(f"Multi-bot error: {e}")
            return False
    
    async def start(self):
        """Start the multi-bot system"""
        
        if not await self.init_bots():
            print("❌ No bots initialized! Exiting...")
            return
        
        # Join target group
        print("\n📋 Adding bots to target group...")
        for bot in self.bots:
            try:
                await bot.join_chat(TARGET_GROUP)
                print(f"✅ Bot joined {TARGET_GROUP}")
            except Exception as e:
                print(f"⚠️ Could not join: {e}")
            await asyncio.sleep(0.5)
        
        # === COMMAND HANDLERS ===
        
        @self.command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("start"))
        async def start_command(client: Client, message: Message):
            await message.reply(
                "🤖 **Auto-Reaction Bot**\n\n"
                f"📊 **Active Bots:** {len(self.bots)}\n"
                f"📌 **Command Group:** {COMMAND_GROUP}\n"
                f"🎯 **Target Group:** {TARGET_GROUP}\n\n"
                "**Commands:**\n"
                "`.setreactions 👍,❤️,🔥` - Set reactions\n"
                "`.setbots 10` - Set bot count\n"
                "`.react on/off` - Toggle auto-react\n"
                "`.reactnow` - Manual reaction\n"
                "`.settings` - View settings\n"
                "`.bots` - View bots"
            )
        
        @self.command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("setreactions"))
        async def set_reactions(client: Client, message: Message):
            user_id = message.from_user.id
            args = message.text.split(maxsplit=1)
            
            if len(args) < 2:
                await message.reply("❌ Usage: `.setreactions 👍,❤️,🔥`")
                return
            
            reactions = [r.strip() for r in args[1].split(',') if r.strip()]
            
            if not reactions:
                await message.reply("❌ Provide valid emojis!")
                return
            
            if user_id not in user_settings:
                user_settings[user_id] = {
                    "reactions": DEFAULT_REACTIONS.copy(),
                    "bot_count": min(DEFAULT_BOT_COUNT, len(self.bots)),
                    "auto_react": True
                }
            
            user_settings[user_id]["reactions"] = reactions
            await message.reply(f"✅ Reactions set: {' '.join(reactions[:10])}")
        
        @self.command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("setbots"))
        async def set_bot_count(client: Client, message: Message):
            user_id = message.from_user.id
            args = message.text.split()
            
            if len(args) < 2:
                await message.reply(f"❌ Usage: `.setbots 10` (max: {len(self.bots)})")
                return
            
            try:
                count = int(args[1])
                max_bots = len(self.bots)
                
                if count > max_bots:
                    count = max_bots
                    await message.reply(f"⚠️ Only {max_bots} bots available! Setting to {max_bots}")
                
                if user_id not in user_settings:
                    user_settings[user_id] = {
                        "reactions": DEFAULT_REACTIONS.copy(),
                        "bot_count": count,
                        "auto_react": True
                    }
                else:
                    user_settings[user_id]["bot_count"] = count
                
                await message.reply(f"✅ {count} bots will react per post!")
                
            except ValueError:
                await message.reply("❌ Provide a valid number!")
        
        @self.command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("react"))
        async def toggle_react(client: Client, message: Message):
            user_id = message.from_user.id
            args = message.text.split()
            
            if len(args) < 2:
                await message.reply("❌ Usage: `.react on` or `.react off`")
                return
            
            if user_id not in user_settings:
                user_settings[user_id] = {
                    "reactions": DEFAULT_REACTIONS.copy(),
                    "bot_count": min(DEFAULT_BOT_COUNT, len(self.bots)),
                    "auto_react": True
                }
            
            if args[1].lower() == "on":
                user_settings[user_id]["auto_react"] = True
                await message.reply("✅ Auto-reaction ON")
            elif args[1].lower() == "off":
                user_settings[user_id]["auto_react"] = False
                await message.reply("❌ Auto-reaction OFF")
        
        @self.command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("reactnow"))
        async def react_now(client: Client, message: Message):
            user_id = message.from_user.id
            
            if user_id not in user_settings:
                await message.reply("❌ First set settings with `.setreactions` and `.setbots`")
                return
            
            try:
                async for msg in self.command_bot.get_chat_history(TARGET_GROUP, limit=2):
                    if msg.text and not msg.text.startswith('.'):
                        target_msg = msg
                        break
                else:
                    await message.reply("❌ No messages found!")
                    return
                
                settings = user_settings[user_id]
                reactions = settings.get("reactions", DEFAULT_REACTIONS)
                bot_count = min(settings.get("bot_count", DEFAULT_BOT_COUNT), len(self.bots), len(reactions))
                
                status = await message.reply(f"🎯 Adding {bot_count} reactions...")
                await self.add_reactions(target_msg.id, TARGET_GROUP, reactions, bot_count)
                await status.edit_text(f"✅ Added {bot_count} reactions!")
                
            except Exception as e:
                await message.reply(f"❌ Error: {str(e)[:100]}")
        
        @self.command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("bots"))
        async def list_bots(client: Client, message: Message):
            bot_names = []
            for bot in self.bots[:20]:
                try:
                    info = await bot.get_me()
                    bot_names.append(f"• @{info.username}")
                except:
                    bot_names.append("• Unknown")
            
            text = f"🤖 **Active Bots:** {len(self.bots)}\n\n"
            text += "\n".join(bot_names)
            if len(self.bots) > 20:
                text += f"\n... and {len(self.bots)-20} more"
            
            await message.reply(text)
        
        @self.command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("settings"))
        async def show_settings(client: Client, message: Message):
            user_id = message.from_user.id
            
            if user_id not in user_settings:
                await message.reply("No settings configured! Use `.setreactions` and `.setbots`")
                return
            
            s = user_settings[user_id]
            text = f"**Settings:**\n\n"
            text += f"📋 Reactions: {' '.join(s['reactions'][:5])}...\n"
            text += f"🤖 Bots: {s['bot_count']}/{len(self.bots)}\n"
            text += f"⚡ Auto-react: {'ON' if s['auto_react'] else 'OFF'}\n"
            text += f"🎯 Total reactions/post: {s['bot_count']}"
            await message.reply(text)
        
        # === AUTO-REACTION ON TARGET GROUP ===
        @self.command_bot.on_message(filters.chat(TARGET_GROUP))
        async def auto_react_on_target(client: Client, message: Message):
            try:
                if message.from_user and message.from_user.is_bot:
                    return
                
                for user_id, settings in user_settings.items():
                    if settings.get("auto_react", True):
                        reactions = settings.get("reactions", DEFAULT_REACTIONS)
                        bot_count = min(settings.get("bot_count", DEFAULT_BOT_COUNT), len(self.bots), len(reactions))
                        
                        if bot_count > 0:
                            await asyncio.sleep(2)
                            await self.add_reactions(message.id, TARGET_GROUP, reactions, bot_count)
                        break
                        
            except Exception as e:
                print(f"Auto-react error: {e}")
        
        print("\n" + "=" * 60)
        print("🚀 SYSTEM READY!")
        print("=" * 60)
        print(f"🤖 Active Bots: {len(self.bots)}")
        print(f"📌 Commands in: {COMMAND_GROUP}")
        print(f"🎯 Reactions in: {TARGET_GROUP}")
        print("\n💡 Quick Start:")
        print("   1. .setreactions 👍,❤️,🔥")
        print("   2. .setbots 5")
        print("   3. .react on")
        print("=" * 60)
        
        await self.command_bot.run()
    
    async def stop(self):
        for bot in self.bots:
            try:
                await bot.stop()
            except:
                pass

# === MAIN ===
async def main():
    if not COMMAND_GROUP or not TARGET_GROUP:
        print("\n❌ ERROR: Set COMMAND_GROUP and TARGET_GROUP in environment variables!")
        return
    
    multi_bot = MultiBotReaction()
    try:
        await multi_bot.start()
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        await multi_bot.stop()

if __name__ == "__main__":
    # Start Flask thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Run multi-bot system
    asyncio.run(main())
