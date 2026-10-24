import tkinter as tk
import customtkinter as ctk
import json
from pathlib import Path
import pymem
import pymem.process
import math
import win32event
import win32gui as wg # pyright: ignore[reportMissingModuleSource]
import time
import threading
import ctypes
from ctypes import wintypes



# THESE VARIABLES MAY BE CHANGED

JSON_FILENAME = "UNIB2.json" # Rename this if using a different json file; it must be in the same folder as this app
WINDOW_TITLE = "UNIB2 Trainer" # Rename this app's window (has no effect whatsoever)
WINDOW_ALPHA = 0.8 # The app's transparency (0 = invisible, 1 = opaque)

# top of screen
HD_HEIGHT = 125 # HP Display height below top of screen
# ----- middle of screen -----
FDM_HEIGHT = 10 # Frame Data Meter height above GRD Display
GD_HEIGHT = 65 # GRD Display height above bottom of screen
# bottom of screen

# Health Display - Show each character's current HP
HD_SPACING = 220 # Distance between HP values and the center of the screen
HD_FONT = ("Times New Roman", 32, "bold")

# GRD Display - Show each character's current GRD
GD_SPACING = 380 # Distance between GRD values and the center of the screen
GD_FONT = ("Times New Roman", 32, "bold")

FDM_WIDTH = 120 # IMPORTANT: Number of squares per Frame Data Meter row; one square per frame
FDM_SQWIDTH = 14 # Pixel-width of each square
FDM_SQHEIGHT = 23 # Pixel-height of each square
FDM_YPAD = 5 # Pixels between top and bottom bars
FDM_XPAD = 1 # Pixels between each square in a row
FDM_BORDERW = 7 # Border width around the Meter
FDM_HWIDTH = 2 # Outline Width
FDM_TEXTMIN = 5 # A number will appear over similar sets of consecutive frames of this count or higher
FDM_FONT = ("Times New Roman", 17, "bold") # Text of numerical representation of groups of same-colored frames
FDM_TEXT_OUTLINE_COLOR = "#000000"
FDM_TEXT_XOFFSET = -3 # Move the text this many pixels left/right
FDM_TEXT_YOFFSET = 0 # Move the text this many pixels up/down
FDM_OVERRIDE_BUFFER = 3 # As the meter draws over itself, text fields up to this number in the future will be hidden
FDM_HCOLOR = "#30179E" # Outline Color
FDM_BG = "#1A1A1A" # Background Color

FDM_C_NEXT          = "#A5A0A0" # Color of the NEXT frame, overriding previous color
FDM_C_EMPTY         = "#4B4B4B" # Color of empty squares
FDM_C_STUN          = "#990000" # Hitstun/Blockstun
FDM_C_ATK           = "#0DE76F" # Attacking
FDM_C_ADV           = "#1493B9" # At neutral while other is not
FDM_C_INVINCIBLE    = "#F1F1F1" # Invincible
FDM_C_SKIPPED       = "#5F130B" # This frame was skipped due to lag, so actual data is unknown
FDM_C_AIRBORNE      = "#FFFF00" # Jumping
FDM_C_BUSY          = "#682662" # Not neutral, attacking, or getting hit; Backdash, Assault, etc
FDM_C_ACTIVE        = "#FF0000" # Active Frames





# These may be also changed, but be careful
APP_CLOSE_CHECK_MS = 1000 # Check if should auto-close because the game is closed every this-many milliseconds
FDM_TEXT_OUTLINE_WIDTH = 1 # Looks pretty bad with values greater than 1.
REFRESH_MS = 15 # UI Frame Rate (milliseconds per refresh)
FDM_REFRESH_MS = 14 # Same but for FrameDataMeter (runs on a separate thread)
WINDOW_RESOLUTION = "1920x1080"
WINDOW_MINSIZE = [320, 240]
WINDOW_DRAGGABLE = False # Whether window is draggable; this disables transparency and auto-snapping
WINDOW_BG_TRANSPARENT = True
WINDOW_BG_TRANSPARENT_C = "#000055" # The window becomes this color, then is color-keyed out; it's not perfect
AUTOSNAP_POSITION = [0, 0] # Autosnap to this position, relative to the game window, if WINDOW_DRAGGABLE is False
LABEL_VISIBLE = False # Whether to show values; does not affect Frame Data Bar, primarily for debugging
LABEL_FONT = ("Times New Roman", 25, "bold")
LABEL_PAD = (0, 0)





