import tkinter as tk
import customtkinter as ctk
import json
from pathlib import Path
import pymem
import pymem.process
import math
from enum import Enum
import win32gui as wg # pyright: ignore[reportMissingModuleSource]
import time


# THESE VARIABLES MAY BE CHANGED

# top of screen
HD_HEIGHT = 125 # HP Display height below top of screen
# ----- middle of screen -----
FDM_HEIGHT = 10 # Frame Data Meter height above GRD Display
GD_HEIGHT = 65 # GRD Display height above bottom of screen
# bottom of screen

JSON_FILENAME = "UNIB2.json"
WINDOW_TITLE = "UNIB2 Trainer"
WINDOW_ALPHA = 0.9

LABEL_VISIBLE = False # Whether to show values; does not affect Frame Data Bar
LABEL_FONT = ("Times New Roman", 25, "bold")
LABEL_PAD = (0, 0)

HD_SPACING = 220 # Distance between HP values
HD_FONT = ("Times New Roman", 32, "bold")

GD_SPACING = 380 # Distance between GRD values
GD_FONT = ("Times New Roman", 32, "bold")

FDM_WIDTH = 120 # IMPORTANT: Number of squares per Frame Data Meter row; one square per frame
FDM_SQWIDTH = 14 # Pixel-width of each square
FDM_SQHEIGHT = 23 # Pixel-height of each square
FDM_YPAD = 5 # Pixels between top and bottom bars
FDM_XPAD = 1 # Pixels between each square in a row
FDM_BORDERW = 7 # Border width around the Meter
FDM_HWIDTH = 2 # Outline Width
FDM_HCOLOR = "#30179E" # Outline Color

FDM_BG              = "#1A1A1A" # Background Color
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
REFRESH_MS = 32 # UI Frame Rate (milliseconds per refresh)
FDM_REFRESH_MS = 10 # Same but for FrameDataMeter
WINDOW_RESOLUTION = "1920x1080"
WINDOW_MINSIZE = [320, 240]
WINDOW_DRAGGABLE = False # Whether window is draggable; this disables transparency and auto-snapping
WINDOW_BG_TRANSPARENT = True
WINDOW_BG_TRANSPARENT_C = "#000000" # The window becomes this color, then is color-keyed out; it's not perfect
AUTOSNAP_POSITION = [0, 0] # Autosnap to this position, relative to the game window, if WINDOW_DRAGGABLE is False





# Probably never change these
EXECUTABLE_NAME = "uni2.exe"
WINDOW_NAME = "UNDER NIGHT IN-BIRTH II Sys:Celes"
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")
pm = pymem.Pymem(EXECUTABLE_NAME)
module =  pymem.process.module_from_name(pm.process_handle, EXECUTABLE_NAME)
base_address = module.lpBaseOfDll
l = [] # Labels
i = -1 # Label indexing








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
    def __init__(self, filename = JSON_FILENAME):

        script_dir = Path(__file__).resolve().parent
        file_path = script_dir / filename

        with open(file_path, "r", encoding = "utf-8") as file:
            raw_addresses = json.load(file)

        self.addresses = {
            name: convert_address(value)
            for name, value in raw_addresses.items()
        }

    def __getattr__(self, name):
        try:
            return self.addresses[name]
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



        s.p1_rectangles = []
        s.p2_rectangles = []

        # Frame Data Meter
        for i in range(FDM_WIDTH):
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

        # end __init__()


    def fdm_update(s):

        try:
            s.go()

        except Exception as error:
            print(f"Memory read failed in FrameDataMeter(): {error}")

        finally:
            new_time = time.perf_counter()
            elapsed_time = new_time - s.utime
            s.utime = new_time

            s.after(math.floor(max(1, FDM_REFRESH_MS - elapsed_time * 1000)), s.fdm_update)

    def go(self): # Read all relevant values and update the frame data meter accordingly.
        un = self.updates_needed()
        for i in range(un):
            p1 = self.update_squares(True, i, un)
            p2 = self.update_squares(False, i, un)
            p1_color = p1[0]
            p2_color = p2[0]
            skip = p1[1] and p2[1]

            # Update Canvas
            if not skip:
                if self.to_reset:
                    self.reset_fdm()

                self.canvas.itemconfigure(
                    self.p1_rectangles[self.index],
                    fill = p1_color
                )
                self.canvas.itemconfigure(
                    self.p2_rectangles[self.index],
                    fill = p2_color
                )

                self.index = self.index + 1
                if self.index >= FDM_WIDTH:
                    self.index = 0

            else:
                self.to_reset = True

            self.canvas.itemconfigure(
                self.p1_rectangles[self.index],
                fill = FDM_C_NEXT
            )
            self.canvas.itemconfigure(
                self.p2_rectangles[self.index],
                fill = FDM_C_NEXT
            )
            self.canvas.itemconfigure(
                self.p1_rectangles[(self.index + 1) % FDM_WIDTH],
                fill = FDM_C_EMPTY
            )
            self.canvas.itemconfigure(
                self.p2_rectangles[(self.index + 1) % FDM_WIDTH],
                fill = FDM_C_EMPTY
            )

        # end go()

    def update_squares(self, player1, i, un):

        if (i < un - 1) and not (self.to_reset):
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

    def reset_fdm(self):
        self.index = 0
        for i in range(FDM_WIDTH):
            self.canvas.itemconfigure(
                self.p1_rectangles[i],
                fill = FDM_C_EMPTY
            )
        for i in range(FDM_WIDTH):
            self.canvas.itemconfigure(
                self.p2_rectangles[i],
                fill = FDM_C_EMPTY
            )
        self.to_reset = False

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
        s.fdm.fdm_update()

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
    def start_drag(self, event): # Remember where the user clicked
        self.drag_x = event.x_root - self.winfo_x()
        self.drag_y = event.y_root - self.winfo_y()
    def drag_window(self, event): # Keep the window moving with the clicked cursor
        x = self.winfo_pointerx() - self.drag_x
        y = self.winfo_pointery() - self.drag_y
        self.geometry(f"+{x}+{y}")

    def auto_snap_update(self): # Auto-move the window to the target location
        x1, y1, x2, y2 = wg.GetClientRect(wg.FindWindow(None, WINDOW_NAME))
        self.geometry(f"+{x1 + AUTOSNAP_POSITION[0]}+{y1 + AUTOSNAP_POSITION[1]}")

    def overlay_update(self): #This is run every frame (defined by REFRESH_MS)
        try:
            self.update_labels()
            self.update_GD()
            self.update_HD()

        except Exception as error:
            print(f"Memory read failed: {error}")

        finally:
            self.after(REFRESH_MS, self.overlay_update) #Run again on the next interval defined by REFRESH_MS


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


def nl(self): # New Label
        result = ctk.CTkLabel(self)
        result.pack(pady=(LABEL_PAD), anchor = "e")
        result.configure(text = "", font = LABEL_FONT)
        return result

def next(s):
    s.i = s.i + 1
    return s.l[s.i]



if __name__ == "__main__":
    app = Overlay()
    app.mainloop()