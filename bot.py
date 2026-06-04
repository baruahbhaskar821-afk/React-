import asyncio
import os
import random
from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
import threading
import sys

# Flask for Render
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot Running"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

# Config
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKENS = [t.strip() for t in os.environ.get("BOT_TOKENS", "").split(',') if t.strip()]
COMMAND_GROUP = os.environ.get("COMMAND_GROUP", "")
TARGET_GROUP = os.environ.get("TARGET_GROUP", "")

DEFAULT_REACTIONS = ["👍", "❤️", "🔥", "🎉", "😍"]
DEFAULT_BOT_COUNT = 3

user_settings = {}
bots = []
command_bot = None

print("=" * 60)
print("🤖 MULTIPLE BOTS AUTO-REACTION SYSTEM (FIXED)")
print("=" * 60)
print(f"Python: {sys.version}")
print(f"Total Bot Tokens: {len(BOT_TOKENS)}")
print(f"Command Group: {COMMAND_GROUP}")
print(f"Target Group: {TARGET_GROUP}")
print("=" * 60)

async def init_bots():
    global bots, command_bot
    print("\n📋 Initializing bots...")
    
    for i, token in enumerate(BOT_TOKENS):
        try:
            bot = Client(f"bot_{i}", api_id=API_ID, api_hash=API_HASH, bot_token=token, in_memory=True)
            await bot.start()
            info = await bot.get_me()
            bots.append(bot)
            print(f"✅ Bot {len(bots)}: @{info.username}")
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"❌ Failed: {str(e)[:50]}")
    
    print(f"\n✅ Total bots: {len(bots)}")
    if bots:
        command_bot = bots[0]
        return True
    return False

async def add_reactions(message_id, chat_id, reactions_list, bot_count):
    try:
        available = len(bots)
        actual = min(bot_count, available, len(reactions_list))
        if actual == 0:
            return False
        
        selected_bots = random.sample(bots, actual)
        selected_reactions = random.sample(reactions_list, actual)
        
        success = 0
        for i, bot in enumerate(selected_bots):
            try:
                msg = await bot.get_messages(chat_id, message_id)
                await msg.react(selected_reactions[i])
                success += 1
                await asyncio.sleep(0.3)
            except:
                pass
        
        print(f"✅ Added {success}/{actual} reactions")
        return success > 0
    except Exception as e:
        print(f"Error: {e}")
        return False