# Probably never change these
EXECUTABLE_NAME = "uni2.exe"
WINDOW_NAME = "UNDER NIGHT IN-BIRTH II Sys:Celes"
pm = pymem.Pymem(EXECUTABLE_NAME)
module =  pymem.process.module_from_name(pm.process_handle, EXECUTABLE_NAME)
base_address = module.lpBaseOfDll
l = [] # Labels
i = -1 # Label indexing




# !!! VOODOO MAGIC ZONE - HANDLE WITH CAUTION !!!
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateWaitableTimerExW.restype = wintypes.HANDLE
kernel32.CreateWaitableTimerExW.argtypes = [
    wintypes.LPVOID,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    wintypes.DWORD,
]
kernel32.SetWaitableTimer.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(ctypes.c_longlong),
    wintypes.LONG,
    wintypes.LPVOID,
    wintypes.LPVOID,
    wintypes.BOOL,
]
kernel32.SetWaitableTimer.restype = wintypes.BOOL
kernel32.WaitForSingleObject.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
]
kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
def create_high_res_timer():
    timer = kernel32.CreateWaitableTimerExW(None, None, 0x00000002, 0x001F0003)
    if not timer:
        raise ctypes.WinError(ctypes.get_last_error())
    return timer
def wait_until(timer, deadline):
    remaining = deadline - time.perf_counter()
    if remaining <= 0:
        return
    due_time = ctypes.c_longlong(-max(1, int(remaining * 10_000_000)))
    if not kernel32.SetWaitableTimer(timer, ctypes.byref(due_time), 0, None, None, False):
        raise ctypes.WinError(ctypes.get_last_error())
    result = kernel32.WaitForSingleObject(timer, 0xFFFFFFFF)
    if result == 0xFFFFFFFF:
        raise ctypes.WinError(ctypes.get_last_error())
    if result != 0:
        raise RuntimeError(f"Unexpected timer wait result: {result}")
# !!! VOODOO MAGIC ZONE END !!!

# The app automatically closes if the game is not running
def game_is_running(pm):
    result = win32event.WaitForSingleObject(pm.process_handle, 0)
    return result == win32event.WAIT_TIMEOUT

# Auto-snapping
if not wg.FindWindow(None, WINDOW_NAME):
    print("Window Not Found! Auto-snapping requires the game to be open with its default name.")
    WINDOW_DRAGGABLE = True



# Store all addresses in a unique class and call it "a" (read from JSON file)

def convert_address(value):
    if isinstance(value, str):
        return int(value, 0)
    if isinstance(value, list):
        return [convert_address(item) for item in value]
    return value

class Addresses:
    def __init__(s, filename = JSON_FILENAME):

        script_dir = Path(__file__).resolve().parent
        file_path = script_dir / filename

        with open(file_path, "r", encoding = "utf-8") as file:
            raw_addresses = json.load(file)

        s.addresses = {
            name: convert_address(value)
            for name, value in raw_addresses.items()
        }

    def __getattr__(s, name):
        try:
            return s.addresses[name]
        except KeyError:
            raise AttributeError(
                f"Address {name} not found in JSON file!"
            ) from None

a = Addresses()




# Frame Data Meter

