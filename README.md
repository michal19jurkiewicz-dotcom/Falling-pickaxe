# Falling Pickaxe
Falling Pickaxe Game inspired from YouTube shorts livestreams.

You can check my video here:
https://www.youtube.com/watch?v=gcjeidHWEb4
<div align="left">
      <a href="https://www.youtube.com/watch?v=gcjeidHWEb4">
         <img src="https://img.youtube.com/vi/gcjeidHWEb4/0.jpg" style="width:40%;">
      </a>
</div>

## Before you use it
If you consider streaming this game on your own youtube channel, please add credits in the description of your video/livestream. Credits should inclue a link to this repository and [a link to my youtube channel.](https://www.youtube.com/@vycdev)

Copy paste example:
```
Falling Pickaxe game made by Vycdev
YT: https://www.youtube.com/@vycdev
GH: https://github.com/vycdev/falling-pickaxe
```

Donations on [YouTube (Super Thanks)](https://www.youtube.com/watch?v=gcjeidHWEb4) or showing support on [Patreon](https://patreon.com/vycdev?utm_medium=unknown&utm_source=join_link&utm_campaign=creatorshare_creator&utm_content=copyLink) is also highly appreciated.

## How to use it
*Update: You can watch my tutorial here: https://youtu.be/aFrvoFE7r_g*

### Quick Start (Recommended)
The easiest way to run the game is using the automated scripts that handle everything for you:

**For Windows:**
Just double-click `Start Game.bat` in the project's root folder - no terminal needed.

Or from a terminal:
```
./scripts/run.ps1
```

**For Linux/macOS:**
```
chmod +x ./scripts/run.sh
./scripts/run.sh
```

These scripts will automatically:
- Create a Python virtual environment if it doesn't exist
- Install all required dependencies
- Run the game with automatic restart on crashes
- Exit cleanly when you close the game window

### Manual Setup (Advanced Users)
If you prefer to set up the environment manually:

1. Make sure you have Python 3.x installed. If you don't, follow the instructions from the official [python website](http://python.org/downloads/)
2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Linux/macOS:
   source .venv/bin/activate
   ```
3. Install packages:
   ```
   pip install -r requirements.txt
   ```
4. Run the game:
   ```
   python ./src/main.py
   ```

### Configuration
When you launch the game you land on a menu with **PLAY**, **SETTINGS** and **QUIT**. Open **SETTINGS** to configure everything through a normal in-game screen (checkboxes, text fields, scrollable sections) - no manual JSON editing required:

1. Under "YouTube Chat", turn on **Chat control enabled** and paste your livestream's URL or video ID into **Livestream URL / video ID**.
2. (Optional) Under "Subscribers (StreamElements)", enable subscriber alerts - see "Free chat & subscriber integration" below.
3. Adjust any of the other sections (TNT & Pickaxe events, Pickaxe Rain, Sky & weather, HUD, ...) to your liking.
4. Click **SAVE & BACK** - your changes are written to `config.json` immediately, then click **PLAY**.

Everything is still stored in `config.json` under the hood (created automatically from `default.config.json` on first run), so advanced users can still edit that file directly if they prefer - the in-game Settings screen just reads and writes the same file.

**Note:** The automated scripts (`run.ps1`, `run.sh` and `Start Game.bat`) will run the game and restart it in case of unexpected crashes. When you close the game window normally, the script will exit cleanly. This is perfect for unattended streams.

You can disable the entire YouTube integration by turning off **Chat control enabled** in Settings (or setting `"CHAT_CONTROL": false` in `config.json`).

### Free chat & subscriber integration
This game does **not** use the official YouTube Data API, so there's no Google Cloud project, no API key, and no daily quota to manage.

- **Chat, Super Chats and Super Stickers** are read with [chat-downloader](https://github.com/xenova/chat-downloader), the same way the live chat webpage itself works. Nothing to configure beyond the livestream URL/ID - it reconnects automatically if the connection drops or the stream hasn't started yet, which matters for long, unattended streams.
- **New-subscriber alerts** (the ones that spawn a MegaTNT) use a free [StreamElements](https://streamelements.com/) account instead, because YouTube itself only exposes an *exact* subscriber count through its paid-quota API - the public channel page rounds the number for channels over ~1,000 subscribers, which makes polling for "+1" unreliable. StreamElements already tracks each individual subscription in real time (it's what powers its on-stream alert widgets), so this reports the real event instead of guessing from a rounded number.
  1. Create a free account at [streamelements.com](https://streamelements.com/) and connect your YouTube channel to it.
  2. Open your account/channel settings in the StreamElements dashboard and copy your **Channel ID** and **JWT Token**.
  3. In the game's Settings screen (or `config.json`), enable **Subscriber alerts enabled** and paste both values into **StreamElements channel ID** and **StreamElements JWT token**.
  4. Leave subscriber alerts disabled if you'd rather skip this - everything else (chat, Super Chats) works without it.

### Available chat commands
```
tnt

fast
slow

big

wood
stone
iron
gold
diamond
netherite
```

### MegaTNT spawning

Extra details about when a MegaTNT appears in the game:

- New subscribers are detected in real time through the free StreamElements integration described above (see "Free chat & subscriber integration"). Each subscription event appends an entry to the `mega_tnt_queue` (the string `"New Subscriber"`) and the MegaTNT will be spawned when the queues are processed.
- Queue processing happens every `QUEUES_POP_INTERVAL_SECONDS` (see `default.config.json` / `config.json`).
- Requirements for automatic MegaTNT spawning: `CHAT_CONTROL` must be `true`, and `SUBSCRIBER_ALERTS_ENABLED` must be `true` with a valid `STREAMELEMENTS_CHANNEL_ID` / `STREAMELEMENTS_JWT_TOKEN` configured.
- The queued owner name is currently the literal string `"New Subscriber"` (not the subscriber's username). You can change this behavior in code if you want actual usernames used.
- You can also spawn a MegaTNT manually in-game by pressing the `M` key — this spawns immediately (no queue).
- MegaTNTs use a larger explosion radius, detonate automatically ~4 seconds after spawn, and trigger a stronger camera shake.


### Livestream-friendly extras
All of these are on by default and can each be turned off independently in `config.json` - nothing here needs any external account or API key, everything is generated at runtime.

- **Pickaxe Rain** - a periodic, purely-visual "it's raining pickaxes" moment (reuses the existing pickaxe art). Toggle with `PICKAXE_RAIN_ENABLED`, tune timing with `PICKAXE_RAIN_INTERVAL_SECONDS_MIN/MAX` and `PICKAXE_RAIN_DURATION_SECONDS`.
- **Day/night cycle** - the sky gradually shifts through night/sunrise/day/sunset. Toggle with `DAY_NIGHT_CYCLE_ENABLED`, set the full cycle length with `DAY_NIGHT_CYCLE_SECONDS`.
- **Moving clouds** - toggle with `CLOUDS_ENABLED`.
- **Weather** - rain, snow and storms (with lightning + thunder) come and go automatically, each with its own ambient sound. Toggle with `WEATHER_ENABLED`, tune how often it changes with `WEATHER_CHANGE_INTERVAL_SECONDS_MIN/MAX`. If both `DAY_NIGHT_CYCLE_ENABLED` and `CLOUDS_ENABLED` are turned off, the game falls back to the original static background image.
- **Best depth record** - your deepest run is saved to `logs/high_score.json` and shown in the HUD as `BEST`, surviving between game restarts.
- **HUD panels** - the on-screen command list, the "next event" / active-event countdown, and the center "LIKE = TNT" / "SUB = MEGA TNT" engagement banner can each be turned off with `HUD_SHOW_COMMANDS`, `HUD_SHOW_NEXT_EVENT` and `HUD_SHOW_ENGAGEMENT_BANNER`.

## Contributing
Any kind of improvements to the code, refactoring, new features, bug fixes, ideas, or anything else is welcome. You can open an issue or a pull requets and I will review it as soon as I can.

You can also help by subscribing or becoming a member of [my YouTube channel](https://www.youtube.com/@vycdev) to help me create more videos and projects like these.

## AI Slop for SEO (ignore this if you are a human being)
**Falling Pickaxe: Ultimate Mining Arcade Game for Streamers – Explosive Action & Massive Earnings!**

Step into the world of **Falling Pickaxe**, the most addictive and interactive mining arcade game designed specifically for YouTube streamers! In this high-energy, physics-based adventure, you control a gigantic pickaxe falling through a dynamic, block-filled landscape. Smash obstacles, trigger explosive TNT, and collect valuable ores to power up your gameplay while engaging with your audience in real time.

**Why Falling Pickaxe is a Must-Play for Streamers:**

- **Interactive Live Chat Integration:** Let your viewers control the game! Live commands and super chats can spawn TNT, upgrade your pickaxe, or trigger wild power-ups, creating a fully immersive, viewer-driven experience that boosts engagement and subscriber growth.
- **Explosive Visuals & Retro Charm:** Enjoy stunning particle effects, realistic physics, and explosive animations that keep your stream exciting and visually captivating. Every impact and explosion is a spectacle that draws in viewers and increases watch time.
- **Monetization & Revenue Opportunities:** Use Falling Pickaxe to maximize your earnings through super chats, donations, and sponsored gameplay challenges. With its fast-paced action and interactive features, your channel becomes a hotspot for gaming enthusiasts and potential sponsors.
- **Community-Driven Challenges:** Host live competitions, subscriber challenges, and donation-triggered events that make every stream a unique and engaging event. Build a loyal community and watch your subscriber count soar!

Transform your YouTube channel into a money-making, interactive gaming hub with **Falling Pickaxe** – the ultimate mining adventure that delivers explosive action, high viewer engagement, and serious revenue potential. Start streaming today and experience the thrill of interactive arcade gaming like never before!

## Inspiration
As I showed you in the video my inspiration was [Petyr](https://www.youtube.com/@petyrguardian) and the other YouTubers who made their own version of the Falling Pickaxe game. Huge thanks to them.

## External contributors
https://www.youtube.com/@Iklzzz
