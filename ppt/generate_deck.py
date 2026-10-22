import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml import parse_xml

# -------------------------------------------------------------
# Configuration & Colors
# -------------------------------------------------------------
BASE_DIR = r"d:\Mark-LV-main\ppt"
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_PPTX = os.path.join(BASE_DIR, "FRIDAY_MARK20_Showcase.pptx")

# Sci-Fi Cyber Palette
COLOR_BG_DARK = RGBColor(3, 7, 18)         # #030712
COLOR_CARD_BG = RGBColor(11, 20, 38)       # #0B1426
COLOR_CARD_BORDER = RGBColor(14, 116, 144)  # #0E7490
COLOR_CYAN = RGBColor(0, 242, 254)         # #00F2FE
COLOR_BLUE = RGBColor(79, 172, 254)        # #4FACFE
COLOR_GREEN = RGBColor(0, 245, 155)        # #00F59B
COLOR_AMBER = RGBColor(245, 158, 11)       # #F59E0B
COLOR_RED = RGBColor(239, 68, 68)          # #EF4444
COLOR_PURPLE = RGBColor(168, 85, 247)      # #A855F7
COLOR_WHITE = RGBColor(255, 255, 255)
COLOR_TEXT_MUTED = RGBColor(148, 163, 184) # #94A3B8

FONT_HEADING = "Segoe UI"
FONT_BODY = "Segoe UI"
FONT_MONO = "Consolas"

# -------------------------------------------------------------
# Helpers
# -------------------------------------------------------------
def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    return prs

def apply_slide_bg(slide):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = COLOR_BG_DARK

def add_slide_transition(slide, trans_type="fade", spd="med"):
    """
    Applies OpenXML slide transition: fade, wipe, push, zoom, etc.
    """
    if trans_type == "wipe":
        inner = '<p:wipe dir="r"/>'
    elif trans_type == "push":
        inner = '<p:push dir="l"/>'
    elif trans_type == "zoom":
        inner = '<p:zoom/>'
    else:
        inner = '<p:fade/>'

    xml = f'<p:transition xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" spd="{spd}">{inner}</p:transition>'
    slide._element.append(parse_xml(xml))

def add_entrance_animation(slide, shape, dur=500, delay=0):
    """
    Adds a fade entrance animation to the shape.
    """
    spid = shape._element.nvSpPr.cNvPr.id
    timing_xml = parse_xml(
        f'''<p:timing xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:tnLst>
    <p:par>
      <p:cTn id="1" dur="indefinite" restart="always" nodeType="tmRoot">
        <p:childTn>
          <p:seq concurrent="1" nextAc="seek">
            <p:cTn id="2" dur="indefinite" nodeType="mainSeq">
              <p:childTn>
                <p:par>
                  <p:cTn id="3" fill="hold">
                    <p:stCondLst>
                      <p:cond delay="{delay}"/>
                    </p:stCondLst>
                    <p:childTn>
                      <p:par>
                        <p:cTn id="4" fill="hold">
                          <p:stCondLst>
                            <p:cond delay="0"/>
                          </p:stCondLst>
                          <p:childTn>
                            <p:animEffect transition="in" filter="fade">
                              <p:cBhvr>
                                <p:cTn id="5" dur="{dur}"/>
                                <p:tgtEl>
                                  <p:spTgt spid="{spid}"/>
                                </p:tgtEl>
                              </p:cBhvr>
                            </p:animEffect>
                          </p:childTn>
                        </p:cTn>
                      </p:par>
                    </p:childTn>
                  </p:cTn>
                </p:par>
              </p:childTn>
            </p:cTn>
          </p:seq>
        </p:childTn>
      </p:cTn>
    </p:par>
  </p:tnLst>
</p:timing>'''
    )
    slide._element.append(timing_xml)

def add_header(slide, category, title, subtitle=None):
    # Category badge
    cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.5), Inches(0.35))
    tf_c = cat_box.text_frame
    tf_c.word_wrap = True
    tf_c.margin_left = tf_c.margin_right = tf_c.margin_top = tf_c.margin_bottom = 0
    p_c = tf_c.paragraphs[0]
    p_c.text = f"// {category.upper()}"
    p_c.font.size = Pt(11)
    p_c.font.name = FONT_MONO
    p_c.font.bold = True
    p_c.font.color.rgb = COLOR_CYAN

    # Title
    t_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.72), Inches(11.5), Inches(0.6))
    tf_t = t_box.text_frame
    tf_t.word_wrap = True
    tf_t.margin_left = tf_t.margin_right = tf_t.margin_top = tf_t.margin_bottom = 0
    p_t = tf_t.paragraphs[0]
    p_t.text = title
    p_t.font.size = Pt(24)
    p_t.font.name = FONT_HEADING
    p_t.font.bold = True
    p_t.font.color.rgb = COLOR_WHITE

    if subtitle:
        sub_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(11.5), Inches(0.35))
        tf_s = sub_box.text_frame
        tf_s.word_wrap = True
        tf_s.margin_left = tf_s.margin_right = tf_s.margin_top = tf_s.margin_bottom = 0
        p_s = tf_s.paragraphs[0]
        p_s.text = subtitle
        p_s.font.size = Pt(13)
        p_s.font.name = FONT_BODY
        p_s.font.color.rgb = COLOR_TEXT_MUTED

