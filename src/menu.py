import sys

import pygame
from pathlib import Path

from config import save_config

# Windows' clipboard is ANSI-codepage text (not UTF-8) through pygame's scrap
# module, so Polish/special characters need the "mbcs" codec (Python's alias
# for "whatever the system's ANSI codepage is") to round-trip correctly.
_CLIPBOARD_ENCODING = "mbcs" if sys.platform == "win32" else "utf-8"
_scrap_ready = False


def _ensure_scrap():
    """Lazily initializes pygame's clipboard module. Returns False (instead of
    raising) if unavailable, so copy/paste just silently does nothing rather
    than crashing the settings screen."""
    global _scrap_ready
    if _scrap_ready:
        return True
    try:
        pygame.scrap.init()
        _scrap_ready = True
    except Exception:
        _scrap_ready = False
    return _scrap_ready


def _get_clipboard_text():
    if not _ensure_scrap():
        return ""
    try:
        raw = pygame.scrap.get(pygame.SCRAP_TEXT)
        if not raw:
            return ""
        text = raw.decode(_CLIPBOARD_ENCODING, errors="replace")
        # CF_TEXT-style clipboard data is NUL-terminated.
        return text.rstrip("\x00").replace("\r\n", " ").replace("\n", " ")
    except Exception:
        return ""


def _set_clipboard_text(text):
    if not _ensure_scrap():
        return
    try:
        pygame.scrap.put(pygame.SCRAP_TEXT, text.encode(_CLIPBOARD_ENCODING, errors="replace") + b"\x00")
    except Exception:
        pass

MENU_WIDTH, MENU_HEIGHT = 1000, 760

BG_COLOR = (18, 18, 26)
PANEL_COLOR = (32, 32, 44)
ROW_COLOR = (42, 42, 56)
ROW_ACTIVE_COLOR = (60, 90, 120)
ACCENT_COLOR = (90, 200, 255)
TEXT_COLOR = (235, 235, 240)
MUTED_COLOR = (150, 150, 160)
SECTION_COLOR = (255, 205, 90)

ROW_HEIGHT = 64
SECTION_HEIGHT = 40
CONTENT_TOP = 130
CONTENT_BOTTOM = MENU_HEIGHT - 80

