# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Key Bindings
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# --- Playback / navigation ---
KEY_PLAY        = 'space'
KEY_STEP_FWD    = 'Right'
KEY_STEP_BWD    = 'Left'

# --- Reset / camera ---
KEY_RESET_GROUP     = ['BackSpace']
KEY_CAM_RESET       = ['r', 'KP_0']
KEY_CENTER_VIEW     = 'KP_5'
KEY_CAM_PROJ        = 'c'
KEY_ROT_YL          = 'KP_4'
KEY_ROT_YR          = 'KP_6'
KEY_ROT_XD          = 'KP_2'
KEY_ROT_XU          = 'KP_8'
KEY_TRUCK_L         = 'KP_4'   # Ctrl+KP_4 → camera truck left
KEY_TRUCK_R         = 'KP_6'   # Ctrl+KP_6 → camera truck right
KEY_PEDESTAL_U      = 'KP_8'   # Ctrl+KP_8 → camera pedestal up
KEY_PEDESTAL_D      = 'KP_2'   # Ctrl+KP_2 → camera pedestal down
KEY_TURNTABLE       = 'KP_Decimal'  # auto-rotation toggle
TURNTABLE_ROT_STEP  = 5              # manual rotation step (degrees)

# --- Camera view presets ---
KEY_VIEW_FRONT   = 'F1'
KEY_VIEW_BACK    = 'F2'
KEY_VIEW_SIDE_L  = 'F3'
KEY_VIEW_SIDE_R  = 'F4'
KEY_VIEW_TOP     = 'F5'
KEY_VIEW_BOTTOM  = 'F6'
KEY_AXIS_SWAP    = 'Tab'  # model axis swap cycle (OFF → Y↔Z → X↔Z → X↔Y)

# --- KP camera zoom / dolly ---
KEY_KP_ZOOM_IN   = 'KP_7'
KEY_KP_ZOOM_OUT  = 'KP_9'
KEY_KP_DOLLY_IN  = 'KP_1'
KEY_KP_DOLLY_OUT = 'KP_3'

# --- Scene toggles ---
KEY_SCREENSHOT  = 'grave'          # ` → save screenshot
KEY_GRID        = '1'              # grid + bounding box toggle
KEY_BACKFACE    = 'b'
KEY_ACTOR_NEXT  = 'F12'           # cycle actor visibility
KEY_THEME       = 'F11'           # theme toggle (black ↔ white)
KEY_OVERLAY        = 'slash'       # / → show/hide all overlays
KEY_LOG_OVERLAY    = 'period'      # . → log overlay show/hide
KEY_STATUS_TEXT    = 'comma'       # , → status text show/hide
KEY_SEQ_OVERLAY    = 'apostrophe'  # ' → image sequence overlay show/hide
KEY_HELP        = 'h'

# --- Frame jump ---
KEY_FIRST_FRAME = 'Up'
KEY_LAST_FRAME  = 'Down'

# --- Render modes ---
KEY_MESH_DEFAULT    = 'q'
KEY_SMOOTH_SHADING  = 's'
KEY_VTX             = '2'
KEY_WIRE            = '3'
KEY_SMOOTH          = '4'
KEY_ISO             = '5'
KEY_LIGHT           = 'd'
KEY_NORMAL_COLOR    = '6'
KEY_MESH_QUALITY    = '7'
KEY_FACE_NORMAL     = '8'
KEY_DEPTH           = '9'
KEY_EDGE            = 'e'

# --- Parameter increment / axis cycle ---
KEY_INC         = 'KP_Add'       # context-dependent increment
KEY_DEC         = 'KP_Subtract'  # context-dependent decrement
KEY_AXIS_NEXT   = 'Next'         # PgDn: axis cycle forward
KEY_AXIS_PREV   = 'Prior'        # PgUp: axis cycle backward