def add_card(slide, left, top, width, height, bg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1.2)
    else:
        shape.line.fill.background()
    return shape

# -------------------------------------------------------------
# SLIDE BUILDERS
# -------------------------------------------------------------

def build_slide_1(prs):
    """Slide 1: Title & Hero Cover"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    apply_slide_bg(slide)
    add_slide_transition(slide, "fade", "med")

    # Center Hero Card
    hero_card = add_card(slide, Inches(0.8), Inches(0.8), Inches(11.733), Inches(5.9),
                         bg_color=RGBColor(8, 14, 28), border_color=COLOR_CARD_BORDER)

    # Header banner image crop
    banner_img_path = os.path.join(ASSETS_DIR, "header_banner_clean.png")
    if os.path.exists(banner_img_path):
        slide.shapes.add_picture(banner_img_path, Inches(1.2), Inches(1.1), Inches(10.933), Inches(3.2))

    # Feature Badges
    badges = [
        ("🛡️ EDITH Security L4", COLOR_AMBER),
        ("⚡ Dev Agent Engine", COLOR_CYAN),
        ("📱 Mobile Web HUD", COLOR_PURPLE),
        ("🎭 3D Wireframe Avatar", COLOR_BLUE),
        ("🎙️ Real-Time Gemini Live", COLOR_GREEN),
    ]
    b_width = Inches(2.05)
    b_gap = Inches(0.18)
    start_x = Inches(1.2)
    b_y = Inches(4.55)

    for i, (text, col) in enumerate(badges):
        b_shape = add_card(slide, start_x + i * (b_width + b_gap), b_y, b_width, Inches(0.55),
                           bg_color=RGBColor(15, 23, 42), border_color=col)
        tf = b_shape.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.text = text
        p.alignment = PP_ALIGN.CENTER
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE

    # Author & Star Info
    auth_box = slide.shapes.add_textbox(Inches(1.2), Inches(5.4), Inches(10.933), Inches(0.8))
    tf_a = auth_box.text_frame
    tf_a.word_wrap = True
    p1 = tf_a.paragraphs[0]
    p1.text = "ENGINEERED WITH PASSION BY PRANAY GANDLEWAR"
    p1.alignment = PP_ALIGN.CENTER
    p1.font.size = Pt(13)
    p1.font.bold = True
    p1.font.name = FONT_HEADING
    p1.font.color.rgb = COLOR_CYAN

    p2 = tf_a.add_paragraph()
    p2.text = "Portfolio: pranay-portfoliio.vercel.app  •  Instagram: @mr.pranay_1101  •  Contact: pranay.tech.ai@gmail.com"
    p2.alignment = PP_ALIGN.CENTER
    p2.font.size = Pt(11)
    p2.font.name = FONT_BODY
    p2.font.color.rgb = COLOR_TEXT_MUTED

    add_entrance_animation(slide, hero_card, dur=600)
    return slide

def build_slide_2(prs):
    """Slide 2: Dual-Brain Intelligence & System Architecture"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    apply_slide_bg(slide)
    add_slide_transition(slide, "push", "med")
    add_header(slide, "System Architecture", "Dual-Brain Intelligence: Cloud Voice + Local Nervous System",
               "Designed for ultra-low latency conversational speed with deep hardware orchestration.")

    # 3 Pillar Cards
    pillars = [
        ("01", "Gemini Live Voice Brain", COLOR_CYAN, [
            "Bidirectional 16kHz audio streaming via WebSockets",
            "Sub-second response latency with natural turn-taking",
            "Multilingual fluency (fluent English, Hindi, and more)",
            "Speech interruption support with live hardware VAD"
        ]),
        ("02", "Autonomous Action Engine", COLOR_GREEN, [
            "Dynamic registry executing 20+ specialized system actions",
            "Full OS control: mouse, keyboard, brightness, process management",
            "Autonomous Dev Agent for writing & debugging codebase",
            "Local web browsing, video streaming & file indexing"
        ]),
        ("03", "Zero-Trust Safety & EDITH", COLOR_AMBER, [
            "E.D.I.T.H. 5-Tier risk analysis on every function call",
            "Hardware-gated screen confirmation for high-risk actions",
            "Full journaled undo operations for reversible mutations",
            "Air-gapped blocklist forbidding unauthorized destructive tools"
        ])
    ]

    card_w = Inches(3.6)
    card_h = Inches(4.5)
    gap = Inches(0.4)
    start_x = Inches(0.8)
    card_y = Inches(1.8)

    for i, (num, title, col, points) in enumerate(pillars):
        c_shape = add_card(slide, start_x + i * (card_w + gap), card_y, card_w, card_h,
                           bg_color=COLOR_CARD_BG, border_color=col)
        tf = c_shape.text_frame
        tf.word_wrap = True
        tf.margin_top = Inches(0.3)
        tf.margin_left = Inches(0.3)
        tf.margin_right = Inches(0.3)

        # Number & Category
        p_num = tf.paragraphs[0]
        p_num.text = f"// CORE PILLAR {num}"
        p_num.font.size = Pt(11)
        p_num.font.name = FONT_MONO
        p_num.font.bold = True
        p_num.font.color.rgb = col

        # Title
        p_tit = tf.add_paragraph()
        p_tit.text = title
        p_tit.font.size = Pt(18)
        p_tit.font.name = FONT_HEADING
        p_tit.font.bold = True
        p_tit.font.color.rgb = COLOR_WHITE
        p_tit.space_after = Pt(14)

        # Points
        for pt in points:
            p_pt = tf.add_paragraph()
            p_pt.text = f"▪  {pt}"
            p_pt.font.size = Pt(12)
            p_pt.font.name = FONT_BODY
            p_pt.font.color.rgb = COLOR_TEXT_MUTED
            p_pt.space_after = Pt(8)

    # Bottom Stat Bar
    stat_shape = add_card(slide, Inches(0.8), Inches(6.5), Inches(11.733), Inches(0.65),
                          bg_color=RGBColor(10, 18, 36), border_color=COLOR_CARD_BORDER)
    tf_stat = stat_shape.text_frame
    tf_stat.word_wrap = True
    tf_stat.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_s = tf_stat.paragraphs[0]
    p_s.text = "⚡ METRICS:  20+ Native Actions  |  < 800ms Latency  |  5 Security Risk Tiers  |  100% Offline HUD Telemetry"
    p_s.alignment = PP_ALIGN.CENTER
    p_s.font.size = Pt(12)
    p_s.font.name = FONT_MONO
    p_s.font.bold = True
    p_s.font.color.rgb = COLOR_CYAN

    return slide

