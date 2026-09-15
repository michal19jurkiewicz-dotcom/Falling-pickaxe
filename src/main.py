import time
import pygame
import pymunk
import pymunk.pygame_util
from youtube import validate_live_stream_id
from chat_watcher import ChatWatcher
from subscriber_watcher import SubscriberWatcher
from subscriber_count import SubscriberCountWatcher
from config import config
from atlas import create_texture_atlas
from pathlib import Path
from chunk import get_block, clean_chunks, delete_block, chunks
from constants import BLOCK_SCALE_FACTOR, BLOCK_SIZE, CHUNK_HEIGHT, CHUNK_WIDTH, INTERNAL_HEIGHT, INTERNAL_WIDTH, FRAMERATE
from pickaxe import Pickaxe
from camera import Camera
from sound import SoundManager
from tnt import Tnt, MegaTnt, SuperTnt, Creeper
from sky import Sky
from pickaxe_rain import PickaxeRain
from star_boost import StarBoost
from menu import run_main_menu
import random
from hud import Hud
from collections import deque

# Track key states
key_t_pressed = False
key_m_pressed = False

#
chat_watcher = None
subscriber_watcher = None
subscriber_count_watcher = None


def start_watchers():
    """Starts the free chat/subscriber background watchers based on the current config.
    Called after the settings menu closes, so it always reflects whatever the
    player just configured (including changes made in the in-game Settings screen).
    """
    global chat_watcher, subscriber_watcher, subscriber_count_watcher

    # Optional current-subscriber-count readout - independent of chat control,
    # it just periodically reads the channel's public "About" page.
    if config.get("SUBSCRIBER_COUNT_ENABLED", False):
        channel_url = config.get("SUBSCRIBER_COUNT_CHANNEL_URL", "")
        if channel_url:
            poll_interval = config.get("SUBSCRIBER_COUNT_POLL_INTERVAL_SECONDS", 60)
            subscriber_count_watcher = SubscriberCountWatcher(channel_url, poll_interval).start()
        else:
            print("SUBSCRIBER_COUNT_ENABLED is true but SUBSCRIBER_COUNT_CHANNEL_URL is missing. Subscriber count display disabled.")

    if config["CHAT_CONTROL"] != True:
        return

    video_id = validate_live_stream_id(config.get("LIVESTREAM_ID", ""))

    if video_id is None:
        print("No valid LIVESTREAM_ID configured. Chat control will be disabled.")
    else:
        log_dir = Path(__file__).parent.parent / "logs"
        cookies_file = config.get("YOUTUBE_COOKIES_FILE", "").strip() or None
        chat_watcher = ChatWatcher(video_id, log_dir=log_dir, cookies_file=cookies_file).start()
        print(f"Chat watcher started for video: {video_id}")

    if config.get("SUBSCRIBER_ALERTS_ENABLED", False):
        se_channel_id = config.get("STREAMELEMENTS_CHANNEL_ID", "")
        se_jwt_token = config.get("STREAMELEMENTS_JWT_TOKEN", "")

        if se_channel_id and se_jwt_token:
            subscriber_watcher = SubscriberWatcher(se_channel_id, se_jwt_token).start()
            print("Subscriber watcher started (StreamElements).")
        else:
            print("SUBSCRIBER_ALERTS_ENABLED is true but STREAMELEMENTS_CHANNEL_ID/STREAMELEMENTS_JWT_TOKEN are missing. Subscriber alerts disabled.")

# Queues for chat
tnt_queue = deque()
tnt_queue_authors = set()
tnt_rain_queue = deque()
tnt_rain_authors = set()
super_tnt_queue = deque()
super_tnt_authors = set()
tnt_superchat_queue = deque()
tnt_superchat_authors = set()
fast_slow_queue = deque()
fast_slow_authors = set()
big_queue = deque()
big_authors = set()
pickaxe_queue = deque()
pickaxe_authors = set()
mega_tnt_queue = deque()
creeper_queue = deque()
creeper_authors = set()