# (config key, label, description, type) - type is "bool", "int", "float" or "str".
# Labels and descriptions are in Polish, since this screen replaces manually
# editing config.json for Polish-speaking streamers.
SETTINGS_SECTIONS = [
    ("Czat na YouTube (za darmo, bez klucza API)", [
        ("CHAT_CONTROL", "Sterowanie czatem", "Włącza komendy z czatu (tnt, rain, super, creeper, fast, big, nazwy kilofów) i superczaty.", "bool"),
        ("LIVESTREAM_ID", "Link / ID transmisji", "Link do Twojego live na YouTube albo samo ID filmu.", "str"),
        ("YOUTUBE_COOKIES_FILE", "Plik cookies YouTube (opcjonalnie)", "Ścieżka do pliku cookies.txt z zalogowanej przeglądarki - pomaga, gdy YouTube blokuje odczyt czatu.", "str"),
        ("YT_POLL_INTERVAL_SECONDS", "Odświeżanie czatu (s)", "Co ile sekund gra przetwarza nowe wiadomości z czatu.", "float"),
        ("QUEUES_POP_INTERVAL_SECONDS", "Obsługa kolejki komend (s)", "Co ile sekund wykonywana jest kolejna komenda z czatu.", "float"),
    ]),
    ("Subskrybenci (StreamElements, za darmo)", [
        ("SUBSCRIBER_ALERTS_ENABLED", "Alerty o nowych subskrybentach", "Spawnuje MegaTNT za każdego nowego subskrybenta.", "bool"),
        ("STREAMELEMENTS_CHANNEL_ID", "ID kanału StreamElements", "Znajdziesz je w ustawieniach konta StreamElements.", "str"),
        ("STREAMELEMENTS_JWT_TOKEN", "Token JWT StreamElements", "Token dostępowy z panelu StreamElements - traktuj jak hasło.", "str"),
    ]),
    ("Licznik subskrybentów (opcjonalny)", [
        ("SUBSCRIBER_COUNT_ENABLED", "Pokaż aktualną liczbę subskrybentów", "Osobna, opcjonalna opcja - pokazuje w HUD obecną łączną liczbę subskrybentów kanału (nie to samo co alerty o nowych subach).", "bool"),
        ("SUBSCRIBER_COUNT_CHANNEL_URL", "Kanał (link lub @nazwa)", "Np. @TwojaNazwa albo pełny link do kanału na YouTube - dane pobierane są za darmo z publicznej strony kanału.", "str"),
        ("SUBSCRIBER_COUNT_POLL_INTERVAL_SECONDS", "Odświeżanie licznika (s)", "Co ile sekund gra sprawdza aktualną liczbę subskrybentów.", "float"),
    ]),
    ("TNT i wydarzenia z kilofem", [
        ("TNT_SPAWN_INTERVAL_SECONDS_MIN", "Min. czas do TNT (s)", "Najkrótszy możliwy odstęp między losowymi TNT.", "float"),
        ("TNT_SPAWN_INTERVAL_SECONDS_MAX", "Maks. czas do TNT (s)", "Najdłuższy możliwy odstęp między losowymi TNT.", "float"),
        ("TNT_AMOUNT_ON_SUPERCHAT", "Ilość TNT za superczat", "Ile TNT spada za każdy Super Chat / Super Sticker.", "int"),
        ("FAST_SLOW_INTERVAL_SECONDS_MIN", "Min. czas do przyspieszenia (s)", "Najkrótszy odstęp między zdarzeniami przyspieszenia gry.", "float"),
        ("FAST_SLOW_INTERVAL_SECONDS_MAX", "Maks. czas do przyspieszenia (s)", "Najdłuższy odstęp między zdarzeniami przyspieszenia gry.", "float"),
        ("FAST_SLOW_DURATION_SECONDS", "Czas trwania przyspieszenia (s)", "Jak długo trwa przyspieszenie.", "float"),
        ("RANDOM_PICKAXE_INTERVAL_SECONDS_MIN", "Min. czas do losowego kilofa (s)", "Najkrótszy odstęp między losową zmianą kilofa.", "float"),
        ("RANDOM_PICKAXE_INTERVAL_SECONDS_MAX", "Maks. czas do losowego kilofa (s)", "Najdłuższy odstęp między losową zmianą kilofa.", "float"),
        ("PICKAXE_ENLARGE_INTERVAL_SECONDS_MIN", "Min. czas do powiększenia kilofa (s)", "Najkrótszy odstęp między powiększeniami kilofa.", "float"),
        ("PICKAXE_ENLARGE_INTERVAL_SECONDS_MAX", "Maks. czas do powiększenia kilofa (s)", "Najdłuższy odstęp między powiększeniami kilofa.", "float"),
        ("PICKAXE_ENLARGE_DURATION_SECONDS", "Czas trwania powiększenia (s)", "Jak długo kilof pozostaje powiększony.", "float"),
    ]),
    ("Deszcz Kilofów", [
        ("PICKAXE_RAIN_ENABLED", "Deszcz kilofów włączony", "Fizyczne kilofy spadają z góry, tworzą kupkę i pomagają kopać przez chwilę.", "bool"),
        ("PICKAXE_RAIN_INTERVAL_SECONDS_MIN", "Min. czas do deszczu kilofów (s)", "Najkrótszy odstęp między kolejnymi deszczami kilofów.", "float"),
        ("PICKAXE_RAIN_INTERVAL_SECONDS_MAX", "Maks. czas do deszczu kilofów (s)", "Najdłuższy odstęp między kolejnymi deszczami kilofów.", "float"),
        ("PICKAXE_RAIN_DURATION_SECONDS", "Czas trwania deszczu kilofów (s)", "Jak długo spadające kilofy pomagają kopać.", "float"),
    ]),
    ("Gwiazdka (boost surowców)", [
        ("STAR_BOOST_ENABLED", "Boost surowców włączony", "Na chwilę mnoży zdobywane surowce i dodaje efekt iskierek.", "bool"),
        ("STAR_BOOST_INTERVAL_SECONDS_MIN", "Min. czas do gwiazdki (s)", "Najkrótszy odstęp między kolejnymi boostami.", "float"),
        ("STAR_BOOST_INTERVAL_SECONDS_MAX", "Maks. czas do gwiazdki (s)", "Najdłuższy odstęp między kolejnymi boostami.", "float"),
        ("STAR_BOOST_DURATION_SECONDS", "Czas trwania boostu (s)", "Jak długo surowce są mnożone.", "float"),
        ("STAR_BOOST_MULTIPLIER", "Mnożnik surowców", "Np. 2 oznacza podwójne surowce podczas boostu.", "int"),
    ]),
    ("Niebo i pogoda", [
        ("DAY_NIGHT_CYCLE_ENABLED", "Cykl dnia i nocy", "Niebo w tle zmienia się od nocy przez wschód, dzień i zachód.", "bool"),
        ("DAY_NIGHT_CYCLE_SECONDS", "Długość pełnej doby (s)", "Ile sekund trwa cały cykl dzień-noc.", "float"),
        ("CLOUDS_ENABLED", "Ruchome chmury", "Chmury przesuwające się po niebie w tle.", "bool"),
        ("WEATHER_ENABLED", "Zmienna pogoda", "Krótkie, zmieniające się w tle opady deszczu, śniegu i burze z piorunami.", "bool"),
        ("WEATHER_CHANGE_INTERVAL_SECONDS_MIN", "Min. czas trwania pogody (s)", "Najkrótszy czas trwania danej pogody.", "float"),
        ("WEATHER_CHANGE_INTERVAL_SECONDS_MAX", "Maks. czas trwania pogody (s)", "Najdłuższy czas trwania danej pogody.", "float"),
    ]),
    ("HUD", [
        ("HUD_SHOW_NEXT_EVENT", "Pokaż licznik następnego wydarzenia", "Ramka z odliczaniem do Deszczu Kilofów.", "bool"),
        ("HUD_SHOW_COMMANDS", "Pokaż listę komend", "Panel z komendami czatu po prawej stronie ekranu.", "bool"),
        ("HUD_SHOW_ENGAGEMENT_BANNER", "Pokaż baner LIKE=TNT / SUB=NUKE", "Napis zachęcający widzów do polubienia i subskrypcji.", "bool"),
    ]),
    ("Inne", [
        ("SAVE_PROGRESS_INTERVAL_SECONDS", "Zapis postępu (s)", "Co ile sekund gra zapisuje głębokość i statystyki do logów.", "float"),
    ]),
]