class FrameDataMeter(ctk.CTkFrame):

    def __init__(s, master, **kwargs):
        super().__init__(master, **kwargs)

        s.index = 0
        s.to_reset = False
        s.last_clock = g_int(a.MISCTIMER)
        s.utime = time.perf_counter() # used for timing the meter, so it updates as close to every frame as possible

        s.canvas = tk.Canvas(
            s,
            width = FDM_WIDTH * (FDM_SQWIDTH + FDM_XPAD) - FDM_XPAD,
            height = 2 * FDM_SQHEIGHT + FDM_YPAD,
            bg = FDM_BG,
            highlightthickness = FDM_HWIDTH,
            highlightbackground= FDM_HCOLOR
        )
        s.canvas.pack(padx = FDM_BORDERW, pady = FDM_BORDERW)

        s.p1_colors = [FDM_C_EMPTY] * FDM_WIDTH
        s.p2_colors = [FDM_C_EMPTY] * FDM_WIDTH
        s.indices_to_update = set()

        s.p1_rectangles = []
        s.p2_rectangles = []

        for i in range(FDM_WIDTH): # Frame Data Meter
            x = i * (FDM_SQWIDTH + FDM_XPAD)
            rect1 = s.canvas.create_rectangle(
                x, # Left
                0, # Top
                x + FDM_SQWIDTH, # Right
                FDM_SQHEIGHT, # Bot
                fill = FDM_C_EMPTY,
                outline = ""
            )
            s.p1_rectangles.append(rect1)
            rect2 = s.canvas.create_rectangle(
                x, # Left
                FDM_SQHEIGHT + FDM_YPAD, # Top
                x + FDM_SQWIDTH, # Right
                2 * FDM_SQHEIGHT + FDM_YPAD, # Bot
                fill = FDM_C_EMPTY,
                outline = ""
            )
            s.p2_rectangles.append(rect2)

        s.text_count = math.ceil(FDM_WIDTH / FDM_TEXTMIN)
        s.texts_to_hide = []
        s.p1_texts = [] # text instances
        s.p2_texts = []
        s.p1_text_vals = [0] * s.text_count # Value of texts in texts[]
        s.p2_text_vals = [0] * s.text_count
        s.p1_text_inds = [0] * s.text_count # index along FDM_WIDTH of texts in texts[]
        s.p2_text_inds = [0] * s.text_count
        s.p1_texts_need_update = set() # Whether each text in texts[] needs visually updated
        s.p2_texts_need_update = set()
        s.p1_last_text = 0 # index in texts[] of the last text instance updated
        s.p2_last_text = 0
        s.p1_last_color = FDM_C_EMPTY
        s.p2_last_color = FDM_C_EMPTY

        for i in range(s.text_count):
            for texts in [s.p1_texts, s.p2_texts]:
                texts.append({
                    "outline": [s.canvas.create_text(0,0,text="",fill="black",font=FDM_FONT,anchor="e",state="hidden")
                        for _ in range(8)],
                    "main": s.canvas.create_text(0,0,text="",fill="white",font=FDM_FONT,anchor="e",state="hidden")
                })

        s.indices_to_update = set() # these indexes in p#_colors and p#_rectangles need to have their UI updated

        # voodoo magic stuff used in collect_data()
        s.data_lock = threading.Lock()
        s.stop_event = threading.Event()
        s.worker = threading.Thread(
            target = s.collect_data,
            daemon=True
        )
        s.worker.start()

        s.update_FDM_UI() # Start the tkinter update loop

        # end __init__()

    def collect_data(s): # voodoo magic (aka multithreading); runs go() roughly 60 times per second
        interval = FDM_REFRESH_MS / 1000.0
        timer = create_high_res_timer()
        next_time = time.perf_counter()

        try:
            while not s.stop_event.is_set():
                try:
                    with s.data_lock:
                        s.go()
                except Exception as error:
                    print(f"ERR in FrameDataMeter.collect_data(): {error}")

                next_time += interval
                wait_until(timer, next_time)

                end = time.perf_counter()

                # Avoid attempting to catch up after a long delay.
                if end >= next_time + interval:
                    next_time = end
        finally:
            kernel32.CloseHandle(timer)

    def go(s): # Read all relevant values and update the frame data meter accordingly.
        un = s.updates_needed()
        for i in range(un):
            p1 = s.update_squares(True, i, un)
            p2 = s.update_squares(False, i, un)

            this_index = s.index

            p1_color = p1[0]
            p2_color = p2[0]
            skip = p1[1] and p2[1]

            if not skip:

                s.invalidate_texts_at_index(this_index)

                s.p1_colors[this_index] = p1_color
                s.p2_colors[this_index] = p2_color
                s.indices_to_update.add(this_index)

                s.index = this_index + 1
                if s.index >= FDM_WIDTH:
                    s.index = 0

                # Update Texts
                for player1 in (True, False):
                    last_color = s.p1_last_color if player1 else s.p2_last_color
                    color = p1_color if player1 else p2_color
                    text_inds = s.p1_text_inds if player1 else s.p2_text_inds
                    text_vals = s.p1_text_vals if player1 else s.p2_text_vals
                    text_index = s.p1_last_text if player1 else s.p2_last_text
                    texts_needs_update = (
                        s.p1_texts_need_update if player1
                        else s.p2_texts_need_update
                    )

                    if last_color == color:
                        text_inds[text_index] = this_index
                        text_vals[text_index] += 1
                        updated_text = text_index
                    else:
                        updated_text = (text_index + 1) % s.text_count
                        text_vals[updated_text] = 1
                        text_inds[updated_text] = this_index

                        if player1:
                            s.p1_last_text = updated_text
                        else:
                            s.p2_last_text = updated_text

                    texts_needs_update.add(updated_text)

                    if player1:
                        s.p1_last_color = color
                    else:
                        s.p2_last_color = color

                if s.to_reset:
                    s.reset_fdm()

            else:
                s.to_reset = True

            s.color_next_frames()

        # end go()

    def color_next_frames(s): # Colors the next frame's square, and resets the frame after that's square.
        next_index = s.index
        after_next = (s.index + 1) % FDM_WIDTH

        s.p1_colors[next_index] = FDM_C_NEXT
        s.p2_colors[next_index] = FDM_C_NEXT
        s.p1_colors[after_next] = FDM_C_EMPTY
        s.p2_colors[after_next] = FDM_C_EMPTY
        s.indices_to_update.add(next_index)
        s.indices_to_update.add(after_next)

    def stop_worker(s): # Close this when the game closes
        s.stop_event.set()
        if s.worker.is_alive():
            s.worker.join(timeout=1.0)

    def update_FDM_UI(s):
        try:
            with s.data_lock:
                indices = s.indices_to_update.copy()
                s.indices_to_update.clear()

                updates = [
                    (i, s.p1_colors[i], s.p2_colors[i])
                    for i in indices
                ]

            for i, p1_color, p2_color in updates:
                s.canvas.itemconfigure(s.p1_rectangles[i], fill = p1_color)
                s.canvas.itemconfigure(s.p2_rectangles[i], fill = p2_color)

            s.update_texts()

        except Exception as error:
            print(f"Memory read failed in FrameDataMeter.update_FDM_UI(): {error}")

        finally:
            s.after(REFRESH_MS, s.update_FDM_UI)
        # end update_FDM_UI

    def draw_outlined_text(s, text_items, x, y, val):
        offsets = [
            (-FDM_TEXT_OUTLINE_WIDTH, -FDM_TEXT_OUTLINE_WIDTH),
            (0, -FDM_TEXT_OUTLINE_WIDTH),
            (FDM_TEXT_OUTLINE_WIDTH, -FDM_TEXT_OUTLINE_WIDTH),
            (-FDM_TEXT_OUTLINE_WIDTH, 0),
            (FDM_TEXT_OUTLINE_WIDTH, 0),
            (-FDM_TEXT_OUTLINE_WIDTH, FDM_TEXT_OUTLINE_WIDTH),
            (0, FDM_TEXT_OUTLINE_WIDTH),
            (FDM_TEXT_OUTLINE_WIDTH, FDM_TEXT_OUTLINE_WIDTH)
        ]

        for item, (dx, dy) in zip(text_items["outline"], offsets):
            s.canvas.coords(item, x + dx, y + dy)
            s.canvas.itemconfig(item, text=str(val), state="normal")

        s.canvas.coords(text_items["main"], x, y)
        s.canvas.itemconfig(text_items["main"], text=str(val), state="normal")

    def hide_text_at_index(s, player1, fdm_index):
        text_inds = s.p1_text_inds if player1 else s.p2_text_inds
        texts_need_update = (s.p1_texts_need_update if player1 else s.p2_texts_need_update)
        texts_vals = s.p1_text_vals if player1 else s.p2_text_vals
        for ind, endpoint in enumerate(text_inds):
            if endpoint == fdm_index:
                texts_need_update.add(ind)
                texts_vals[ind] = 0
                return

    def invalidate_texts_at_index(s, fdm_index):
        for player1 in (True, False):
            text_inds = (s.p1_text_inds if player1 else s.p2_text_inds)
            text_vals = (s.p1_text_vals if player1 else s.p2_text_vals)
            texts_need_update = (s.p1_texts_need_update if player1 else s.p2_texts_need_update)

            for ind, endpoint in enumerate(text_inds):
                if text_vals[ind] > 0 and endpoint == fdm_index:
                    text_vals[ind] = 0
                    texts_need_update.add(ind)

    def update_texts(s): # A little bit of voodoo magic for the text elements
        with s.data_lock:
            updates = []

            for player1 in (True, False):
                texts = s.p1_texts if player1 else s.p2_texts
                text_inds = s.p1_text_inds if player1 else s.p2_text_inds
                text_vals = s.p1_text_vals if player1 else s.p2_text_vals
                colors = s.p1_colors if player1 else s.p2_colors
                pending = (s.p1_texts_need_update if player1 else s.p2_texts_need_update)

                for ind in pending:
                    fdm_index = text_inds[ind]
                    updates.append((texts[ind],fdm_index,text_vals[ind],colors[fdm_index],player1))

                pending.clear()

        for text, fdm_index, val, color, player1 in updates:
            y = (
                FDM_SQHEIGHT / 2 + FDM_TEXT_YOFFSET
                if player1
                else FDM_SQHEIGHT + FDM_YPAD + FDM_SQHEIGHT / 2 + FDM_TEXT_YOFFSET
            )

            if val > FDM_TEXTMIN and color != FDM_C_EMPTY:
                x = (
                    fdm_index * (FDM_SQWIDTH + FDM_XPAD) + FDM_SQWIDTH + FDM_TEXT_XOFFSET
                )
                s.draw_outlined_text(text, x, y, val)
            else:
                for item in text["outline"]:
                    s.canvas.itemconfig(item, state="hidden")
                s.canvas.itemconfig(text["main"], state="hidden")

    def update_squares(s, player1, i, un):

        if (i < un - 1) and not (s.to_reset):
            return [FDM_C_SKIPPED, False]
        elif g_int_1b(a.ST1_INVINC if player1 else a.ST2_INVINC) == 0:
            return [FDM_C_INVINCIBLE, False]
        elif g_int_1b(a.ST1_ACTIVE if player1 else a.ST2_ACTIVE) != 0:
            return [FDM_C_ACTIVE, False]
        elif g_int(a.ST1_ATTACKING if player1 else a.ST2_ATTACKING) > 0:
            return [FDM_C_ATK, False]
        elif g_int(a.ST1_STUN_T if player1 else a.ST2_STUN_T) != 0:
            return [FDM_C_STUN, False]
        elif g_int_1b(a.ST1_BUSY if player1 else a.ST2_BUSY) > 0:
            return [FDM_C_BUSY, False]
        elif g_int_1b(a.ST1_AIRBORNE if player1 else a.ST2_AIRBORNE) != 0:
            return [FDM_C_AIRBORNE, True]
        else:
            return [FDM_C_ADV, True]

    def reset_fdm(s):
        s.index = 0
        s.p1_colors = [FDM_C_EMPTY] * FDM_WIDTH
        s.p2_colors = [FDM_C_EMPTY] * FDM_WIDTH
        s.to_reset = False
        s.indices_to_update.update(range(FDM_WIDTH))
        s.p1_last_color = FDM_C_EMPTY
        s.p2_last_color = FDM_C_EMPTY
        s.p1_last_text = 0
        s.p2_last_text = 0
        s.p1_text_vals = [0] * s.text_count
        s.p2_text_vals = [0] * s.text_count
        s.p1_text_inds = [0] * s.text_count
        s.p2_text_inds = [0] * s.text_count
        for i in range(s.text_count):
            s.p1_texts_need_update.add(i)
            s.p2_texts_need_update.add(i)

    def updates_needed(s): # Based on the MISCTIMER, how many updates need to happen?
        clock = math.floor(g_int_1b(a.MISCTIMER))
        result = 0
        if (s.last_clock <= clock):
            result = int(clock - s.last_clock)
        else:
            result = int(clock + 256 - s.last_clock)
        s.last_clock = clock
        if result > 2 and clock > 7:
            print(f"Lag Detected at {clock}|{result}! Frame Data Meter may have an error!")
        if result > 10:
            s.reset_fdm()
            result = 1
        return result