def build_slide_3(prs):
    """Slide 3: Operations HUD — Real-Time Control Center (Using Screenshot 1)"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    apply_slide_bg(slide)
    add_slide_transition(slide, "wipe", "med")
    add_header(slide, "Live Operations", "Mission Control HUD: Real-Time Telemetry & Natural Conversation",
               "Full-screen cybernetic interface with active sensory feedback and telemetry monitoring.")

    # Left: Screenshot 1 (hud_ring_full.png)
    hud_img = os.path.join(ASSETS_DIR, "hud_ring_full.png")
    if os.path.exists(hud_img):
        # Card border behind image
        add_card(slide, Inches(0.75), Inches(1.75), Inches(6.4), Inches(4.8),
                 bg_color=RGBColor(5, 10, 20), border_color=COLOR_CYAN)
        slide.shapes.add_picture(hud_img, Inches(0.8), Inches(1.8), Inches(6.3), Inches(4.7))

    # Right: Detailed Feature Breakdown
    features = [
        ("Arc Reactor Visualizer", COLOR_CYAN,
         "Orbital concentric rings dynamically pulse and expand based on microphone input and speaker audio amplitude."),
        ("Multilingual Spoken Response", COLOR_GREEN,
         "Demonstrated natural Hindi conversation ('नमस्ते Pranay, 02:18 मिनट हो रहे हैं...') with zero manual language switching."),
        ("Hardware System Telemetry", COLOR_BLUE,
         "Real-time monitoring of CPU (19%), RAM (94%), Network I/O (1KB/s), GPU, and OS process count in the top-left monitor."),
        ("Automated News Aggregator", COLOR_AMBER,
         "Integrated scraping engine parsing top world headlines and displaying them in dedicated HUD widgets."),
        ("Hardware Control & Safety", COLOR_RED,
         "Instant physical controls: [F4] Mute, [F11] Fullscreen, [ESC] Interrupt speech, and active microphone status indicator.")
    ]

    r_x = Inches(7.4)
    r_w = Inches(5.1)
    card_h = Inches(0.9)
    gap = Inches(0.08)
    start_y = Inches(1.75)

    for i, (title, col, desc) in enumerate(features):
        c = add_card(slide, r_x, start_y + i * (card_h + gap), r_w, card_h,
                     bg_color=COLOR_CARD_BG, border_color=col)
        tf = c.text_frame
        tf.word_wrap = True
        tf.margin_top = Inches(0.12)
        tf.margin_left = Inches(0.2)
        tf.margin_right = Inches(0.2)

        p1 = tf.paragraphs[0]
        p1.text = f"▶  {title}"
        p1.font.size = Pt(13)
        p1.font.name = FONT_HEADING
        p1.font.bold = True
        p1.font.color.rgb = col

        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(10.5)
        p2.font.name = FONT_BODY
        p2.font.color.rgb = COLOR_TEXT_MUTED

    return slide

def build_slide_4(prs):
    """Slide 4: 3D Holographic Cybernetic Avatar (Using Screenshot 2)"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    apply_slide_bg(slide)
    add_slide_transition(slide, "fade", "med")
    add_header(slide, "AI Persona", "Living Persona: 3D Holographic Wireframe Facial Avatar",
               "Seamlessly morphs between Arc Reactor rings and an expressive 3D wireframe face mesh.")

    # Left: Screenshot 2 (hud_face_full.png)
    face_img = os.path.join(ASSETS_DIR, "hud_face_full.png")
    if os.path.exists(face_img):
        add_card(slide, Inches(0.75), Inches(1.75), Inches(6.4), Inches(4.8),
                 bg_color=RGBColor(5, 10, 20), border_color=COLOR_CYAN)
        slide.shapes.add_picture(face_img, Inches(0.8), Inches(1.8), Inches(6.3), Inches(4.7))

    # Right: Avatar Technology Stack
    avatar_points = [
        ("WebGL & Three.js Canvas", COLOR_CYAN,
         "Real-time polygonal mesh head modeled with futuristic cyan wireframes and deep ambient shading, rendered directly inside the GUI."),
        ("Audio-Driven Phoneme Lip Sync", COLOR_GREEN,
         "Voice output stream is split into amplitude and frequency bands to drive realistic procedural mouth open/close and articulation."),
        ("Dynamic Mode Switching", COLOR_BLUE,
         "Console log confirms: 'SYS: HUD switched to the animated face.' User can switch between minimalist ring and 3D face on command."),
        ("Emotive Cybernetic Optics", COLOR_AMBER,
         "Glowing green ocular nodes react to user gaze, processing states, and system notifications with realistic focus shifts."),
        ("Zero Performance Overhead", COLOR_PURPLE,
         "Lightweight geometry optimized to maintain 60 FPS animation without impacting background agent operations.")
    ]

    r_x = Inches(7.4)
    r_w = Inches(5.1)
    card_h = Inches(0.9)
    gap = Inches(0.08)
    start_y = Inches(1.75)

    for i, (title, col, desc) in enumerate(avatar_points):
        c = add_card(slide, r_x, start_y + i * (card_h + gap), r_w, card_h,
                     bg_color=COLOR_CARD_BG, border_color=col)
        tf = c.text_frame
        tf.word_wrap = True
        tf.margin_top = Inches(0.12)
        tf.margin_left = Inches(0.2)
        tf.margin_right = Inches(0.2)

        p1 = tf.paragraphs[0]
        p1.text = f"✦  {title}"
        p1.font.size = Pt(13)
        p1.font.name = FONT_HEADING
        p1.font.bold = True
        p1.font.color.rgb = col

        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(10.5)
        p2.font.name = FONT_BODY
        p2.font.color.rgb = COLOR_TEXT_MUTED

    return slide

