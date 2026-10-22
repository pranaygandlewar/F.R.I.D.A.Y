import os
import win32com.client

RAW_PPTX = r"d:\Mark-LV-main\ppt\deck_raw.pptx"
FINAL_PPTX = r"d:\Mark-LV-main\ppt\FRIDAY_MARK20_Showcase.pptx"

# Transition Constants
TRANS_FADE = 3849       # ppEffectFadeSmoothly
TRANS_PUSH_L = 3853     # ppEffectPushLeft
TRANS_PUSH_R = 3854     # ppEffectPushRight
TRANS_PUSH_U = 3855     # ppEffectPushUp
TRANS_WIPE_R = 3856     # ppEffectWipeRight
TRANS_WIPE_L = 3857     # ppEffectWipeLeft
TRANS_COVER_L = 1281    # ppEffectCoverLeft

# Animation Effect Constants
ANIM_ZOOM = 23          # msoAnimEffectZoom
ANIM_FLY = 2            # msoAnimEffectFly
ANIM_FADE = 10          # msoAnimEffectFade
ANIM_FLOAT = 30         # msoAnimEffectFloat
ANIM_GROW_SHRINK = 59   # msoAnimEffectGrowShrink
ANIM_BOUNCE = 26        # msoAnimEffectBounce

# Animation Trigger Constants
TRIG_ON_CLICK = 1       # msoAnimTriggerOnPageClick
TRIG_WITH_PREV = 2      # msoAnimTriggerWithPrevious
TRIG_AFTER_PREV = 3     # msoAnimTriggerAfterPrevious