async def main():
    global user_settings
    
    if not await init_bots():
        print("❌ No bots initialized!")
        return
    
    # Don't auto-join - just warn
    print("\n⚠️ Please manually add all bots to the target group!")
    print(f"   Target Group: {TARGET_GROUP}")
    print("   Add each bot as a member using 'Add Member' button\n")
    
    @command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("start"))
    async def cmd_start(client, message):
        await message.reply(
            f"🤖 **Auto-Reaction Bot Active!**\n\n"
            f"📊 Bots: {len(bots)}\n"
            f"📌 Command: {COMMAND_GROUP}\n"
            f"🎯 Target: {TARGET_GROUP}\n\n"
            "**Commands:**\n"
            "`.setreactions 👍,❤️,🔥`\n"
            "`.setbots 5`\n"
            "`.react on/off`\n"
            "`.reactnow`\n"
            "`.settings`"
        )
    
    @command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("setreactions"))
    async def cmd_setreactions(client, message):
        uid = message.from_user.id
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("❌ Usage: `.setreactions 👍,❤️,🔥`")
            return
        reactions = [r.strip() for r in args[1].split(',') if r.strip()]
        if not reactions:
            await message.reply("❌ No valid emojis!")
            return
        if uid not in user_settings:
            user_settings[uid] = {"reactions": DEFAULT_REACTIONS.copy(), "bot_count": 3, "auto_react": True}
        user_settings[uid]["reactions"] = reactions
        await message.reply(f"✅ Reactions set: {' '.join(reactions[:8])}")
    
    @command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("setbots"))
    async def cmd_setbots(client, message):
        uid = message.from_user.id
        args = message.text.split()
        if len(args) < 2:
            await message.reply(f"❌ Usage: `.setbots 5` (max: {len(bots)})")
            return
        try:
            count = int(args[1])
            if count > len(bots):
                count = len(bots)
                await message.reply(f"⚠️ Only {len(bots)} bots available! Setting to {count}")
            if uid not in user_settings:
                user_settings[uid] = {"reactions": DEFAULT_REACTIONS.copy(), "bot_count": count, "auto_react": True}
            else:
                user_settings[uid]["bot_count"] = count
            await message.reply(f"✅ {count} bots will react per post!")
        except:
            await message.reply("❌ Invalid number!")
    
    @command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("react"))
    async def cmd_react(client, message):
        uid = message.from_user.id
        args = message.text.split()
        if len(args) < 2:
            await message.reply("❌ Use `.react on` or `.react off`")
            return
        if uid not in user_settings:
            user_settings[uid] = {"reactions": DEFAULT_REACTIONS.copy(), "bot_count": 3, "auto_react": True}
        if args[1].lower() == "on":
            user_settings[uid]["auto_react"] = True
            await message.reply("✅ Auto-reaction ON")
        else:
            user_settings[uid]["auto_react"] = False
            await message.reply("❌ Auto-reaction OFF")
    
    @command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("reactnow"))
    async def cmd_reactnow(client, message):
        uid = message.from_user.id
        if uid not in user_settings:
            await message.reply("❌ First use `.setreactions` and `.setbots`")
            return
        try:
            async for msg in command_bot.get_chat_history(TARGET_GROUP, limit=2):
                if msg.text and not msg.text.startswith('.'):
                    target = msg
                    break
            else:
                await message.reply("❌ No messages found!")
                return
            
            s = user_settings[uid]
            reactions = s.get("reactions", DEFAULT_REACTIONS)
            count = min(s.get("bot_count", 3), len(bots), len(reactions))
            
            status = await message.reply(f"🎯 Adding {count} reactions...")
            await add_reactions(target.id, TARGET_GROUP, reactions, count)
            await status.edit_text(f"✅ Added {count} reactions!")
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)[:100]}")
    
    @command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("settings"))
    async def cmd_settings(client, message):
        uid = message.from_user.id
        if uid not in user_settings:
            await message.reply("No settings configured!")
            return
        s = user_settings[uid]
        text = f"**Settings:**\n\n"
        text += f"📋 Reactions: {' '.join(s['reactions'][:5])}\n"
        text += f"🤖 Bots: {s['bot_count']}/{len(bots)}\n"
        text += f"⚡ Auto-react: {'ON' if s['auto_react'] else 'OFF'}\n"
        text += f"🎯 Total/post: {s['bot_count']}"
        await message.reply(text)
    
    @command_bot.on_message(filters.chat(COMMAND_GROUP) & filters.command("bots"))
    async def cmd_bots(client, message):
        names = []
        for bot in bots[:20]:
            try:
                info = await bot.get_me()
                names.append(f"• @{info.username}")
            except:
                names.append("• Unknown")
        text = f"🤖 **Bots:** {len(bots)}\n\n" + "\n".join(names)
        await message.reply(text)
    
    # Auto-reaction on target group
    @command_bot.on_message(filters.chat(TARGET_GROUP))
    async def auto_react_handler(client, message):
        if message.from_user and message.from_user.is_bot:
            return
        for uid, s in user_settings.items():
            if s.get("auto_react", True):
                reactions = s.get("reactions", DEFAULT_REACTIONS)
                count = min(s.get("bot_count", 3), len(bots), len(reactions))
                if count > 0:
                    await asyncio.sleep(1)
                    await add_reactions(message.id, TARGET_GROUP, reactions, count)
                break
    
    print("=" * 60)
    print("🚀 SYSTEM READY!")
    print("=" * 60)
    print(f"🤖 Bots: {len(bots)}")
    print(f"📌 Commands: {COMMAND_GROUP}")
    print(f"🎯 Reactions: {TARGET_GROUP}")
    print("\n⚠️ IMPORTANT: Manually add all bots to the target group!")
    print("=" * 60)
    
    # Use idle() instead of run()
    await asyncio.Event().wait()

if __name__ == "__main__":
    # Start Flask
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Run main
    asyncio.run(main())