def handle_youtube_poll():
    if subscriber_watcher is not None:
        for _ in subscriber_watcher.drain():
            mega_tnt_queue.append("New Subscriber")  # Add to mega tnt queue

    if chat_watcher is None:
        return

    new_messages = chat_watcher.drain()

    for message in new_messages:
        author = message["author"]
        text = message["message"]
        is_superchat = message["is_superchat"]
        is_supersticker = message["is_supersticker"]

        text_lower = text.lower()

        # Check for "tnt" command (add author to regular tnt_queue) - Only English "tnt"
        if "tnt" in text_lower:
            if author not in tnt_queue_authors:
                tnt_queue.append(author)
                tnt_queue_authors.add(author)
                print(f"Added {author} to regular TNT queue")

        # "rain" - a shower of 3-8 regular TNT at once (this is what the LIKE banner refers to)
        if "rain" in text_lower:
            if author not in tnt_rain_authors:
                tnt_rain_queue.append(author)
                tnt_rain_authors.add(author)
                print(f"Added {author} to TNT Rain queue")

        # "super" - a single, stronger Super TNT
        if "super" in text_lower:
            if author not in super_tnt_authors:
                super_tnt_queue.append(author)
                super_tnt_authors.add(author)
                print(f"Added {author} to Super TNT queue")

        # "creeper" - spawns one falling Creeper that explodes after 3 seconds
        if "creeper" in text_lower:
            if author not in creeper_authors:
                creeper_queue.append(author)
                creeper_authors.add(author)
                print(f"Added {author} to Creeper queue")

        # Check for Superchat/Supersticker (add to superchat tnt queue)
        if is_superchat or is_supersticker:
            if author not in tnt_superchat_authors:
                 tnt_superchat_queue.append((author, text))
                 tnt_superchat_authors.add(author)
                 print(f"Added {author} to Superchat TNT queue")

        if "fast" in text.lower() and author not in fast_slow_authors:
            fast_slow_queue.append((author, "Fast"))
            fast_slow_authors.add(author)
            print(f"Added {author} to Fast queue")

        if "big" in text.lower() and author not in big_authors:
            big_queue.append(author)
            big_authors.add(author)
            print(f"Added {author} to Big queue")

        # Check for pickaxe commands (add author and pickaxe type to pickaxe_queue)
        if "wood" in text_lower:
             if author not in pickaxe_authors:
                 pickaxe_queue.append((author, "wooden_pickaxe"))
                 pickaxe_authors.add(author)
                 print(f"Added {author} to Pickaxe queue (wooden_pickaxe)")
        elif "stone" in text_lower:
             if author not in pickaxe_authors:
                 pickaxe_queue.append((author, "stone_pickaxe"))
                 pickaxe_authors.add(author)
                 print(f"Added {author} to Pickaxe queue (stone_pickaxe)")
        elif "iron" in text_lower:
             if author not in pickaxe_authors:
                 pickaxe_queue.append((author, "iron_pickaxe"))
                 pickaxe_authors.add(author)
                 print(f"Added {author} to Pickaxe queue (iron_pickaxe)")
        elif "gold" in text_lower:
             if author not in pickaxe_authors:
                 pickaxe_queue.append((author, "golden_pickaxe"))
                 pickaxe_authors.add(author)
                 print(f"Added {author} to Pickaxe queue (golden_pickaxe)")
        elif "diamond" in text_lower:
             if author not in pickaxe_authors:
                 pickaxe_queue.append((author, "diamond_pickaxe"))
                 pickaxe_authors.add(author)
                 print(f"Added {author} to Pickaxe queue (diamond_pickaxe)")
        elif "netherite" in text_lower:
             if author not in pickaxe_authors:
                 pickaxe_queue.append((author, "netherite_pickaxe"))
                 pickaxe_authors.add(author)
                 print(f"Added {author} to Pickaxe queue (netherite_pickaxe)")

    # print the queue counts (optional, for debugging)
    # print(f"Queues: TNT={len(tnt_queue)}, Superchat TNT={len(tnt_superchat_queue)}, Fast/Slow={len(fast_slow_queue)}, Big={len(big_queue)}, Pickaxe={len(pickaxe_queue)}, MegaTNT={len(mega_tnt_queue)}")