def _parse_value(raw, ftype, fallback):
    try:
        if ftype == "int":
            return int(raw)
        elif ftype == "float":
            return float(raw)
        else:
            return raw
    except ValueError:
        return fallback


class _Button:
    def __init__(self, rect, label):
        self.rect = pygame.Rect(rect)
        self.label = label

    def draw(self, screen, font, hovered=False):
        color = ACCENT_COLOR if hovered else PANEL_COLOR
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), self.rect, width=2, border_radius=10)
        text = font.render(self.label, True, TEXT_COLOR)
        screen.blit(text, text.get_rect(center=self.rect.center))

    def hovered(self, pos):
        return self.rect.collidepoint(pos)


def _build_rows():
    """Flattens SETTINGS_SECTIONS into ("section", title) / ("field", key, label, description, ftype) rows."""
    rows = []
    for title, fields in SETTINGS_SECTIONS:
        rows.append(("section", title))
        for key, label, description, ftype in fields:
            rows.append(("field", key, label, description, ftype))
    return rows


_ROWS = _build_rows()


def _run_settings(screen, clock, config, title_font, font, small_font, tiny_font):
    working = dict(config)
    scroll_y = 0
    active_field = None
    input_buffer = ""

    save_button = _Button((MENU_WIDTH // 2 - 230, MENU_HEIGHT - 60, 220, 44), "ZAPISZ I WRÓĆ")
    cancel_button = _Button((MENU_WIDTH // 2 + 10, MENU_HEIGHT - 60, 220, 44), "WRÓĆ (odrzuć zmiany)")

    def commit_active_field():
        nonlocal active_field, input_buffer
        if active_field is None:
            return
        for row in _ROWS:
            if row[0] == "field" and row[1] == active_field:
                _, key, _label, _desc, ftype = row
                working[key] = _parse_value(input_buffer, ftype, working.get(key))
                break
        active_field = None
        input_buffer = ""

    def content_height():
        """Total height of all rows, independent of scroll offset."""
        height = 0
        for row in _ROWS:
            height += SECTION_HEIGHT if row[0] == "section" else ROW_HEIGHT
        return height

    def layout():
        """Returns a list of (row, y, row_rect, control_rect_or_None) for hit-testing/drawing."""
        layout_rows = []
        y = CONTENT_TOP - scroll_y
        for row in _ROWS:
            if row[0] == "section":
                layout_rows.append((row, y, pygame.Rect(40, y, MENU_WIDTH - 80, SECTION_HEIGHT - 6), None))
                y += SECTION_HEIGHT
            else:
                row_rect = pygame.Rect(40, y, MENU_WIDTH - 80, ROW_HEIGHT - 8)
                control_rect = pygame.Rect(MENU_WIDTH - 320, y + (ROW_HEIGHT - 8 - 36) // 2, 260, 36)
                layout_rows.append((row, y, row_rect, control_rect))
                y += ROW_HEIGHT
        return layout_rows

    running = True
    result = None
    while running:
        max_scroll = max(0, content_height() - (CONTENT_BOTTOM - CONTENT_TOP))
        scroll_y = max(0, min(max_scroll, scroll_y))
        rows_layout = layout()

        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                result = "quit"
                running = False
            elif event.type == pygame.MOUSEWHEEL:
                scroll_y = max(0, min(max_scroll, scroll_y - event.y * 40))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_pos = event.pos
                if save_button.hovered(click_pos):
                    commit_active_field()
                    config.clear()
                    config.update(working)
                    save_config()
                    result = "menu"
                    running = False
                    continue
                if cancel_button.hovered(click_pos):
                    result = "menu"
                    running = False
                    continue

                clicked_field = None
                for row, y, row_rect, control_rect in rows_layout:
                    if row[0] != "field":
                        continue
                    if not (CONTENT_TOP - 10 <= y <= CONTENT_BOTTOM):
                        continue
                    _, key, _label, _desc, ftype = row
                    if control_rect.collidepoint(click_pos):
                        clicked_field = (key, ftype)
                        break

                if clicked_field is not None:
                    key, ftype = clicked_field
                    if ftype == "bool":
                        working[key] = not bool(working.get(key, False))
                    else:
                        if active_field != key:
                            commit_active_field()
                            active_field = key
                            input_buffer = str(working.get(key, ""))
                else:
                    commit_active_field()
            elif event.type == pygame.KEYDOWN:
                if active_field is not None:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                        commit_active_field()
                    elif event.key == pygame.K_ESCAPE:
                        active_field = None
                        input_buffer = ""
                    elif event.key == pygame.K_BACKSPACE:
                        input_buffer = input_buffer[:-1]
                    elif event.key == pygame.K_v and (event.mod & pygame.KMOD_CTRL):
                        input_buffer += _get_clipboard_text()
                    elif event.key == pygame.K_c and (event.mod & pygame.KMOD_CTRL):
                        _set_clipboard_text(input_buffer)
                    elif event.key == pygame.K_x and (event.mod & pygame.KMOD_CTRL):
                        _set_clipboard_text(input_buffer)
                        input_buffer = ""
                    elif event.unicode and event.unicode.isprintable():
                        input_buffer += event.unicode
                elif event.key == pygame.K_ESCAPE:
                    result = "menu"
                    running = False

        if not running:
            break

        screen.fill(BG_COLOR)

        title_surface = title_font.render("USTAWIENIA", True, ACCENT_COLOR)
        screen.blit(title_surface, (40, 40))
        hint_surface = tiny_font.render("Kliknij pole, aby edytować - Enter zatwierdza - Ctrl+C/V/X kopiuje/wkleja/wycina - przewijaj kółkiem myszy", True, MUTED_COLOR)
        screen.blit(hint_surface, (40, 92))

        screen.set_clip(pygame.Rect(0, CONTENT_TOP - 10, MENU_WIDTH, CONTENT_BOTTOM - CONTENT_TOP + 20))
        for row, y, row_rect, control_rect in rows_layout:
            if y + ROW_HEIGHT < CONTENT_TOP - 60 or y > CONTENT_BOTTOM + 60:
                continue

            if row[0] == "section":
                section_surface = font.render(row[1], True, SECTION_COLOR)
                screen.blit(section_surface, (row_rect.x, row_rect.y))
                pygame.draw.line(screen, SECTION_COLOR, (row_rect.x, row_rect.bottom), (row_rect.right, row_rect.bottom), 1)
                continue

            _, key, label, description, ftype = row
            is_active = key == active_field

            pygame.draw.rect(screen, ROW_ACTIVE_COLOR if is_active else ROW_COLOR, row_rect, border_radius=8)

            label_surface = small_font.render(label, True, TEXT_COLOR)
            screen.blit(label_surface, (row_rect.x + 12, row_rect.y + 6))
            if description:
                desc_surface = tiny_font.render(description, True, MUTED_COLOR)
                # Leave room so the description never runs under the control widget
                max_desc_width = control_rect.x - (row_rect.x + 12) - 20
                if desc_surface.get_width() > max_desc_width > 0:
                    # Truncate with an ellipsis rather than overlapping the control
                    while desc_surface.get_width() > max_desc_width and len(description) > 1:
                        description = description[:-1]
                        desc_surface = tiny_font.render(description + "...", True, MUTED_COLOR)
                screen.blit(desc_surface, (row_rect.x + 12, row_rect.y + 6 + label_surface.get_height() + 2))

            if ftype == "bool":
                checked = bool(working.get(key, False))
                box_rect = pygame.Rect(control_rect.x, control_rect.y, control_rect.height, control_rect.height)
                pygame.draw.rect(screen, PANEL_COLOR, box_rect, border_radius=6)
                pygame.draw.rect(screen, ACCENT_COLOR if checked else MUTED_COLOR, box_rect, width=2, border_radius=6)
                if checked:
                    inner = box_rect.inflate(-10, -10)
                    pygame.draw.rect(screen, ACCENT_COLOR, inner, border_radius=4)
                state_text = tiny_font.render("WŁ" if checked else "WYŁ", True, ACCENT_COLOR if checked else MUTED_COLOR)
                screen.blit(state_text, (box_rect.right + 10, box_rect.y + (box_rect.height - state_text.get_height()) // 2))
            else:
                pygame.draw.rect(screen, PANEL_COLOR, control_rect, border_radius=8)
                pygame.draw.rect(screen, ACCENT_COLOR if is_active else MUTED_COLOR, control_rect, width=2, border_radius=8)
                value_text = input_buffer if is_active else str(working.get(key, ""))
                value_surface = tiny_font.render(value_text, True, TEXT_COLOR)

                # Long values (URLs, tokens) must never spill out of the box or off
                # the screen - clip to the control, and keep the tail (cursor end)
                # visible rather than the start, like a normal text input.
                inner_rect = control_rect.inflate(-16, -8)
                text_x = control_rect.x + 10
                if value_surface.get_width() > inner_rect.width:
                    text_x = control_rect.right - 10 - value_surface.get_width()

                screen.set_clip(inner_rect)
                screen.blit(value_surface, (text_x, control_rect.y + (control_rect.height - value_surface.get_height()) // 2))
                screen.set_clip(pygame.Rect(0, CONTENT_TOP - 10, MENU_WIDTH, CONTENT_BOTTOM - CONTENT_TOP + 20))

        screen.set_clip(None)

        save_button.draw(screen, tiny_font, hovered=save_button.hovered(mouse_pos))
        cancel_button.draw(screen, tiny_font, hovered=cancel_button.hovered(mouse_pos))

        pygame.display.flip()
        clock.tick(60)

    return result


def run_main_menu(config):
    """Shows the main menu (and, on request, the settings screen). Returns "play" or "quit".
    Any settings changes made are written both into the given config dict (in place) and to config.json.
    """
    screen = pygame.display.set_mode((MENU_WIDTH, MENU_HEIGHT))
    pygame.display.set_caption("Falling Pickaxe")

    icon_path = Path(__file__).parent / "assets" / "pickaxe" / "diamond_pickaxe.png"
    if icon_path.exists():
        pygame.display.set_icon(pygame.image.load(icon_path))

    clock = pygame.time.Clock()

    title_font = pygame.font.Font(None, 72)
    font = pygame.font.Font(None, 32)
    small_font = pygame.font.Font(None, 28)
    tiny_font = pygame.font.Font(None, 24)

    play_button = _Button((MENU_WIDTH // 2 - 150, 340, 300, 64), "GRAJ")
    settings_button = _Button((MENU_WIDTH // 2 - 150, 420, 300, 64), "USTAWIENIA")
    quit_button = _Button((MENU_WIDTH // 2 - 150, 500, 300, 64), "WYJŚCIE")

    state = "menu"

    while True:
        if state == "settings":
            result = _run_settings(screen, clock, config, title_font, font, small_font, tiny_font)
            if result == "quit":
                return "quit"
            state = "menu"
            screen = pygame.display.set_mode((MENU_WIDTH, MENU_HEIGHT))
            continue

        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_pos = event.pos
                if play_button.hovered(click_pos):
                    return "play"
                if settings_button.hovered(click_pos):
                    state = "settings"
                if quit_button.hovered(click_pos):
                    return "quit"
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "quit"

        screen.fill(BG_COLOR)
        title_surface = title_font.render("FALLING PICKAXE", True, ACCENT_COLOR)
        screen.blit(title_surface, title_surface.get_rect(center=(MENU_WIDTH // 2, 200)))
        subtitle_surface = small_font.render("Darmowa integracja z czatem YouTube - w pełni konfigurowalna w Ustawieniach", True, MUTED_COLOR)
        screen.blit(subtitle_surface, subtitle_surface.get_rect(center=(MENU_WIDTH // 2, 250)))

        play_button.draw(screen, font, hovered=play_button.hovered(mouse_pos))
        settings_button.draw(screen, font, hovered=settings_button.hovered(mouse_pos))
        quit_button.draw(screen, font, hovered=quit_button.hovered(mouse_pos))

        pygame.display.flip()
        clock.tick(60)