# Data Overlay (top right)

class Overlay(ctk.CTk):

    def __init__(s):
        super().__init__()

        s.title(WINDOW_TITLE)
        s.geometry(WINDOW_RESOLUTION)
        s.minsize(WINDOW_MINSIZE[0], WINDOW_MINSIZE[1])
        s.attributes("-topmost", True, "-alpha", WINDOW_ALPHA) # Always on top
        s.overrideredirect(True) # Removes borders
        
        if WINDOW_DRAGGABLE:
            s.bind("<Button-1>", s.start_drag) # Drag when the mouse is held
            s.bind("<B1-Motion>", s.drag_window) # Move window when mouse is held and dragged
        else:
            s.auto_snap_update() # Auto-snap to the desired location relative to the game window

        if WINDOW_BG_TRANSPARENT and not WINDOW_DRAGGABLE:
            s.configure(fg_color=WINDOW_BG_TRANSPARENT_C)
            s.attributes("-transparentcolor", WINDOW_BG_TRANSPARENT_C)

        # From top of screen
        s.make_HD_display()
        s.make_labels()

        # From bottom of screen
        s.make_GRD_display()
        s.make_fdm()

        s.overlay_update()

        #end __init__()

    def make_fdm(s):
        s.fdm = FrameDataMeter(s)
        s.fdm.pack(side = "bottom", pady = FDM_HEIGHT)

    def make_GRD_display(s):
        s.GD_frame1 = ctk.CTkFrame(s, fg_color = "transparent")
        s.GD_frame1.pack(side="bottom")
        s.GD_frame2 = ctk.CTkFrame(s.GD_frame1, fg_color = "transparent")
        s.GD_frame2.pack(anchor="center", pady=(0, GD_HEIGHT))

        s.GD_left = ctk.CTkLabel(s.GD_frame2, font=GD_FONT)
        s.GD_left.pack(side="left", padx=(0, GD_SPACING))
        s.GD_right = ctk.CTkLabel(s.GD_frame2, font=GD_FONT)
        s.GD_right.pack(side="right")

    def make_HD_display(s):
        s.HD_frame1 = ctk.CTkFrame(s, fg_color = "transparent")
        s.HD_frame1.pack(side = "top")
        s.HD_frame2 = ctk.CTkFrame(s.HD_frame1, fg_color = "transparent")
        s.HD_frame2.pack(anchor="center", pady=(HD_HEIGHT, 0))

        s.HD_left = ctk.CTkLabel(s.HD_frame2, font = HD_FONT)
        s.HD_left.pack(side = "left", padx = (0, HD_SPACING))
        s.HD_right = ctk.CTkLabel(s.HD_frame2, font = HD_FONT)
        s.HD_right.pack(side = "right")

    def make_labels(s):
        num_labels = 20 # Can be higher than needed, but not lower
        s.l = [nl(s) for _ in range(num_labels)] # shoutouts to Google for fixing this...
        #end make_labels





    def update_labels(s):
        if LABEL_VISIBLE:
            s.i = -1

            # GRD Clock
            val1 = int(780 - g_int(a.GRDCLOCK) / 100)
            next(s).configure(text = f"GRD Clock: {val1}")

            # Player EXS
            val1 = g_int(a.P1_EXS) / 100
            val2 = g_int(a.P2_EXS) / 100
            next(s).configure(text = f"EXS: {val1:.2f} | {val2:.2f}")

            # Player Character
            val1 = get_char_name(g_int(a.P1_CHAR))
            val2 = get_char_name(g_int(a.P2_CHAR))
            next(s).configure(text = f"CHAR: {val1} | {val2}")

            # Player Vorpal
            val1 = g_int(a.P1_VORPAL)
            val2 = g_int(a.P2_VORPAL)
            next(s).configure(text = f"VORPAL: {
                (("Neither") if (val2 == 0) else ("P2"))
                if (val1 == 0) else
                (("P1") if (val2 == 0) else ("Both")) }"
            )

            # Player Veil Off timer
            val1 = int(g_int(a.P1_VOTIME) / 18)
            val2 = int(g_int(a.P2_VOTIME) / 18)
            next(s).configure(text = f"Veil Off: {val1} | {val2}")

            # P1 Frame Info - Startup
            val1 = g_int(a.FD1_STARTUP)
            next(s).configure(text = f"Startup: {val1}")

            # P1 Frame Info - Advantage
            val1 = g_int(a.FD1_ADVANTAGE)
            next(s).configure(text = f"Advantage: {val1}")

            # P1 Attacking
            val1 = g_int(a.ST1_ATTACKING)
            next(s).configure(text = f"Attacking: {val1}")

        #end update_labels

    def update_GD(s):
        p1_GRD = g_int(a.P1_GRDSTOCKS) + g_int(a.P1_GRDCURR) / 100
        p2_GRD = g_int(a.P2_GRDSTOCKS) + g_int(a.P2_GRDCURR) / 100
        s.GD_left .configure(text = f"{p1_GRD:.2f}")
        s.GD_right.configure(text = f"{p2_GRD:.2f}")


    def update_HD(s):
        s.HD_left .configure(text = f"{int(g_int(a.P1_HEALTH))}")
        s.HD_right.configure(text = f"{int(g_int(a.P2_HEALTH))}")
        



    # Make Window Draggable, unless auto-snap is enabled
    def start_drag(s, event): # Remember where the user clicked
        s.drag_x = event.x_root - s.winfo_x()
        s.drag_y = event.y_root - s.winfo_y()
    def drag_window(s, event): # Keep the window moving with the clicked cursor
        x = s.winfo_pointerx() - s.drag_x
        y = s.winfo_pointery() - s.drag_y
        s.geometry(f"+{x}+{y}")

    def auto_snap_update(s): # Auto-move the window to the target location
        x1, y1, x2, y2 = wg.GetClientRect(wg.FindWindow(None, WINDOW_NAME))
        s.geometry(f"+{x1 + AUTOSNAP_POSITION[0]}+{y1 + AUTOSNAP_POSITION[1]}")

    def overlay_update(s): #This is run every frame (defined by REFRESH_MS)
        try:
            s.update_labels()
            s.update_GD()
            s.update_HD()

        except Exception as error:
            print(f"Memory read failed: {error}")

        finally:
            s.after(REFRESH_MS, s.overlay_update) #Run again on the next interval defined by REFRESH_MS

    def check_game_process(s):
            if not game_is_running(pm):
                s.fdm.stop_worker()
                s.destroy()
                return
            s.after(APP_CLOSE_CHECK_MS, s.check_game_process)