def animate_deck():
    print("Connecting to Microsoft PowerPoint Application...")
    ppt = win32com.client.Dispatch('PowerPoint.Application')
    pres = ppt.Presentations.Open(RAW_PPTX, WithWindow=False)
    total_slides = pres.Slides.Count
    print(f"Opened deck with {total_slides} slides.")

    # -------------------------------------------------------------
    # SLIDE 1: Hero & Identity
    # Transition: Smooth Cinematic Fade
    # Animations:
    # 1. Hero Card: Zoom in (TRIG_ON_CLICK)
    # 2. Banner Picture: Float in (TRIG_AFTER_PREV)
    # 3. Badges (Shapes 3-7): Bounce in sequentially (TRIG_AFTER_PREV)
    # -------------------------------------------------------------
    s1 = pres.Slides(1)
    s1.SlideShowTransition.EntryEffect = TRANS_FADE
    s1.SlideShowTransition.Duration = 1.0
    seq1 = s1.TimeLine.MainSequence

    # Shape 1: Hero Card -> Zoom In
    e = seq1.AddEffect(s1.Shapes(1), ANIM_ZOOM, 0, TRIG_ON_CLICK)
    e.Timing.Duration = 0.75

    # Shape 2: Header Banner Image -> Float In
    if s1.Shapes.Count >= 2:
        e = seq1.AddEffect(s1.Shapes(2), ANIM_FLOAT, 0, TRIG_AFTER_PREV)
        e.Timing.Duration = 0.6

    # Shapes 3-7: Badges -> Fly in from bottom sequentially
    for shp_idx in range(3, min(8, s1.Shapes.Count + 1)):
        e = seq1.AddEffect(s1.Shapes(shp_idx), ANIM_FLY, 0, TRIG_AFTER_PREV)
        e.Timing.Duration = 0.35
        e.EffectParameters.Direction = 4 # from bottom

    # Shape 8: Author Footer -> Fade In
    if s1.Shapes.Count >= 8:
        e = seq1.AddEffect(s1.Shapes(8), ANIM_FADE, 0, TRIG_AFTER_PREV)
        e.Timing.Duration = 0.5

    print("Animated Slide 1: Hero Cover.")

    # -------------------------------------------------------------
    # SLIDE 2: Architecture & Core Pillars
    # Transition: Push Left
    # Animations:
    # Pillar Cards 1, 2, 3 -> Fly in from Right on Click, then with prev
    # -------------------------------------------------------------
    s2 = pres.Slides(2)
    s2.SlideShowTransition.EntryEffect = TRANS_PUSH_L
    s2.SlideShowTransition.Duration = 0.7
    seq2 = s2.TimeLine.MainSequence

    # Shape 1, 2: Header -> Fade In
    seq2.AddEffect(s2.Shapes(1), ANIM_FADE, 0, TRIG_ON_CLICK).Timing.Duration = 0.4
    seq2.AddEffect(s2.Shapes(2), ANIM_FLOAT, 0, TRIG_WITH_PREV).Timing.Duration = 0.5

    # Shapes 4, 5, 6: The 3 Pillar Cards
    for idx, shp_idx in enumerate([4, 5, 6]):
        if shp_idx <= s2.Shapes.Count:
            trig = TRIG_ON_CLICK if idx == 0 else TRIG_AFTER_PREV
            e = seq2.AddEffect(s2.Shapes(shp_idx), ANIM_ZOOM, 0, trig)
            e.Timing.Duration = 0.5

    # Bottom Metrics Bar
    if s2.Shapes.Count >= 7:
        seq2.AddEffect(s2.Shapes(7), ANIM_FLY, 0, TRIG_AFTER_PREV).Timing.Duration = 0.4

    print("Animated Slide 2: System Architecture.")

    # -------------------------------------------------------------
    # SLIDE 3: Operations HUD (Full Screen 1)
    # Transition: Wipe Right
    # Animations:
    # Full HUD Image -> Zoom In prominently
    # Feature Callouts -> Float in sequentially
    # -------------------------------------------------------------
    s3 = pres.Slides(3)
    s3.SlideShowTransition.EntryEffect = TRANS_WIPE_R
    s3.SlideShowTransition.Duration = 0.8
    seq3 = s3.TimeLine.MainSequence

    # Shape 5: HUD Screenshot -> Dramatic Zoom In!
    if s3.Shapes.Count >= 5:
        e = seq3.AddEffect(s3.Shapes(5), ANIM_ZOOM, 0, TRIG_ON_CLICK)
        e.Timing.Duration = 0.8

    # Feature Cards (Shapes 6-10) -> Fly in from right on clicks / after
    for idx, shp_idx in enumerate(range(6, min(11, s3.Shapes.Count + 1))):
        trig = TRIG_AFTER_PREV if idx > 0 else TRIG_AFTER_PREV
        e = seq3.AddEffect(s3.Shapes(shp_idx), ANIM_FLY, 0, trig)
        e.Timing.Duration = 0.35
        e.EffectParameters.Direction = 2 # from right

    print("Animated Slide 3: Operations HUD Overview.")

    # -------------------------------------------------------------
    # SLIDE 4: ZOOM IN — Arc Reactor & Telemetry
    # Transition: Fast Zoom Transition (simulated via Wipe / Push)
    # Animations:
    # Reactor Crop -> Dynamic Zoom-In
    # Telemetry Crop -> Fly In from left
    # Deep dive cards -> Pop in
    # -------------------------------------------------------------
    s4 = pres.Slides(4)
    s4.SlideShowTransition.EntryEffect = TRANS_FADE
    s4.SlideShowTransition.Duration = 0.6
    seq4 = s4.TimeLine.MainSequence

    # Shape 5: Reactor Zoom Picture -> Giant Zoom In!
    if s4.Shapes.Count >= 5:
        e = seq4.AddEffect(s4.Shapes(5), ANIM_ZOOM, 0, TRIG_ON_CLICK)
        e.Timing.Duration = 0.85

    # Shape 7: Telemetry Crop Picture -> Fly in from left
    if s4.Shapes.Count >= 7:
        e = seq4.AddEffect(s4.Shapes(7), ANIM_FLY, 0, TRIG_AFTER_PREV)
        e.Timing.Duration = 0.6
        e.EffectParameters.Direction = 1 # from left

    # Deep-dive Cards (Shapes 8, 9, 10)
    for shp_idx in range(8, min(11, s4.Shapes.Count + 1)):
        e = seq4.AddEffect(s4.Shapes(shp_idx), ANIM_FLOAT, 0, TRIG_AFTER_PREV)
        e.Timing.Duration = 0.4

    print("Animated Slide 4: Zoom-In Arc Reactor & Telemetry.")

    # -------------------------------------------------------------
    # SLIDE 5: ZOOM IN — Multilingual Dialogue & News
    # Transition: Push Left
    # Animations:
    # Activity Log Zoom -> Zoom in
    # Dialogue Details -> Fade in on click
    # News Synthesis -> Fly in
    # -------------------------------------------------------------
    s5 = pres.Slides(5)
    s5.SlideShowTransition.EntryEffect = TRANS_PUSH_L
    s5.SlideShowTransition.Duration = 0.7
    seq5 = s5.TimeLine.MainSequence

    # Shape 5: Activity Log Zoom Picture -> Zoom In
    if s5.Shapes.Count >= 5:
        e = seq5.AddEffect(s5.Shapes(5), ANIM_ZOOM, 0, TRIG_ON_CLICK)
        e.Timing.Duration = 0.7

    # Shape 6: Dialogue Transcript Card -> Float in
    if s5.Shapes.Count >= 6:
        e = seq5.AddEffect(s5.Shapes(6), ANIM_FLOAT, 0, TRIG_AFTER_PREV)
        e.Timing.Duration = 0.6

    # Shape 7: News Widget Card -> Fly in
    if s5.Shapes.Count >= 7:
        e = seq5.AddEffect(s5.Shapes(7), ANIM_FLY, 0, TRIG_AFTER_PREV)
        e.Timing.Duration = 0.5
        e.EffectParameters.Direction = 4 # from bottom

    print("Animated Slide 5: Zoom-In Multilingual Dialogue.")

    # -------------------------------------------------------------
    # SLIDE 6: 3D Holographic Avatar Overview (Screenshot 2)
    # Transition: Wipe Right
    # Animations:
    # 3D Face Screenshot -> Dramatic Zoom In!
    # Feature Cards -> Fly in from right
    # -------------------------------------------------------------
    s6 = pres.Slides(6)
    s6.SlideShowTransition.EntryEffect = TRANS_WIPE_R
    s6.SlideShowTransition.Duration = 0.75
    seq6 = s6.TimeLine.MainSequence

    # Shape 5: 3D Face Screenshot -> Zoom In
    if s6.Shapes.Count >= 5:
        e = seq6.AddEffect(s6.Shapes(5), ANIM_ZOOM, 0, TRIG_ON_CLICK)
        e.Timing.Duration = 0.8

    # Feature Cards (Shapes 6-10) -> Fly in from right sequentially
    for shp_idx in range(6, min(11, s6.Shapes.Count + 1)):
        e = seq6.AddEffect(s6.Shapes(shp_idx), ANIM_FLY, 0, TRIG_AFTER_PREV)
        e.Timing.Duration = 0.35
        e.EffectParameters.Direction = 2 # from right

    print("Animated Slide 6: 3D Avatar Overview.")

    # -------------------------------------------------------------
    # SLIDE 7: ZOOM IN — 3D Face Geometry & Lip Sync
    # Transition: Smooth Fade
    # Animations:
    # Face HD Crop -> Zoom In with emphasis
    # Mesh geometry analysis cards -> Pop in
    # -------------------------------------------------------------
    s7 = pres.Slides(7)
    s7.SlideShowTransition.EntryEffect = TRANS_FADE
    s7.SlideShowTransition.Duration = 0.6
    seq7 = s7.TimeLine.MainSequence

    # Shape 5: Face HD Crop Picture -> Zoom In
    if s7.Shapes.Count >= 5:
        e = seq7.AddEffect(s7.Shapes(5), ANIM_ZOOM, 0, TRIG_ON_CLICK)
        e.Timing.Duration = 0.85

    # Mesh Points (Shapes 6, 7, 8)
    for shp_idx in range(6, min(9, s7.Shapes.Count + 1)):
        e = seq7.AddEffect(s7.Shapes(shp_idx), ANIM_FLOAT, 0, TRIG_AFTER_PREV)
        e.Timing.Duration = 0.4

    print("Animated Slide 7: Zoom-In 3D Wireframe Geometry.")

    # -------------------------------------------------------------
    # SLIDE 8: 20+ Action Tool Ecosystem
    # Transition: Push Left
    # Animations:
    # The 4 Tool Columns -> Fly in sequentially from bottom
    # -------------------------------------------------------------
    s8 = pres.Slides(8)
    s8.SlideShowTransition.EntryEffect = TRANS_PUSH_L
    s8.SlideShowTransition.Duration = 0.7
    seq8 = s8.TimeLine.MainSequence

    # Columns 4, 5, 6, 7 -> Fly in
    for idx, shp_idx in enumerate([4, 5, 6, 7]):
        if shp_idx <= s8.Shapes.Count:
            trig = TRIG_ON_CLICK if idx == 0 else TRIG_AFTER_PREV
            e = seq8.AddEffect(s8.Shapes(shp_idx), ANIM_FLY, 0, trig)
            e.Timing.Duration = 0.4
            e.EffectParameters.Direction = 4 # from bottom

    print("Animated Slide 8: Action Tool Ecosystem.")

    # -------------------------------------------------------------
    # SLIDE 9: Multi-Step Mission Planner
    # Transition: Wipe Right
    # Animations:
    # The 5 Pipeline Steps (A, B, C, D, E) -> Pop in sequentially like dominoes!
    # Example Scenario Card -> Zoom in at the end
    # -------------------------------------------------------------
    s9 = pres.Slides(9)
    s9.SlideShowTransition.EntryEffect = TRANS_WIPE_R
    s9.SlideShowTransition.Duration = 0.75
    seq9 = s9.TimeLine.MainSequence

    # Steps 4, 5, 6, 7, 8
    for idx, shp_idx in enumerate([4, 5, 6, 7, 8]):
        if shp_idx <= s9.Shapes.Count:
            trig = TRIG_ON_CLICK if idx == 0 else TRIG_AFTER_PREV
            e = seq9.AddEffect(s9.Shapes(shp_idx), ANIM_ZOOM, 0, trig)
            e.Timing.Duration = 0.35

    # Example Card (Shape 9)
    if s9.Shapes.Count >= 9:
        e = seq9.AddEffect(s9.Shapes(9), ANIM_FLY, 0, TRIG_AFTER_PREV)
        e.Timing.Duration = 0.5
        e.EffectParameters.Direction = 4 # from bottom

    print("Animated Slide 9: Mission Planner Engine.")

    # -------------------------------------------------------------
    # SLIDE 10: E.D.I.T.H. Security Policy Engine (Screenshot 4)
    # Transition: Push Left
    # Animations:
    # EDITH Graphic -> Zoom In prominently
    # 3 Principles -> Float in
    # -------------------------------------------------------------
    s10 = pres.Slides(10)
    s10.SlideShowTransition.EntryEffect = TRANS_PUSH_L
    s10.SlideShowTransition.Duration = 0.7
    seq10 = s10.TimeLine.MainSequence

    # Shape 5: EDITH Image -> Zoom in
    if s10.Shapes.Count >= 5:
        e = seq10.AddEffect(s10.Shapes(5), ANIM_ZOOM, 0, TRIG_ON_CLICK)
        e.Timing.Duration = 0.8

    # Principles (Shapes 6, 7, 8)
    for shp_idx in range(6, min(9, s10.Shapes.Count + 1)):
        e = seq10.AddEffect(s10.Shapes(shp_idx), ANIM_FLOAT, 0, TRIG_AFTER_PREV)
        e.Timing.Duration = 0.4

    print("Animated Slide 10: EDITH Security Engine.")

    # -------------------------------------------------------------
    # SLIDE 11: Mobile Integration & Web HUD
    # Transition: Smooth Fade
    # Animations:
    # 3 Mobile Feature Cards -> Fly in
    # Protocol Card -> Fade in
    # -------------------------------------------------------------
    s11 = pres.Slides(11)
    s11.SlideShowTransition.EntryEffect = TRANS_FADE
    s11.SlideShowTransition.Duration = 0.6
    seq11 = s11.TimeLine.MainSequence

    for idx, shp_idx in enumerate([4, 5, 6]):
        if shp_idx <= s11.Shapes.Count:
            trig = TRIG_ON_CLICK if idx == 0 else TRIG_AFTER_PREV
            e = seq11.AddEffect(s11.Shapes(shp_idx), ANIM_FLY, 0, trig)
            e.Timing.Duration = 0.4
            e.EffectParameters.Direction = 4

    if s11.Shapes.Count >= 7:
        seq11.AddEffect(s11.Shapes(7), ANIM_FADE, 0, TRIG_AFTER_PREV).Timing.Duration = 0.4

    print("Animated Slide 11: Mobile Ecosystem.")

    # -------------------------------------------------------------
    # SLIDE 12: Technical Benchmarks
    # Transition: Push Left
    # Animations:
    # 4 Metric Badges -> Bounce in!
    # Tech Grid -> Float in
    # -------------------------------------------------------------
    s12 = pres.Slides(12)
    s12.SlideShowTransition.EntryEffect = TRANS_PUSH_L
    s12.SlideShowTransition.Duration = 0.7
    seq12 = s12.TimeLine.MainSequence

    # 4 Metrics (Shapes 4, 5, 6, 7) -> Bounce / Zoom In
    for idx, shp_idx in enumerate([4, 5, 6, 7]):
        if shp_idx <= s12.Shapes.Count:
            trig = TRIG_ON_CLICK if idx == 0 else TRIG_AFTER_PREV
            e = seq12.AddEffect(s12.Shapes(shp_idx), ANIM_ZOOM, 0, trig)
            e.Timing.Duration = 0.35

    # Tech Grid (Shapes 8, 9, 10, 11)
    for shp_idx in range(8, min(12, s12.Shapes.Count + 1)):
        e = seq12.AddEffect(s12.Shapes(shp_idx), ANIM_FLOAT, 0, TRIG_AFTER_PREV)
        e.Timing.Duration = 0.35

    print("Animated Slide 12: Technical Benchmarks.")

    # -------------------------------------------------------------
    # SLIDE 13: EPIC & FUNNY "THANK YOU" FINALE!
    # Transition: Dramatic Zoom / Wipe
    # Animations:
    # 1. Headline (THANK YOU FOR NOT PRESSING ESC) -> Zoom In with punch!
    # 2. Funny Cards 1, 2, 3 -> Bounce / Float in with comic timing
    # 3. Creator Card -> Grand entrance!
    # -------------------------------------------------------------
    s13 = pres.Slides(13)
    s13.SlideShowTransition.EntryEffect = TRANS_FADE
    s13.SlideShowTransition.Duration = 0.9
    seq13 = s13.TimeLine.MainSequence

    # Shape 1: Hero Card
    # Shape 2: Funny Header Callout -> Giant Zoom In on Click!
    if s13.Shapes.Count >= 2:
        e = seq13.AddEffect(s13.Shapes(2), ANIM_ZOOM, 0, TRIG_ON_CLICK)
        e.Timing.Duration = 0.85

    # Shapes 3, 4, 5: The 3 Funny Achievement Cards -> Bounce in sequentially!
    for idx, shp_idx in enumerate([3, 4, 5]):
        if shp_idx <= s13.Shapes.Count:
            e = seq13.AddEffect(s13.Shapes(shp_idx), ANIM_FLY, 0, TRIG_AFTER_PREV)
            e.Timing.Duration = 0.45
            e.EffectParameters.Direction = 4 # from bottom

    # Shape 6: Creator Contact & Final Joke Card -> Float in
    if s13.Shapes.Count >= 6:
        e = seq13.AddEffect(s13.Shapes(6), ANIM_FLOAT, 0, TRIG_AFTER_PREV)
        e.Timing.Duration = 0.6

    print("Animated Slide 13: Funny Thank You Finale.")

    # Save to FINAL_PPTX
    pres.SaveAs(FINAL_PPTX)
    pres.Close()
    ppt.Quit()
    print(f"\nAll 13 slides enriched with modern animations and saved to:\n{FINAL_PPTX}")

if __name__ == "__main__":
    animate_deck()