def build_slide_5(prs):
    """Slide 5: Autonomous Action Ecosystem (Using Screenshot 3)"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    apply_slide_bg(slide)
    add_slide_transition(slide, "push", "med")
    add_header(slide, "Tool Ecosystem", "The 20+ Autonomous Action Suite",
               "Comprehensive suite of local system tools discovered dynamically at runtime.")

    # 4 Tool Columns matching the exact files shown in IDE screenshot
    categories = [
        ("System & Hardware", COLOR_CYAN, [
            ("computer_control.py", "Mouse, keyboard & display automation"),
            ("laptop_control.py", "Brightness, battery & sleep modes"),
            ("system_monitor.py", "CPU, RAM & GPU telemetry stream"),
            ("background_mon.py", "Proactive daemon & resource tracking")
        ]),
        ("Developer & Code", COLOR_GREEN, [
            ("dev_agent.py", "Autonomous coding agent & runner"),
            ("code_helper.py", "Syntax fixing, AST parsing & linting"),
            ("desktop.py", "Window tiling, workspace focus & apps"),
            ("open_app.py", "Instant launch for local applications")
        ]),
        ("Web & Intelligence", COLOR_BLUE, [
            ("web_search.py", "Multi-engine live search synthesis"),
            ("browser_control.py", "DOM extraction, clicks & web forms"),
            ("weather_report.py", "Meteorological forecasting & alerts"),
            ("flight_finder.py", "Live airfare & schedule lookup")
        ]),
        ("Media & Comms", COLOR_PURPLE, [
            ("youtube_video.py", "Direct video search & playback"),
            ("video_player.py", "Local MP4/MKV media player control"),
            ("send_message.py", "Automated WhatsApp & email dispatch"),
            ("reminder.py", "Natural language alarms & scheduling")
        ])
    ]

    col_w = Inches(2.7)
    gap = Inches(0.3)
    start_x = Inches(0.8)
    start_y = Inches(1.8)
    col_h = Inches(5.1)

    for i, (cat_name, col, tools) in enumerate(categories):
        card = add_card(slide, start_x + i * (col_w + gap), start_y, col_w, col_h,
                        bg_color=COLOR_CARD_BG, border_color=col)
        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_top = Inches(0.25)
        tf.margin_left = Inches(0.2)
        tf.margin_right = Inches(0.2)

        p_h = tf.paragraphs[0]
        p_h.text = f"// {cat_name.upper()}"
        p_h.font.size = Pt(13)
        p_h.font.name = FONT_HEADING
        p_h.font.bold = True
        p_h.font.color.rgb = col
        p_h.space_after = Pt(14)

        for t_file, t_desc in tools:
            p_f = tf.add_paragraph()
            p_f.text = f"• {t_file}"
            p_f.font.size = Pt(12)
            p_f.font.name = FONT_MONO
            p_f.font.bold = True
            p_f.font.color.rgb = COLOR_WHITE

            p_d = tf.add_paragraph()
            p_d.text = f"   {t_desc}"
            p_d.font.size = Pt(10)
            p_d.font.name = FONT_BODY
            p_d.font.color.rgb = COLOR_TEXT_MUTED
            p_d.space_after = Pt(8)

    return slide

def build_slide_6(prs):
    """Slide 6: Multi-Step Mission Planner (MARK 20 Innovation)"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    apply_slide_bg(slide)
    add_slide_transition(slide, "wipe", "med")
    add_header(slide, "Autonomous Planning", "Multi-Step Mission Planner Engine",
               "MARK 20's new high-order coordination engine for executing complex multi-action tasks.")

    # 5 Horizontal Pipeline Steps
    steps = [
        ("STEP A", "ANNOUNCE", COLOR_CYAN,
         "FRIDAY states one clear sentence naming all steps upfront before taking action."),
        ("STEP B", "REGISTER", COLOR_BLUE,
         "Registers ordered tool dependency graph and parameters in planner state machine."),
        ("STEP C", "EXECUTE LOOP", COLOR_GREEN,
         "Executes step-by-step: calls tool, inspects return value, and accumulates context."),
        ("STEP D", "EDITH GATE", COLOR_AMBER,
         "Every single step passes EDITH risk analysis; triggers hardware gate if Level 3+."),
        ("STEP E", "FINAL REPORT", COLOR_PURPLE,
         "Synthesizes natural conversational completion summary directly back to user.")
    ]

    card_w = Inches(2.15)
    card_h = Inches(3.2)
    gap = Inches(0.24)
    start_x = Inches(0.8)
    card_y = Inches(1.8)

    for i, (tag, name, col, desc) in enumerate(steps):
        c = add_card(slide, start_x + i * (card_w + gap), card_y, card_w, card_h,
                     bg_color=COLOR_CARD_BG, border_color=col)
        tf = c.text_frame
        tf.word_wrap = True
        tf.margin_top = Inches(0.25)
        tf.margin_left = Inches(0.18)
        tf.margin_right = Inches(0.18)

        p_t = tf.paragraphs[0]
        p_t.text = tag
        p_t.font.size = Pt(11)
        p_t.font.name = FONT_MONO
        p_t.font.bold = True
        p_t.font.color.rgb = col

        p_n = tf.add_paragraph()
        p_n.text = name
        p_n.font.size = Pt(16)
        p_n.font.name = FONT_HEADING
        p_n.font.bold = True
        p_n.font.color.rgb = COLOR_WHITE
        p_n.space_after = Pt(12)

        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(11)
        p_d.font.name = FONT_BODY
        p_d.font.color.rgb = COLOR_TEXT_MUTED

    # Bottom Example Scenario Card
    ex_card = add_card(slide, Inches(0.8), Inches(5.3), Inches(11.733), Inches(1.7),
                       bg_color=RGBColor(8, 16, 32), border_color=COLOR_CARD_BORDER)
    tf_ex = ex_card.text_frame
    tf_ex.word_wrap = True
    tf_ex.margin_top = Inches(0.2)
    tf_ex.margin_left = Inches(0.3)
    tf_ex.margin_right = Inches(0.3)

    p_et = tf_ex.paragraphs[0]
    p_et.text = "EXAMPLE MISSION:  \"Turn on Bluetooth, open Chrome, search for flight prices, and maximize the window.\""
    p_et.font.size = Pt(13)
    p_et.font.name = FONT_MONO
    p_et.font.bold = True
    p_et.font.color.rgb = COLOR_CYAN

    p_eb = tf_ex.add_paragraph()
    p_eb.text = "1. Announcement: \"I'm enabling Bluetooth, launching Chrome, checking flights, and maximizing your browser.\"\n" \
                "2. Context Passing: Chrome window handle from step 2 is automatically forwarded to the window maximizer in step 4.\n" \
                "3. Safe Recovery: If any intermediate step fails, execution halts cleanly and reports exact failure points."
    p_eb.font.size = Pt(11)
    p_eb.font.name = FONT_BODY
    p_eb.font.color.rgb = COLOR_TEXT_MUTED

    return slide