def game():
    window_width = int(INTERNAL_WIDTH / 2)
    window_height = int(INTERNAL_HEIGHT / 2)

    # Initialize pygame
    pygame.init()
    clock = pygame.time.Clock()

    # Pymunk physics
    space = pymunk.Space()
    space.gravity = (0, 1000)  # (x, y) - down is positive y

    # Create a resizable window
    screen_size = (window_width, window_height)
    screen = pygame.display.set_mode(screen_size, pygame.RESIZABLE)
    scaled_surface = pygame.Surface(screen_size).convert()
    pygame.display.set_caption("Falling Pickaxe")
    # set icon
    icon = pygame.image.load(Path(__file__).parent.parent / "src/assets/pickaxe" / "diamond_pickaxe.png")
    pygame.display.set_icon(icon)

    # Create an internal surface with fixed resolution
    internal_surface = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))

    # Load texture atlas
    assets_dir = Path(__file__).parent.parent / "src/assets"
    (texture_atlas, atlas_items) = create_texture_atlas(assets_dir)

    # Load background
    background_image = pygame.image.load(assets_dir / "background.png")
    background_scale_factor = 1.5
    background_width = int(background_image.get_width() * background_scale_factor)
    background_height = int(background_image.get_height() * background_scale_factor)
    background_image = pygame.transform.scale(background_image, (background_width, background_height))

    # Scale the entire texture atlas
    texture_atlas = pygame.transform.scale(texture_atlas,
                                        (texture_atlas.get_width() * BLOCK_SCALE_FACTOR,
                                        texture_atlas.get_height() * BLOCK_SCALE_FACTOR))

    for category in atlas_items:
        for item in atlas_items[category]:
            x, y, w, h = atlas_items[category][item]
            atlas_items[category][item] = (x * BLOCK_SCALE_FACTOR, y * BLOCK_SCALE_FACTOR, w * BLOCK_SCALE_FACTOR, h * BLOCK_SCALE_FACTOR)

    #sounds
    sound_manager = SoundManager()

    sound_manager.load_sound("tnt", assets_dir / "sounds" / "tnt.mp3", 0.3)
    sound_manager.load_sound("stone1", assets_dir / "sounds" / "stone1.wav", 0.5)
    sound_manager.load_sound("stone2", assets_dir / "sounds" / "stone2.wav", 0.5)
    sound_manager.load_sound("stone3", assets_dir / "sounds" / "stone3.wav", 0.5)
    sound_manager.load_sound("stone4", assets_dir / "sounds" / "stone4.wav", 0.5)
    sound_manager.load_sound("grass1", assets_dir / "sounds" / "grass1.wav", 0.1)
    sound_manager.load_sound("grass2", assets_dir / "sounds" / "grass2.wav", 0.1)
    sound_manager.load_sound("grass3", assets_dir / "sounds" / "grass3.wav", 0.1)
    sound_manager.load_sound("grass4", assets_dir / "sounds" / "grass4.wav", 0.1)
    sound_manager.load_sound("weather_rain", assets_dir / "sounds" / "weather_rain.wav", 0.4)
    sound_manager.load_sound("weather_wind", assets_dir / "sounds" / "weather_wind.wav", 0.3)
    sound_manager.load_sound("weather_storm", assets_dir / "sounds" / "weather_storm.wav", 0.45)
    sound_manager.load_sound("weather_thunder", assets_dir / "sounds" / "weather_thunder.wav", 0.6)

    # Sky: day/night cycle, clouds, weather
    sky = Sky(config, sound_manager, assets_dir)

    # Pickaxe
    pickaxe = Pickaxe(space, INTERNAL_WIDTH // 2, INTERNAL_HEIGHT // 2, texture_atlas.subsurface(atlas_items["pickaxe"]["wooden_pickaxe"]), sound_manager)

    # TNT
    last_tnt_spawn = pygame.time.get_ticks()
    tnt_spawn_interval = 1000 * random.uniform(config["TNT_SPAWN_INTERVAL_SECONDS_MIN"], config["TNT_SPAWN_INTERVAL_SECONDS_MAX"])
    tnt_list = []  # List to keep track of spawned TNT objects

    # Random Pickaxe
    last_random_pickaxe = pygame.time.get_ticks()
    random_pickaxe_interval = 1000 * random.uniform(config["RANDOM_PICKAXE_INTERVAL_SECONDS_MIN"], config["RANDOM_PICKAXE_INTERVAL_SECONDS_MAX"])

    # Pickaxe enlargement
    last_enlarge = pygame.time.get_ticks()
    enlarge_interval = 1000 * random.uniform(config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MIN"], config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MAX"])
    enlarge_duration = 1000 * config["PICKAXE_ENLARGE_DURATION_SECONDS"]

    # Fast (speed-up event; "Slow" was removed - it didn't feel good for viewers)
    fast_slow_active = False
    fast_slow = "Fast"
    fast_slow_interval = 1000 * random.uniform(config["FAST_SLOW_INTERVAL_SECONDS_MIN"], config["FAST_SLOW_INTERVAL_SECONDS_MAX"])
    last_fast_slow = pygame.time.get_ticks()

    # Star Boost (resource-multiplier power-up with a sparkle trail)
    star_boost_enabled = config.get("STAR_BOOST_ENABLED", True)
    star_boost_active = False
    star_boost_effect = None
    last_star_boost = pygame.time.get_ticks()
    star_boost_interval = 1000 * random.uniform(config.get("STAR_BOOST_INTERVAL_SECONDS_MIN", 25), config.get("STAR_BOOST_INTERVAL_SECONDS_MAX", 50))
    star_boost_duration = 1000 * config.get("STAR_BOOST_DURATION_SECONDS", 8)
    star_boost_multiplier = config.get("STAR_BOOST_MULTIPLIER", 2)

    # Pickaxe Rain (physical event: real pickaxes fall, pile up and help mine)
    pickaxe_rain_enabled = config.get("PICKAXE_RAIN_ENABLED", True)
    pickaxe_rain_active = False
    pickaxe_rain_effect = None
    last_pickaxe_rain = pygame.time.get_ticks()
    pickaxe_rain_interval = 1000 * random.uniform(config.get("PICKAXE_RAIN_INTERVAL_SECONDS_MIN", 20), config.get("PICKAXE_RAIN_INTERVAL_SECONDS_MAX", 45))
    pickaxe_rain_duration = 1000 * config.get("PICKAXE_RAIN_DURATION_SECONDS", 6)

    # Camera
    camera = Camera()

    # HUD
    hud = Hud(texture_atlas, atlas_items, config)

    # Explosions
    explosions = []

    # Youtube
    yt_poll_interval = 1000 * config["YT_POLL_INTERVAL_SECONDS"]
    last_yt_poll = pygame.time.get_ticks()

    # Save progress interval
    save_progress_interval = 1000 * config["SAVE_PROGRESS_INTERVAL_SECONDS"]
    last_save_progress = pygame.time.get_ticks()

    # Youtupe chat queues
    queues_pop_interval = 1000 * config["QUEUES_POP_INTERVAL_SECONDS"]
    last_queues_pop = pygame.time.get_ticks()

    # Main loop
    running = True
    user_quit = False
    while running:
        # ++++++++++++++++++  EVENTS ++++++++++++++++++
        for event in pygame.event.get():
            if event.type == pygame.QUIT:  # Close window event
                running = False
                user_quit = True
            elif event.type == pygame.VIDEORESIZE:  # Window resize event
                new_width, new_height = event.w, event.h

                # Maintain 9:16 aspect ratio
                if new_width / 9 > new_height / 16:
                    new_width = int(new_height * (9 / 16))
                else:
                    new_height = int(new_width * (16 / 9))

                window_width, window_height = new_width, new_height
                screen = pygame.display.set_mode((window_width, window_height), pygame.RESIZABLE)
                scaled_surface = pygame.Surface((window_width, window_height)).convert()

        # ++++++++++++++++++  UPDATE ++++++++++++++++++
        # Determine which chunks are visible
        # Update physics

        dt_ms = clock.get_time()
        current_time = pygame.time.get_ticks()

        step_speed = 1 / FRAMERATE  # Fixed time step for physics simulation
        if fast_slow_active and fast_slow == "Fast":
            step_speed = 1 / (FRAMERATE / 2)
        elif fast_slow_active and fast_slow == "Slow":
            step_speed = 1 / (FRAMERATE * 2)

        space.step(step_speed)

        start_chunk_y = int(pickaxe.body.position.y // (CHUNK_HEIGHT * BLOCK_SIZE) - 1) - 1
        end_chunk_y = int(pickaxe.body.position.y + INTERNAL_HEIGHT) // (CHUNK_HEIGHT * BLOCK_SIZE)  + 1

        # Update pickaxe
        pickaxe.update(current_time)

        # Update camera
        camera.update(pickaxe.body.position.y)

        # ++++++++++++++++++  DRAWING ++++++++++++++++++
        # Clear the internal surface
        screen.fill((0, 0, 0))

        # Sky: day/night cycle + clouds + weather timers (weather itself is drawn later, as an overlay)
        sky.update(dt_ms)

        if config.get("DAY_NIGHT_CYCLE_ENABLED", True) or config.get("CLOUDS_ENABLED", True):
            sky.draw_background(internal_surface)
        else:
            # Both dynamic-sky features are disabled in settings: fall back to the original static background
            internal_surface.blit(background_image, ((INTERNAL_WIDTH - background_width) // 2, (INTERNAL_HEIGHT - background_height) // 2))

        # Check if it's time to spawn a new TNT (regular random spawn)
        if (not config["CHAT_CONTROL"] or (not tnt_queue and not tnt_rain_queue and not super_tnt_queue and not tnt_superchat_queue and not mega_tnt_queue and not creeper_queue)) and current_time - last_tnt_spawn >= tnt_spawn_interval:
             # Example: spawn TNT at position (400, 300) with a given texture
             new_tnt = Tnt(space, pickaxe.body.position.x, pickaxe.body.position.y - 100,
               texture_atlas, atlas_items, sound_manager)
             tnt_list.append(new_tnt)
             last_tnt_spawn = current_time
             # New random interval for the next TNT spawn
             tnt_spawn_interval = 1000 * random.uniform(config["TNT_SPAWN_INTERVAL_SECONDS_MIN"], config["TNT_SPAWN_INTERVAL_SECONDS_MAX"])

        # Check if it's time to change the pickaxe (random)
        if (not config["CHAT_CONTROL"] or not pickaxe_queue) and current_time - last_random_pickaxe >= random_pickaxe_interval:
            pickaxe.random_pickaxe(texture_atlas, atlas_items)
            last_random_pickaxe = current_time
            # New random interval for the next pickaxe change
            random_pickaxe_interval = 1000 * random.uniform(config["RANDOM_PICKAXE_INTERVAL_SECONDS_MIN"], config["RANDOM_PICKAXE_INTERVAL_SECONDS_MAX"])

        # Check if it's time for pickaxe enlargement (random)
        if (not config["CHAT_CONTROL"] or not big_queue) and current_time - last_enlarge >= enlarge_interval:
            pickaxe.enlarge(enlarge_duration)
            last_enlarge = current_time + enlarge_duration
            # New random interval for the next enlargement
            enlarge_interval = 1000 * random.uniform(config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MIN"], config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MAX"])

        # Check if it's time for a speed-up event (random)
        if (not config["CHAT_CONTROL"] or not fast_slow_queue) and current_time - last_fast_slow >= fast_slow_interval and not fast_slow_active:
            fast_slow = "Fast"
            print("Changing speed to:", fast_slow)
            fast_slow_active = True
            last_fast_slow = current_time
            # New random interval for the next speed-up
            fast_slow_interval = 1000 * random.uniform(config["FAST_SLOW_INTERVAL_SECONDS_MIN"], config["FAST_SLOW_INTERVAL_SECONDS_MAX"])
        elif current_time - last_fast_slow >= (1000 * config["FAST_SLOW_DURATION_SECONDS"]) and fast_slow_active:
            fast_slow_active = False
            last_fast_slow = current_time

        # Check if it's time for a Star Boost event (random resource multiplier)
        if star_boost_enabled:
            if not star_boost_active and current_time - last_star_boost >= star_boost_interval:
                star_boost_active = True
                star_boost_effect = StarBoost(texture_atlas, atlas_items, multiplier=star_boost_multiplier)
                last_star_boost = current_time
                print("Starting Star Boost event")
            elif star_boost_active and current_time - last_star_boost >= star_boost_duration:
                star_boost_active = False
                star_boost_effect = None
                last_star_boost = current_time
                star_boost_interval = 1000 * random.uniform(config.get("STAR_BOOST_INTERVAL_SECONDS_MIN", 25), config.get("STAR_BOOST_INTERVAL_SECONDS_MAX", 50))
                print("Star Boost event ended")

        # Check if it's time for a Pickaxe Rain event (random, physical - the
        # dropped pickaxes fall, pile up and help mine nearby blocks)
        if pickaxe_rain_enabled:
            if not pickaxe_rain_active and current_time - last_pickaxe_rain >= pickaxe_rain_interval:
                pickaxe_rain_active = True
                pickaxe_rain_effect = PickaxeRain(
                    space, pickaxe.body.position.x, pickaxe.body.position.y,
                    texture_atlas, atlas_items, sound_manager,
                )
                last_pickaxe_rain = current_time
                print("Starting Pickaxe Rain event")
            elif pickaxe_rain_active and current_time - last_pickaxe_rain >= pickaxe_rain_duration:
                pickaxe_rain_active = False
                if pickaxe_rain_effect is not None:
                    pickaxe_rain_effect.end()
                pickaxe_rain_effect = None
                last_pickaxe_rain = current_time
                pickaxe_rain_interval = 1000 * random.uniform(config.get("PICKAXE_RAIN_INTERVAL_SECONDS_MIN", 20), config.get("PICKAXE_RAIN_INTERVAL_SECONDS_MAX", 45))
                print("Pickaxe Rain event ended")

        # Update all TNTs
        for tnt in tnt_list:
            tnt.update(tnt_list, explosions, camera, current_time)

        # Drain chat/subscriber queues (no network calls here - just reading what
        # the background chat/subscriber watcher threads already collected)
        if (chat_watcher is not None or subscriber_watcher is not None) and current_time - last_yt_poll >= yt_poll_interval:
            last_yt_poll = current_time
            handle_youtube_poll()

        # Process chat queues
        if config["CHAT_CONTROL"] and current_time - last_queues_pop >= queues_pop_interval:
            last_queues_pop = current_time

            # Handle regular TNT from chat command
            if tnt_queue:
                author = tnt_queue.popleft()
                tnt_queue_authors.discard(author)
                print(f"Spawning regular TNT for {author} (from chat command)")
                new_tnt = Tnt(space, pickaxe.body.position.x, pickaxe.body.position.y - 100,
                             texture_atlas, atlas_items, sound_manager, owner_name=author)
                tnt_list.append(new_tnt)
                last_tnt_spawn = current_time

            # Handle MegaTNT (New Subscriber)
            if mega_tnt_queue:
                author = mega_tnt_queue.popleft()
                print(f"Spawning MegaTNT for {author} (New Subscriber)")
                new_megatnt = MegaTnt(space, pickaxe.body.position.x, pickaxe.body.position.y - 100,
                      texture_atlas, atlas_items, sound_manager, owner_name=author)
                tnt_list.append(new_megatnt)
                last_tnt_spawn = current_time

            # Handle TNT Rain command (a shower of 3-8 regular TNT)
            if tnt_rain_queue:
                author = tnt_rain_queue.popleft()
                tnt_rain_authors.discard(author)
                rain_count = random.randint(3, 8)
                print(f"Spawning TNT Rain for {author} ({rain_count} TNT)")
                last_tnt_spawn = current_time
                for _ in range(rain_count):
                    new_tnt = Tnt(space, pickaxe.body.position.x, pickaxe.body.position.y - 100, texture_atlas, atlas_items, sound_manager, owner_name=author)
                    tnt_list.append(new_tnt)

            # Handle Super TNT command
            if super_tnt_queue:
                author = super_tnt_queue.popleft()
                super_tnt_authors.discard(author)
                print(f"Spawning Super TNT for {author}")
                new_super_tnt = SuperTnt(space, pickaxe.body.position.x, pickaxe.body.position.y - 100, texture_atlas, atlas_items, sound_manager, owner_name=author)
                tnt_list.append(new_super_tnt)
                last_tnt_spawn = current_time

            # Handle Creeper command (one falling creeper, explodes after 3s)
            if creeper_queue:
                author = creeper_queue.popleft()
                creeper_authors.discard(author)
                print(f"Spawning Creeper for {author}")
                new_creeper = Creeper(space, pickaxe.body.position.x, pickaxe.body.position.y - 100, texture_atlas, atlas_items, sound_manager, owner_name=author)
                tnt_list.append(new_creeper)
                last_tnt_spawn = current_time

            # Handle Superchat/Supersticker TNT
            if tnt_superchat_queue:
                author, text = tnt_superchat_queue.popleft()
                tnt_superchat_authors.discard(author)
                print(f"Spawning TNT for {author} (Superchat: {text})")
                last_tnt_spawn = current_time
                for _ in range(config["TNT_AMOUNT_ON_SUPERCHAT"]):
                    new_tnt = Tnt(space, pickaxe.body.position.x, pickaxe.body.position.y - 100, texture_atlas, atlas_items, sound_manager, owner_name=author)
                    tnt_list.append(new_tnt)

            # Handle Fast/Slow command
            if fast_slow_queue:
                author, q_fast_slow = fast_slow_queue.popleft()
                fast_slow_authors.discard(author)
                print(f"Changing speed for {author} to {q_fast_slow}")
                fast_slow_active = True
                last_fast_slow = current_time
                fast_slow = q_fast_slow
                fast_slow_interval = 1000 * random.uniform(config["FAST_SLOW_INTERVAL_SECONDS_MIN"], config["FAST_SLOW_INTERVAL_SECONDS_MAX"])

            # Handle Big pickaxe command
            if big_queue:
                author = big_queue.popleft()
                big_authors.discard(author)
                print(f"Making pickaxe big for {author}")
                pickaxe.enlarge(enlarge_duration)
                last_enlarge = current_time + enlarge_duration
                enlarge_interval = 1000 * random.uniform(config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MIN"], config["PICKAXE_ENLARGE_INTERVAL_SECONDS_MAX"])

            # Handle Pickaxe type command
            if pickaxe_queue:
                author, pickaxe_type = pickaxe_queue.popleft()
                pickaxe_authors.discard(author)
                print(f"Changing pickaxe for {author} to {pickaxe_type}")
                pickaxe.pickaxe(pickaxe_type, texture_atlas, atlas_items)
                last_random_pickaxe = current_time
                random_pickaxe_interval = 1000 * random.uniform(config["RANDOM_PICKAXE_INTERVAL_SECONDS_MIN"], config["RANDOM_PICKAXE_INTERVAL_SECONDS_MAX"])


        # Delete chunks
        clean_chunks(start_chunk_y, space)

        resource_multiplier = star_boost_multiplier if star_boost_active else 1

        # Draw blocks in visible chunks
        for chunk_x in range(-1, 2):
            for chunk_y in range(start_chunk_y, end_chunk_y):
                for y in range(CHUNK_HEIGHT):
                    for x in range(CHUNK_WIDTH):
                        block = get_block(chunk_x, chunk_y, x, y, texture_atlas, atlas_items, space)

                        if block == None:
                            continue

                        block.update(space, hud, current_time, resource_multiplier=resource_multiplier)
                        block.draw(internal_surface, camera)

        # Draw pickaxe
        pickaxe.draw(internal_surface, camera)

        # Draw TNT
        for tnt in tnt_list:
            tnt.draw(internal_surface, camera)

        # Draw Pickaxe Rain (physical pickaxes + their landing dust)
        if pickaxe_rain_active and pickaxe_rain_effect is not None:
            pickaxe_rain_effect.update(dt_ms)
            pickaxe_rain_effect.draw(internal_surface, camera)

        # Draw Star Boost sparkle trail
        if star_boost_active and star_boost_effect is not None:
            star_boost_effect.update(dt_ms, pickaxe.body.position.x, pickaxe.body.position.y)
            star_boost_effect.draw(internal_surface, camera)

        # Draw particles
        for explosion in explosions:
            explosion.update(dt_ms)
            explosion.draw(internal_surface, camera)

        # Optionally, remove explosions that have no particles left:
        explosions = [e for e in explosions if e.particles]

        # Draw weather overlay (rain/snow + lightning flash)
        sky.draw_foreground(internal_surface)

        # The HUD's "next event" box always tracks Pickaxe Rain - the one
        # event worth building anticipation for on stream.
        if pickaxe_rain_enabled:
            if pickaxe_rain_active:
                event_state = {
                    "active": True,
                    "name": "Pickaxe Rain",
                    "time_left": max(0.0, (pickaxe_rain_duration - (current_time - last_pickaxe_rain)) / 1000.0),
                    "duration": pickaxe_rain_duration / 1000.0,
                }
            else:
                event_state = {
                    "active": False,
                    "name": "Pickaxe Rain",
                    "next_in": max(0.0, (pickaxe_rain_interval - (current_time - last_pickaxe_rain)) / 1000.0),
                    "interval": pickaxe_rain_interval / 1000.0,
                }
        else:
            event_state = None

        # Draw HUD
        star_boost_state = None
        if star_boost_enabled:
            star_boost_state = {
                "active": star_boost_active,
                "multiplier": star_boost_multiplier,
                "time_left": max(0.0, (star_boost_duration - (current_time - last_star_boost)) / 1000.0) if star_boost_active else 0.0,
            }
        subscriber_count_text = subscriber_count_watcher.get_text() if subscriber_count_watcher is not None else None
        hud.draw(internal_surface, pickaxe.body.position.y, event_state, star_boost_state, subscriber_count_text)

        # Scale internal surface to fit the resized window
        pygame.transform.scale(internal_surface, (window_width, window_height), scaled_surface)
        screen.blit(scaled_surface, (0, 0))

        # Save progress
        if current_time - last_save_progress >= save_progress_interval:
            # Save the game state or progress here
            print("Saving progress...")
            last_save_progress = current_time
            # Save progress to logs folder
            log_dir = Path(__file__).parent.parent / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            with open(log_dir / "progress.txt", "a+") as f:
                f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')} | ")
                f.write(f"Y: {-int(pickaxe.body.position.y // BLOCK_SIZE)} ")
                f.write(f"coal: {hud.amounts['coal']} ")
                f.write(f"iron: {hud.amounts['iron_ingot']} ")
                f.write(f"gold: {hud.amounts['gold_ingot']} ")
                f.write(f"copper: {hud.amounts['copper_ingot']} ")
                f.write(f"redstone: {hud.amounts['redstone']} ")
                f.write(f"lapis: {hud.amounts['lapis_lazuli']} ")
                f.write(f"diamond: {hud.amounts['diamond']} ")
                f.write(f"emerald: {hud.amounts['emerald']} \n")

        # Update the display
        pygame.display.flip()
        clock.tick(FRAMERATE)  # Cap the frame rate

        # Inside the main loop
        keys = pygame.key.get_pressed()

        # Handle TNT spawn (key T)
        if keys[pygame.K_t]:
            if not key_t_pressed:  # Only spawn if the key was not pressed in the previous frame
                new_tnt = Tnt(space, pickaxe.body.position.x, pickaxe.body.position.y - 100,
                            texture_atlas, atlas_items, sound_manager)
                tnt_list.append(new_tnt)
                last_tnt_spawn = current_time
                # New random interval for the next TNT spawn
                tnt_spawn_interval = 1000 * random.uniform(config["TNT_SPAWN_INTERVAL_SECONDS_MIN"], config["TNT_SPAWN_INTERVAL_SECONDS_MAX"])
            key_t_pressed = True
        else:
            key_t_pressed = False  # Reset the flag when the key is released

        # Handle MegaTNT spawn (key M)
        if keys[pygame.K_m]:
            if not key_m_pressed:  # Only spawn if the key was not pressed in the previous frame
                new_megatnt = MegaTnt(space, pickaxe.body.position.x, pickaxe.body.position.y - 100,
                                    texture_atlas, atlas_items, sound_manager)
                tnt_list.append(new_megatnt)
                last_tnt_spawn = current_time
                # New random interval for the next TNT spawn
                tnt_spawn_interval = 1000 * random.uniform(config["TNT_SPAWN_INTERVAL_SECONDS_MIN"], config["TNT_SPAWN_INTERVAL_SECONDS_MAX"])
            key_m_pressed = True
        else:
            key_m_pressed = False  # Reset the flag when the key is released

    # Quit pygame properly
    pygame.quit()

    # Return exit code: 0 for user quit (close window), 1 for crash/error
    if user_quit:
        import sys
        sys.exit(0)  # Normal exit - user closed window
    else:
        import sys
        sys.exit(1)  # Abnormal exit - game crashed or error

pygame.init()
menu_action = run_main_menu(config)

if menu_action == "quit":
    pygame.quit()
    import sys
    sys.exit(0)

start_watchers()
game()