# Get a value from memory
def g_int   (get): # 4 byte integer
    offsets = get[1] if len(get) > 1 else []
    base_offset = get[0]
    address = base_address + base_offset
    for o in offsets:
        address = pm.read_longlong(address) + o
    return pm.read_int(address)
def g_int_1b(get): # 1 byte integer
    offsets = get[1] if len(get) > 1 else []
    base_offset = get[0]
    address = base_address + base_offset
    for o in offsets:
        address = pm.read_longlong(address) + o
    return pm.read_uchar(address)
def g_int_2b(get): # 2 byte integer
    offsets = get[1] if len(get) > 1 else []
    base_offset = get[0]
    address = base_address + base_offset
    for o in offsets:
        address = pm.read_longlong(address) + o
    return pm.read_short(address)
def g_int_8b(get): # 8 byte integer
    offsets = get[1] if len(get) > 1 else []
    base_offset = get[0]
    address = base_address + base_offset
    for o in offsets:
        address = pm.read_longlong(address) + o
    return pm.read_longlong(address)
def g_float (get): # float
    offsets = get[1] if len(get) > 1 else []
    base_offset = get[0]
    address = base_address + base_offset
    for o in offsets:
        address = pm.read_longlong(address) + o
    return pm.read_float(address)
def g_double(get): # double
    offsets = get[1] if len(get) > 1 else []
    base_offset = get[0]
    address = base_address + base_offset
    for o in offsets:
        address = pm.read_longlong(address) + o
    return pm.read_double(address)

    