def build_slide_7(prs):
    """Slide 7: E.D.I.T.H. Security Policy Engine (Using Screenshot 4)"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    apply_slide_bg(slide)
    add_slide_transition(slide, "push", "med")
    add_header(slide, "Security & Safety", "E.D.I.T.H. Security Policy Engine",
               "Evaluation of Dangerous Operations, Intent & Risk Levels (Levels 0 to 4)")

    # Center Image: Clean cropped EDITH graphic
    edith_img = os.path.join(ASSETS_DIR, "edith_security_clean.png")
    if os.path.exists(edith_img):
        # Card border
        add_card(slide, Inches(0.75), Inches(1.75), Inches(11.833), Inches(3.6),
                 bg_color=RGBColor(5, 10, 20), border_color=COLOR_CARD_BORDER)
        slide.shapes.add_picture(edith_img, Inches(0.8), Inches(1.8), Inches(11.733), Inches(3.5))

    # Bottom 3 Safety Principles
    principles = [
        ("Zero Implicit Trust", COLOR_CYAN, "Every autonomous tool invocation undergoes parametric risk verification before code executes."),
        ("Hardware Screen Gate", COLOR_AMBER, "Dangerous actions (Level 3) pause execution until the physical user clicks confirmation on screen."),
        ("Transactional Rollbacks", COLOR_GREEN, "System mutations maintain undo journals, enabling instant voice rollback via \"undo that, Friday\".")
    ]

    p_w = Inches(3.6)
    p_gap = Inches(0.4)
    p_x = Inches(0.8)
    p_y = Inches(5.6)

    for i, (ptit, pcol, ptxt) in enumerate(principles):
        card = add_card(slide, p_x + i * (p_w + p_gap), p_y, p_w, Inches(1.4),
                        bg_color=COLOR_CARD_BG, border_color=pcol)
        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_top = Inches(0.18)
        tf.margin_left = Inches(0.2)
        tf.margin_right = Inches(0.2)

        p1 = tf.paragraphs[0]
        p1.text = f"🛡️  {ptit}"
        p1.font.size = Pt(13)
        p1.font.name = FONT_HEADING
        p1.font.bold = True
        p1.font.color.rgb = pcol

        p2 = tf.add_paragraph()
        p2.text = ptxt
        p2.font.size = Pt(11)
        p2.font.name = FONT_BODY
        p2.font.color.rgb = COLOR_TEXT_MUTED

    return slide

def build_slide_8(prs):
    """Slide 8: Cross-Platform & Mobile Ecosystem"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    apply_slide_bg(slide)
    add_slide_transition(slide, "fade", "med")
    add_header(slide, "Mobile Integration", "Cross-Platform Ecosystem: Remote Web HUD & Phone Mic Relay",
               "Control FRIDAY from anywhere on your local network using your smartphone or tablet.")

    # 3 Columns
    features = [
        ("Mobile Web Dashboard", COLOR_CYAN, [
            "Lightweight responsive Web HUD served via local HTTP daemon",
            "View live telemetry (CPU, RAM, Active Missions) from your phone",
            "Touch-optimized command buttons and interrupt triggers",
            "Zero app store installation required — runs in any mobile browser"
        ]),
        ("Phone Microphone Relay", COLOR_GREEN, [
            "Use your smartphone as a high-fidelity wireless microphone",
            "Encodes 16kHz PCM audio stream directly through WebSockets",
            "Talk to FRIDAY across rooms without buying dedicated hardware",
            "Low-latency packet transmission with automatic reconnects"
        ]),
        ("Distributed System Architecture", COLOR_BLUE, [
            "Desktop engine acts as central server coordinating clients",
            "Secured via local network authentication tokens",
            "Unified event dispatch syncing state across all connected screens",
            "Seamless fallback to local desktop mic when phone is idle"
        ])
    ]

    card_w = Inches(3.6)
    card_h = Inches(4.3)
    gap = Inches(0.4)
    start_x = Inches(0.8)
    card_y = Inches(1.8)

    for i, (title, col, points) in enumerate(features):
        c = add_card(slide, start_x + i * (card_w + gap), card_y, card_w, card_h,
                     bg_color=COLOR_CARD_BG, border_color=col)
        tf = c.text_frame
        tf.word_wrap = True
        tf.margin_top = Inches(0.3)
        tf.margin_left = Inches(0.25)
        tf.margin_right = Inches(0.25)

        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(17)
        p_t.font.name = FONT_HEADING
        p_t.font.bold = True
        p_t.font.color.rgb = col
        p_t.space_after = Pt(14)

        for pt in points:
            p_p = tf.add_paragraph()
            p_p.text = f"▪  {pt}"
            p_p.font.size = Pt(12)
            p_p.font.name = FONT_BODY
            p_p.font.color.rgb = COLOR_TEXT_MUTED
            p_p.space_after = Pt(8)

    # Bottom Protocol Callout
    proto_card = add_card(slide, Inches(0.8), Inches(6.3), Inches(11.733), Inches(0.8),
                          bg_color=RGBColor(8, 16, 32), border_color=COLOR_CARD_BORDER)
    tf_pr = proto_card.text_frame
    tf_pr.word_wrap = True
    tf_pr.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_pr = tf_pr.paragraphs[0]
    p_pr.text = "NETWORK STACK:  Python aiohttp WebSocket Server  •  16kHz PCM Binary Framing  •  mDNS Auto-Discovery  •  SSL/TLS Ready"
    p_pr.alignment = PP_ALIGN.CENTER
    p_pr.font.size = Pt(11)
    p_pr.font.name = FONT_MONO
    p_pr.font.color.rgb = COLOR_CYAN

    return slide

