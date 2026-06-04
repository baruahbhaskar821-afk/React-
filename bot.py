import asyncio
import os
import random
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
import threading
import re

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
COMMAND_GROUP = os.environ.get("COMMAND_GROUP", "")  # Jahan se commands doge
TARGET_GROUP = os.environ.get("TARGET_GROUP", "")    # Jahan posts pe reaction dena hai

# Default settings
DEFAULT_REACTIONS = ["👍", "❤️", "🔥", "🎉", "😍", "👏", "💯", "⭐", "🤣", "😱", "🥳", "😎"]
DEFAULT_BOT_COUNT = 5

# Storage
user_settings = {}  # {user_id: {"reactions": list, "bot_count": int}}
bots_list = []  # List of bot clients
main_bot = None

# === MULTIPLE BOTS MANAGER ===
class MultiBotReaction:
    def __init__(self):
        self.bots = []
        self.command_bot = None
        
    async def init_bots(self):
        """Initialize all bots"""
        print("\n" + "=" * 60)
        print("🤖 INITIALIZING MULTIPLE BOTS")
        print("=" * 60)
        
        bot_count = 0
        for token in BOT_TOKENS:
            token = token.strip()
            if not token:
                continue
                
            try:
                bot = Client(f"bot_{bot_count}", api_id=API_ID, api_hash=API_HASH, bot_token=token)
                await bot.start()
                
                bot_info = await bot.get_me()
                self.bots.append(bot)
                bot_count += 1
                print(f"✅ Bot {bot_count}: @{bot_info.username}")
                
            except Exception as e:
                print(f"❌ Failed: {str(e)[:50]}...")
            
            await asyncio.sleep(0.5)
        
        print(f"\n📊 Total bots initialized: {len(self.bots)}")
        print(f"📌 Command Group: {COMMAND_GROUP}")
        print(f"🎯 Target Group: {TARGET_GROUP}")
        print("=" * 60)
        
        # Use first bot as command bot
        if self.bots:
            self.command_bot = self.bots[0]
            return True
        return False
    
    async def add_reactions(self, message_id: int, chat_id: int, reactions_list: list, bot_count: int):
        """Add reactions using multiple bots to a specific message"""
        try:
            available_bots = len(self.bots)
            actual_bots = min(bot_count, available_bots, len(reactions_list))
            
            if actual_bots == 0:
                return False
            
            # Select random bots
            selected_bots = random.sample(self.bots, actual_bots)
            
            # Select random reactions
            selected_reactions = random.sample(reactions_list, actual_bots)
            
            # Add reactions
            success_count = 0
            for i, bot in enumerate(selected_bots):
                try:
                    # Get the message and react
                    message = await bot.get_messages(chat_id, message_id)
                    await message.react(selected_reactions[i])
                    success_count += 1
                    await asyncio.sleep(0.3)
                except Exception as e:
                    print(f"Bot reaction error: {e}")
            
            print(f"✅ Added {success_count}/{actual_bots} reactions to message {message_id}")
            return success_count > 0
            
        except Exception as e:
            print(f"Multi-bot reaction error: {e}")
            return False
    
    async def start(self):
        """Start the multi-bot system"""
        
        # Initialize all bots
        if not await self.init_bots():
            print("❌ No bots initialized! Exiting...")
            return
        
        # Join target group with all bots
        print("\n📋 Adding bots to target group...")
        for bot in self.bots:
            try:
                await bot.join_chat(TARGET_GROUP)
                print(f"✅ Bot joined {TARGET_GROUP}")
            except Exception as e:
                print(f"⚠️ Bot join error: {e}")
            await asyncio.sleep(0.5)
        
        # === COMMAND HANDLERS (in COMMAND GROUP only) ===
        
        @self.command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("start"))
        async def start_command(client: Client, message: Message):
            await message.reply(
                "🤖 **Multiple Bots Auto-Reaction System**\n\n"
                f"📊 **Active Bots:** {len(self.bots)}\n"
                f"📌 **Command Group:** {COMMAND_GROUP}\n"
                f"🎯 **Target Group:** {TARGET_GROUP}\n\n"
                "**Commands:**\n"
                "`.setreactions 👍,❤️,🔥` - Set reaction emojis\n"
                "`.setbots 10` - Kitne bots reaction denge\n"
                "`.react on` - Auto-reaction ON\n"
                "`.react off` - Auto-reaction OFF\n"
                "`.reactnow` - Manual reaction on last message\n"
                "`.settings` - See current settings\n"
                "`.bots` - See active bots list\n\n"
                f"⚡ **Current active bots:** {len(self.bots)}"
            )
        
        @self.command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("setreactions"))
        async def set_reactions(client: Client, message: Message):
            user_id = message.from_user.id
            args = message.text.split(maxsplit=1)
            
            if len(args) < 2:
                await message.reply("❌ Usage: `.setreactions 👍,❤️,🔥,🎉`")
                return
            
            reactions_text = args[1]
            reactions = [r.strip() for r in reactions_text.split(',') if r.strip()]
            
            if not reactions:
                await message.reply("❌ Please provide valid emojis!")
                return
            
            if user_id not in user_settings:
                user_settings[user_id] = {
                    "reactions": DEFAULT_REACTIONS.copy(),
                    "bot_count": min(DEFAULT_BOT_COUNT, len(self.bots)),
                    "auto_react": True
                }
            
            user_settings[user_id]["reactions"] = reactions
            
            await message.reply(
                f"✅ Reactions set to: {' '.join(reactions[:10])}\n\n"
                f"📊 Total: {len(reactions)} reactions available"
            )
        
        @self.command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("setbots"))
        async def set_bot_count(client: Client, message: Message):
            user_id = message.from_user.id
            args = message.text.split()
            
            if len(args) < 2:
                await message.reply(f"❌ Usage: `.setbots 10`\n\nMax available: {len(self.bots)} bots")
                return
            
            try:
                count = int(args[1])
                if count < 1:
                    await message.reply("❌ Count must be at least 1!")
                    return
                
                max_bots = len(self.bots)
                if count > max_bots:
                    await message.reply(f"⚠️ You have only {max_bots} bots!\nSetting to {max_bots}")
                    count = max_bots
                
                if user_id not in user_settings:
                    user_settings[user_id] = {
                        "reactions": DEFAULT_REACTIONS.copy(),
                        "bot_count": count,
                        "auto_react": True
                    }
                else:
                    user_settings[user_id]["bot_count"] = count
                
                await message.reply(
                    f"✅ {count} bots will react to your posts!\n\n"
                    f"🤖 Each bot gives 1 reaction\n"
                    f"🎯 Total reactions per post: {count}"
                )
                
            except ValueError:
                await message.reply("❌ Please provide a valid number!")
        
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
                await message.reply("✅ Auto-reaction **ON** - Saare naye posts pe reaction denge!")
            elif args[1].lower() == "off":
                user_settings[user_id]["auto_react"] = False
                await message.reply("❌ Auto-reaction **OFF** - Ab reaction nahi denge")
            else:
                await message.reply("❌ Use `.react on` or `.react off`")
        
        @self.command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("reactnow"))
        async def react_now(client: Client, message: Message):
            user_id = message.from_user.id
            
            if user_id not in user_settings:
                await message.reply("❌ First set your settings using `.setreactions` and `.setbots`")
                return
            
            # Get last message from target group
            try:
                last_messages = []
                async for msg in self.command_bot.get_chat_history(TARGET_GROUP, limit=5):
                    if msg.text and not msg.text.startswith('.'):
                        last_messages.append(msg)
                        break
                
                if not last_messages:
                    await message.reply("❌ No messages found in target group!")
                    return
                
                target_msg = last_messages[0]
                
                settings = user_settings[user_id]
                reactions = settings.get("reactions", DEFAULT_REACTIONS)
                bot_count = min(settings.get("bot_count", DEFAULT_BOT_COUNT), len(self.bots), len(reactions))
                
                status_msg = await message.reply(f"🎯 Adding {bot_count} reactions to last message...")
                
                await self.add_reactions(target_msg.id, TARGET_GROUP, reactions, bot_count)
                
                await status_msg.edit_text(f"✅ Added {bot_count} reactions to the message!")
                
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
                    bot_names.append("• Unknown bot")
            
            bot_text = "\n".join(bot_names)
            if len(self.bots) > 20:
                bot_text += f"\n... and {len(self.bots)-20} more"
            
            await message.reply(
                f"🤖 **Active Bots:** {len(self.bots)}\n\n"
                f"{bot_text}\n\n"
                f"⚡ Each bot gives 1 reaction per post\n"
                f"🎯 Target Group: {TARGET_GROUP}"
            )
        
        @self.command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("settings"))
        async def show_settings(client: Client, message: Message):
            user_id = message.from_user.id
            
            if user_id not in user_settings:
                settings_text = "**Current Settings:**\n\n"
                settings_text += f"📋 Reactions: {' '.join(DEFAULT_REACTIONS[:5])}...\n"
                settings_text += f"🤖 Bots Count: {min(DEFAULT_BOT_COUNT, len(self.bots))}\n"
                settings_text += f"⚡ Auto-Reaction: OFF\n\n"
                settings_text += "Use `.setreactions` and `.setbots` to configure!"
            else:
                settings = user_settings[user_id]
                reactions = ' '.join(settings.get("reactions", DEFAULT_REACTIONS)[:10])
                if len(settings.get("reactions", [])) > 10:
                    reactions += "..."
                bot_count = settings.get("bot_count", DEFAULT_BOT_COUNT)
                auto_react = "ON ✅" if settings.get("auto_react", True) else "OFF ❌"
                
                settings_text = "**Current Settings:**\n\n"
                settings_text += f"📋 Reactions: {reactions}\n"
                settings_text += f"🤖 Bots Used: {bot_count} / {len(self.bots)}\n"
                settings_text += f"⚡ Auto-Reaction: {auto_react}\n"
                settings_text += f"🎯 **Total Reactions Per Post:** {bot_count}\n\n"
                settings_text += f"📌 Command Group: {COMMAND_GROUP}\n"
                settings_text += f"🎯 Target Group: {TARGET_GROUP}"
            
            await message.reply(settings_text)
        
        @self.command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("stats"))
        async def stats_command(client: Client, message: Message):
            total_users = len(user_settings)
            
            stats_text = f"📊 **Bot Statistics**\n\n"
            stats_text += f"🤖 Total Bots: {len(self.bots)}\n"
            stats_text += f"👤 Total Users: {total_users}\n"
            stats_text += f"📌 Command Group: {COMMAND_GROUP}\n"
            stats_text += f"🎯 Target Group: {TARGET_GROUP}\n"
            stats_text += f"⚡ Max Reactions/Post: {len(self.bots)}\n\n"
            stats_text += f"✅ System is active and running!"
            
            await message.reply(stats_text)
        
        # === AUTO-REACTION ON TARGET GROUP ===
        @self.command_bot.on_message(filters.chat(TARGET_GROUP))
        async def auto_react_on_target(client: Client, message: Message):
            try:
                # Skip bot's own messages
                if message.from_user and message.from_user.is_bot:
                    return
                
                # Find user who has auto-react ON
                for user_id, settings in user_settings.items():
                    if settings.get("auto_react", True):
                        reactions = settings.get("reactions", DEFAULT_REACTIONS)
                        bot_count = min(settings.get("bot_count", DEFAULT_BOT_COUNT), len(self.bots), len(reactions))
                        
                        if bot_count > 0:
                            # Small delay to ensure message is posted
                            await asyncio.sleep(2)
                            await self.add_reactions(message.id, TARGET_GROUP, reactions, bot_count)
                        break  # Only react once per message
                
            except Exception as e:
                print(f"Auto-react error: {e}")
        
        print("\n" + "=" * 60)
        print("🚀 MULTIPLE BOTS AUTO-REACTION SYSTEM READY!")
        print("=" * 60)
        print(f"🤖 Active Bots: {len(self.bots)}")
        print(f"📌 Send commands in: {COMMAND_GROUP}")
        print(f"🎯 Reactions will appear in: {TARGET_GROUP}")
        print(f"⚡ Max reactions per post: {len(self.bots)}")
        print("\n💡 Commands:")
        print("   .setreactions 👍,❤️,🔥")
        print("   .setbots 30")
        print("   .react on")
        print("   .reactnow (manual reaction on last message)")
        print("=" * 60)
        
        # Keep command bot running
        await self.command_bot.run()
    
    async def stop(self):
        """Stop all bots"""
        for bot in self.bots:
            try:
                await bot.stop()
            except:
                pass

# === MAIN ===
async def main():
    if not COMMAND_GROUP or not TARGET_GROUP:
        print("\n❌ ERROR: Please set COMMAND_GROUP and TARGET_GROUP in environment variables!")
        print("   COMMAND_GROUP = @your_command_group")
        print("   TARGET_GROUP = @your_target_group")
        return
    
    multi_bot = MultiBotReaction()
    try:
        await multi_bot.start()
    except KeyboardInterrupt:
        print("\n🛑 Stopping all bots...")
        await multi_bot.stop()

if __name__ == "__main__":
    # Start Flask thread for Render
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Run multi-bot system
    asyncio.run(main())
