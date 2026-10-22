import tkinter as tk
import customtkinter as ctk
import pymem
import pymem.process
import math
from enum import Enum
import win32gui as wg # pyright: ignore[reportMissingModuleSource]


# These may be changed
WINDOW_TITLE = "UNIB2 Trainer"
WINDOW_ALPHA = 0.9 # 0 = invincible, 1 = opaque
LABEL_VISIBLE = False # Whether to show values; does not affect Frame Data Bar
LABEL_FONT = ("Times New Roman", 25, "bold")
LABEL_PAD = (0, 0)
FDM_WIDTH = 120 # Number of squares per Frame Data Meter row; one square per frame
FDM_POSITION = [0, 0] # X-Y Coordinates of the Frame Data Meter
FDM_SQWIDTH = 14 # Pixel-width of each square
FDM_SQHEIGHT = 23 # Pixel-height of each square
FDM_YPAD = 5 # Pixels between top and bottom bars
FDM_XPAD = 1 # Pixels between each square in a row
FDM_BG = "#1A1A1A" # Background Color
FDM_C_NEXT = "#A5A0A0" # Color of the NEXT frame, overriding previous
FDM_C_EMPTY = "#4B4B4B" # Color of empty squares
FDM_C_STUN = "#AD2614" # Hitstun/Blockstun
FDM_C_ATK = "#0DE76F" # Attacking
FDM_C_ADV = "#1493B9" # At neutral while other is not


# These may be also changed, but be careful
REFRESH_MS = 15 # UI Frame Rate (milliseconds per refresh)
FDM_REFRESH_MS = 12 # Same but for FrameDataMeter
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



# Store all addresses in a unique class and call it "a"
class Addresses():
    # Universal Variables
    GRDCLOCK = [0x874FB0]

    # Player 1
    P1_HEALTH = [0xC6530C]
    P1_EXS = [0xC65330]
    P1_GRDSTOCKS = [0x874DD0]
    P1_GRDCURR = [0x874DD5]
    P1_CHAR = [0x5A4324]
    P1_VORPAL = [0x87A6B0]
    P1_VOTIME = [0xC6538C]

    # Player 2
    P2_HEALTH = [0xC65ECC]
    P2_EXS = [0xC65EF0]
    P2_GRDSTOCKS = [0x874F1C]
    P2_GRDCURR = [0x874F21]
    P2_CHAR = [0x5A4328]
    P2_VORPAL = [0x87A720]
    P2_VOTIME = [0xC65F4C]

    # Frame Data
    FD1_STARTUP = [0x87B4C4, [0x20]]
    FD1_TOTAL = [0x87B4C4, [0x24]]
    FD1_ADVANTAGE = [0x87B4C4, [0x30]]
    FD2_STARTUP = [0x87B4C4, [0x68]]
    FD2_TOTAL = [0x87B4C4, [0x6C]]
    FD2_ADVANTAGE = [0x87B4C4, [0x80]]

    # Combo Info
    DI_DAMAGE = [0x859B2C]
    DI_DAMAGE_BASIC = [0x859B30]
    DI_COMBO = [0x859B24]
    DI_COMBO_BASIC = [0x859B1C]
    DI_MAXCOMBO = [0x8776F4]
    DI_MAXCOMBO_BASIC = [0x859B1C]
    DI_HIT_PRORATION = [0x859B48]
    DI_HIT_DETERIORATION = [0x859B4C]
    DI_COMBO_PRORATION = [0x859B04]
    DI_COMBO_DETERIORATION = [0x859B14]

    # P1 States
    ST1_BUSY = [0xC65949]      # 0 when able to attack, 1 when unable
    ST1_ATTACKING = [0xC65734] # 0 when not attacking, 1 when attacking
    ST1_AIRBORNE = [0xC652EB]  # 0 when not airborne, 1 when airborne
    ST1_STUN_T = [0xC654A8] # Total hit-/block-stun imparted on this hit
    ST1_STUN_R = [0xC654A4] # Remaining hit-/block-stun before recovery

    # P2 States
    ST2_BUSY = [0xC66509]
    ST2_ATTACKING = [0xC662F4]
    ST2_STUN_T = [0xC66068]
    ST2_STUN_R = [0xC66064]


a = Addresses()


class FrameDataMeter(ctk.CTkFrame):

    def __init__(s, master, **kwargs):
        super().__init__(master, **kwargs)

        s.index = 0
        s.to_reset = False
        s.last_GRD_clock = g_int(a.GRDCLOCK) / 100

        width = FDM_WIDTH * (FDM_SQWIDTH + FDM_XPAD) - FDM_XPAD
        height = 2 * FDM_SQHEIGHT + FDM_YPAD

        s.canvas = tk.Canvas(
            s,
            width = width,
            height = height,
            bg = FDM_BG,
            highlightthickness = 0
        )

        s.canvas.pack(padx = 5, pady = 5)

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
            s.after(FDM_REFRESH_MS, s.fdm_update) #Run again on the next interval defined by REFRESH_MS

    def go(self): # Read all relevant values and update the frame data meter accordingly.
        un = self.updates_needed()
        for _ in range(un):
            p1_color = FDM_C_EMPTY # Update these
            p2_color = FDM_C_EMPTY
            skip = True

            # Player 1
            if g_int(a.ST1_ATTACKING) > 0:
                p1_color = FDM_C_ATK
                skip = False
            elif g_int(a.ST1_STUN_T) != 0:
                p1_color = FDM_C_STUN
                skip = False
            else:
                p1_color = FDM_C_ADV

            # Player 2
            if g_int(a.ST2_ATTACKING) > 0:
                p2_color = FDM_C_ATK
                skip = False
            elif g_int(a.ST2_STUN_T) != 0:
                p2_color = FDM_C_STUN
                skip = False
            else:
                p2_color = FDM_C_ADV


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

    def updates_needed(s): # Based on the GRD Clock, how many updates need to happen?
        grd_clock = math.floor(g_int(a.GRDCLOCK) / 100)
        result = 0
        if (s.last_GRD_clock <= grd_clock):
            result = int(grd_clock - s.last_GRD_clock)
        else:
            result = int(grd_clock + 780 - s.last_GRD_clock)
        s.last_GRD_clock = grd_clock
        if result > 1:
            print(f"RESULT {result} GREATER THAN 1 IN FrameDataMeter.updates_needed()! MAY HAVE INACCURATE DATA!")
        if result > 10:
            s.reset_fdm()
        return result


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

        s.make_labels()

        s.overlay_update()

        s.make_fdm()

        #end __init__()

    def make_fdm(s):
        s.fdm = FrameDataMeter(s)
        s.fdm.pack(side = "bottom")
        s.fdm.fdm_update()

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

            # Player Health
            val1 = int(g_int(a.P1_HEALTH))
            val2 = int(g_int(a.P2_HEALTH))
            next(s).configure(text = f"HEALTH: {val1} | {val2}")

            # Player EXS
            val1 = g_int(a.P1_EXS) / 100
            val2 = g_int(a.P2_EXS) / 100
            next(s).configure(text = f"EXS: {val1:.2f} | {val2:.2f}")

            # Player GRD
            val1 = g_int(a.P1_GRDSTOCKS) + g_int(a.P1_GRDCURR) / 100
            val2 = g_int(a.P2_GRDSTOCKS) + g_int(a.P2_GRDCURR) / 100
            next(s).configure(text = f"GRD: {val1:.2f} | {val2:.2f}")

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