def build_slide_9(prs):
    """Slide 9: Engineering Stack & Benchmarks"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    apply_slide_bg(slide)
    add_slide_transition(slide, "push", "med")
    add_header(slide, "Specifications", "Engineering Specifications & Performance Benchmarks",
               "Architected for performance, stability, and modular extension.")

    # 4 Metric Cards
    metrics = [
        ("< 800 ms", "Voice Turn-Around Latency", COLOR_CYAN),
        ("20+ Tools", "Dynamic Action Registry", COLOR_GREEN),
        ("5 Levels", "E.D.I.T.H. Risk Hierarchy", COLOR_AMBER),
        ("Dual Mode", "Arc Reactor / 3D Avatar", COLOR_PURPLE),
    ]

    m_w = Inches(2.7)
    m_gap = Inches(0.3)
    m_x = Inches(0.8)
    m_y = Inches(1.8)

    for i, (val, label, col) in enumerate(metrics):
        mc = add_card(slide, m_x + i * (m_w + m_gap), m_y, m_w, Inches(1.6),
                      bg_color=COLOR_CARD_BG, border_color=col)
        tf = mc.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE

        p_v = tf.paragraphs[0]
        p_v.text = val
        p_v.alignment = PP_ALIGN.CENTER
        p_v.font.size = Pt(28)
        p_v.font.name = FONT_HEADING
        p_v.font.bold = True
        p_v.font.color.rgb = col

        p_l = tf.add_paragraph()
        p_l.text = label
        p_l.alignment = PP_ALIGN.CENTER
        p_l.font.size = Pt(11.5)
        p_l.font.name = FONT_BODY
        p_l.font.color.rgb = COLOR_WHITE

    # Lower Grid: Technology Details
    tech_grid = [
        ("Core Runtime", "Python 3.12, asyncio event loops, sounddevice PCM capture, Win32 API hooks."),
        ("AI Framework", "Google Gemini 2.0 Flash / Multimodal Live bidirectional streaming protocol."),
        ("HUD & Interface", "PyQt6 hardware-accelerated GUI, WebGL / Three.js 3D avatar canvas, QSS cyber theme."),
        ("Security Policy", "EDITH gatekeeper with risk scoring, action undo journaling, and process blacklists.")
    ]

    t_w = Inches(5.7)
    t_h = Inches(1.5)
    t_x1 = Inches(0.8)
    t_x2 = Inches(6.833)
    t_y1 = Inches(3.7)
    t_y2 = Inches(5.4)

    coords = [(t_x1, t_y1), (t_x2, t_y1), (t_x1, t_y2), (t_x2, t_y2)]

    for (layer, details), (cx, cy) in zip(tech_grid, coords):
        tc = add_card(slide, cx, cy, t_w, t_h, bg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER)
        tf = tc.text_frame
        tf.word_wrap = True
        tf.margin_top = Inches(0.2)
        tf.margin_left = Inches(0.25)
        tf.margin_right = Inches(0.25)

        p1 = tf.paragraphs[0]
        p1.text = f"⚙  {layer}"
        p1.font.size = Pt(14)
        p1.font.name = FONT_HEADING
        p1.font.bold = True
        p1.font.color.rgb = COLOR_CYAN

        p2 = tf.add_paragraph()
        p2.text = details
        p2.font.size = Pt(11.5)
        p2.font.name = FONT_BODY
        p2.font.color.rgb = COLOR_TEXT_MUTED

    return slide

def build_slide_10(prs):
    """Slide 10: Conclusion & Creator Connect"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    apply_slide_bg(slide)
    add_slide_transition(slide, "fade", "med")

    # Outer Showcase Card
    hero = add_card(slide, Inches(1.2), Inches(0.8), Inches(10.933), Inches(5.9),
                    bg_color=RGBColor(8, 14, 28), border_color=COLOR_CYAN)

    # Top Text Box (Title, Quote, Subtitle)
    top_box = slide.shapes.add_textbox(Inches(1.5), Inches(1.1), Inches(10.333), Inches(2.3))
    tf_top = top_box.text_frame
    tf_top.word_wrap = True
    tf_top.margin_left = tf_top.margin_right = tf_top.margin_top = tf_top.margin_bottom = 0

    p0 = tf_top.paragraphs[0]
    p0.text = "// THE FUTURE OF PERSONAL COMPUTING"
    p0.alignment = PP_ALIGN.CENTER
    p0.font.size = Pt(12)
    p0.font.name = FONT_MONO
    p0.font.bold = True
    p0.font.color.rgb = COLOR_CYAN
    p0.space_after = Pt(6)

    p1 = tf_top.add_paragraph()
    p1.text = "\"ALWAYS AT YOUR SERVICE, BOSS.\""
    p1.alignment = PP_ALIGN.CENTER
    p1.font.size = Pt(30)
    p1.font.name = FONT_HEADING
    p1.font.bold = True
    p1.font.color.rgb = COLOR_WHITE
    p1.space_after = Pt(10)

    p2 = tf_top.add_paragraph()
    p2.text = "FRIDAY bridges the frontier between cloud voice intelligence and deep desktop autonomy.\n" \
              "A truly personal AI assistant built for developers, creators, and power users."
    p2.alignment = PP_ALIGN.CENTER
    p2.font.size = Pt(13)
    p2.font.name = FONT_BODY
    p2.font.color.rgb = COLOR_TEXT_MUTED

    # Creator Info Card (Lower Half)
    cbox = add_card(slide, Inches(2.0), Inches(3.6), Inches(9.333), Inches(2.6),
                    bg_color=RGBColor(12, 22, 42), border_color=COLOR_BLUE)
    tf_c = cbox.text_frame
    tf_c.word_wrap = True
    tf_c.margin_top = Inches(0.25)
    tf_c.margin_left = Inches(0.4)
    tf_c.margin_right = Inches(0.4)

    pc1 = tf_c.paragraphs[0]
    pc1.text = "ENGINEERED WITH PASSION BY PRANAY GANDLEWAR"
    pc1.alignment = PP_ALIGN.CENTER
    pc1.font.size = Pt(15)
    pc1.font.name = FONT_HEADING
    pc1.font.bold = True
    pc1.font.color.rgb = COLOR_CYAN
    pc1.space_after = Pt(14)

    links = [
        "🌐  Portfolio:  https://pranay-portfoliio.vercel.app/",
        "📸  Instagram:  @mr.pranay_1101  •  https://www.instagram.com/mr.pranay_1101/",
        "📬  Email Contact:  pranay.tech.ai@gmail.com",
        "⭐  GitHub Repository:  pranaygandlewar/F.R.I.D.A.Y  (MARK 20)"
    ]

    for l in links:
        pl = tf_c.add_paragraph()
        pl.text = l
        pl.alignment = PP_ALIGN.CENTER
        pl.font.size = Pt(12)
        pl.font.name = FONT_BODY
        pl.font.color.rgb = COLOR_WHITE
        pl.space_after = Pt(6)

    return slide