def get_char_name(integer_val): # Get a character's name based on their char index (0 -> "Hyde", etc.)
    match integer_val:
        case 0: return "Hyde"
        case 1: return "Linne"
        case 2: return "Waldstein"
        case 3: return "Carmine"
        case 4: return "Orie"
        case 5: return "Gordeau"
        case 6: return "Merkava"
        case 7: return "Vatista"
        case 8: return "Seth"
        case 9: return "Yuzuriha"
        case 10: return "Hilda"
        case 15: return "Chaos" # This is the training menu order, by the way...
        case 12: return "Nanase"
        case 13: return "Byakuya"
        case 24: return "Phonon"
        case 21: return "Mika"
        case 16: return "Wagner"
        case 17: return "Enkidu"
        case 18: return "Londrekia"
        case 19: return "Tsurugi"
        case 22: return "Kaguya"
        case 23: return "Kuon"
        case 20: return "Uzuki"
        case 25: return "Ogre"
        case 26: return "Izumi"
        case 11: return "Eltnum"
        case 14: return "Akatsuki"
    return "ERR IN GET_CHAR_NAME"


def nl(s): # New Label
        result = ctk.CTkLabel(s)
        result.pack(pady=(LABEL_PAD), anchor = "e")
        result.configure(text = "", font = LABEL_FONT)
        return result

def next(s):
    s.i = s.i + 1
    return s.l[s.i]



if __name__ == "__main__":
    app = Overlay()
    app.check_game_process()
    app.mainloop()