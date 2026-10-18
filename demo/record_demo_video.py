"""BARSA — Automated High-Resolution Screen Recording Script.

Uses Playwright to capture a continuous 1080p video walkthrough of the
BARSA Dashboard, Project ATLAS, FalkorDB Knowledge Graph, Multi-Agent
Coordination, Version Control, and Live Graph Continuation.
"""

import asyncio
import os
import shutil
import time
from pathlib import Path
from playwright.async_api import async_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent
VIDEO_DIR = ROOT_DIR / "demo" / "video"


async def record_walkthrough():
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("  LAUNCHING PLAYWRIGHT HIGH-DEFINITION VIDEO RECORDER (1080p)")
    print("=" * 80)
    print(f"  Target Video Output: {VIDEO_DIR}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--window-size=1920,1080",
                "--font-render-hinting=none",
            ],
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(VIDEO_DIR),
            record_video_size={"width": 1920, "height": 1080},
            device_scale_factor=1.0,
        )

        page = await context.new_page()

        # ---------------------------------------------------------------------
        # SCENE 1: DASHBOARD HOME & SYSTEM OVERVIEW (0:00 - 0:40)
        # ---------------------------------------------------------------------
        print("\n[Scene 1] Recording Dashboard Home & Overview...")
        await page.goto("http://localhost:5173", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Smooth scroll down to reveal system metrics
        await page.mouse.wheel(0, 400)
        await page.wait_for_timeout(2000)
        await page.mouse.wheel(0, 400)
        await page.wait_for_timeout(3000)
        await page.mouse.wheel(0, -800)
        await page.wait_for_timeout(2000)

        # ---------------------------------------------------------------------
        # SCENE 2: PROJECT ATLAS WORKSPACE & GOALS (0:40 - 1:15)
        # ---------------------------------------------------------------------
        print("\n[Scene 2] Navigating to Projects & Project ATLAS...")
        await page.goto("http://localhost:5173/projects", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Click into Project ATLAS detail
        await page.goto("http://localhost:5173/projects/proj-atlas", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        await page.mouse.wheel(0, 300)
        await page.wait_for_timeout(2500)
        await page.mouse.wheel(0, -300)
        await page.wait_for_timeout(2000)

        # ---------------------------------------------------------------------
        # SCENE 3: FALKORDB KNOWLEDGE GRAPH & CONTINUATION (1:15 - 2:30)
        # ---------------------------------------------------------------------
        print("\n[Scene 3] Recording FalkorDB Knowledge Graph Explorer...")
        await page.goto("http://localhost:5173/graph", wait_until="networkidle")
        await page.wait_for_timeout(4000)

        # Interact with the Graph canvas (pan/hover)
        await page.mouse.move(960, 540)
        await page.wait_for_timeout(1000)
        await page.mouse.down()
        await page.mouse.move(860, 480, steps=10)
        await page.mouse.up()
        await page.wait_for_timeout(3000)

        # Scroll down to observe Node Breakdown & Graph Continuation Panel
        await page.mouse.wheel(0, 500)
        await page.wait_for_timeout(3500)

        # Click on Resume / Next-Task query if available on page
        resume_buttons = await page.query_selector_all("button:has-text('Resume'), button:has-text('Continuation'), button:has-text('Reasoning')")
        if resume_buttons:
            print("  -> Triggering Live Graph Reasoning in UI...")
            await resume_buttons[0].click()
            await page.wait_for_timeout(4000)

        await page.mouse.wheel(0, 300)
        await page.wait_for_timeout(3000)
        await page.mouse.wheel(0, -800)
        await page.wait_for_timeout(2000)

        # ---------------------------------------------------------------------
        # SCENE 4: MULTI-AGENT COORDINATION & CAPABILITIES (2:30 - 3:15)
        # ---------------------------------------------------------------------
        print("\n[Scene 4] Recording Multi-Agent Coordination & Tasks...")
        await page.goto("http://localhost:5173/agents", wait_until="networkidle")
        await page.wait_for_timeout(3500)
        await page.mouse.wheel(0, 300)
        await page.wait_for_timeout(2500)
        await page.mouse.wheel(0, -300)

        await page.goto("http://localhost:5173/tasks", wait_until="networkidle")
        await page.wait_for_timeout(3500)
        await page.mouse.wheel(0, 400)
        await page.wait_for_timeout(2500)
        await page.mouse.wheel(0, -400)

        # ---------------------------------------------------------------------
        # SCENE 5: VERSION CONTROL & MEMORY CHECKPOINTS (3:15 - 3:55)
        # ---------------------------------------------------------------------
        print("\n[Scene 5] Recording Version Control DAG & Memory Checkpoints...")
        await page.goto("http://localhost:5173/version-control", wait_until="networkidle")
        await page.wait_for_timeout(3500)

        await page.goto("http://localhost:5173/memory", wait_until="networkidle")
        await page.wait_for_timeout(3500)
        await page.mouse.wheel(0, 300)
        await page.wait_for_timeout(2000)
        await page.mouse.wheel(0, -300)

        # ---------------------------------------------------------------------
        # SCENE 6: SECURITY & LOCAL STORAGE (3:55 - 4:20)
        # ---------------------------------------------------------------------
        print("\n[Scene 6] Recording Security Policies & Storage Engine...")
        await page.goto("http://localhost:5173/security", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        await page.goto("http://localhost:5173/storage", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Return to Dashboard Home for finale
        await page.goto("http://localhost:5173", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Finalize and close video
        print("\n[Scene 7] Finalizing video encoding...")
        video = page.video
        await context.close()
        await browser.close()

        if video:
            raw_video_path = await video.path()
            target_path = VIDEO_DIR / "BARSA_Graph_Hacks_Demo_1080p.webm"
            if os.path.exists(raw_video_path):
                shutil.copy(raw_video_path, str(target_path))
                size_mb = os.path.getsize(str(target_path)) / (1024 * 1024)
                print("\n" + "=" * 80)
                print("  VIDEO RECORDING COMPLETED SUCCESSFULLY!")
                print(f"  Saved To : {target_path}")
                print(f"  File Size: {size_mb:.2f} MB")
                print(f"  Format   : WebM Video (1920x1080 Full HD)")
                print("=" * 80 + "\n")
            else:
                print(f"Raw video generated at: {raw_video_path}")


if __name__ == "__main__":
    asyncio.run(record_walkthrough())