# -------------------------------------------------------------
# Main Execution
# -------------------------------------------------------------
def main():
    print("Building FRIDAY MARK 20 Presentation Deck...")
    prs = create_deck()

    print("Adding Slide 1: Title & Hero...")
    build_slide_1(prs)

    print("Adding Slide 2: Dual-Brain Architecture...")
    build_slide_2(prs)

    print("Adding Slide 3: Operations HUD (Screenshot 1)...")
    build_slide_3(prs)

    print("Adding Slide 4: 3D Holographic Avatar (Screenshot 2)...")
    build_slide_4(prs)

    print("Adding Slide 5: Autonomous Action Ecosystem (Screenshot 3)...")
    build_slide_5(prs)

    print("Adding Slide 6: Multi-Step Mission Planner...")
    build_slide_6(prs)

    print("Adding Slide 7: EDITH Security Policy Engine (Screenshot 4)...")
    build_slide_7(prs)

    print("Adding Slide 8: Mobile Integration & Web HUD...")
    build_slide_8(prs)

    print("Adding Slide 9: Specifications & Benchmarks...")
    build_slide_9(prs)

    print("Adding Slide 10: Conclusion & Creator Connect...")
    build_slide_10(prs)

    prs.save(OUTPUT_PPTX)
    print(f"Deck saved successfully to: {OUTPUT_PPTX}")
    print(f"File size: {os.path.getsize(OUTPUT_PPTX)} bytes")

if __name__ == "__main__":
    main()
