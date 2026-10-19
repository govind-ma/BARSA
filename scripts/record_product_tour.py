import os
import sys
import time
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

RECORDING_DIR = Path(r"d:\projects\BARSA\recordings")
RECORDING_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR = RECORDING_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def record_tour():
    print("==================================================")
    print("Starting BARSA Master Product Tour Screen Recording")
    print("==================================================")
    print(f"Target directory: {RECORDING_DIR}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--font-render-hinting=none",
            ]
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(RECORDING_DIR),
            record_video_size={"width": 1920, "height": 1080},
            device_scale_factor=1,
        )

        page = context.new_page()

        def smooth_move(x, y):
            try:
                page.mouse.move(x, y, steps=12)
                page.wait_for_timeout(250)
            except Exception:
                pass

        # ----------------------------------------------------
        # Scene 1: Projects Page
        # ----------------------------------------------------
        print("1. Loading Projects page...")
        page.goto("http://localhost:5173/projects", wait_until="networkidle")
        page.wait_for_timeout(2500)
        smooth_move(500, 300)
        page.screenshot(path=str(SCREENSHOTS_DIR / "01_projects_page.png"), full_page=False)

        open_btn = page.locator("button:has-text('Open Project')").first
        if open_btn.is_visible():
            open_btn.hover()
            page.wait_for_timeout(1000)

        # ----------------------------------------------------
        # Scene 2: Project Overview
        # ----------------------------------------------------
        print("2. Entering Project Overview...")
        if open_btn.is_visible():
            open_btn.click()
        else:
            page.goto("http://localhost:5173/", wait_until="networkidle")
        
        page.wait_for_timeout(3000)
        page.screenshot(path=str(SCREENSHOTS_DIR / "02_overview_page.png"), full_page=False)

        # Smooth scroll through Overview
        smooth_move(960, 500)
        page.mouse.wheel(0, 350)
        page.wait_for_timeout(1500)
        page.mouse.wheel(0, -350)
        page.wait_for_timeout(1000)

        # ----------------------------------------------------
        # Scene 3: Why This Task? (Graph Reasoning Modal)
        # ----------------------------------------------------
        print("3. Demonstrating FalkorDB Graph Reasoning Modal...")
        why_btn = page.locator("button:has-text('Why this task?')").first
        if why_btn.is_visible():
            why_btn.hover()
            page.wait_for_timeout(800)
            why_btn.click()
            page.wait_for_timeout(2500)
            page.screenshot(path=str(SCREENSHOTS_DIR / "03_graph_reasoning_modal.png"), full_page=False)
            page.keyboard.press("Escape")
            page.wait_for_timeout(1500)

        # ----------------------------------------------------
        # Scene 4: Continue Work (Agent Handover Modal)
        # ----------------------------------------------------
        print("4. Demonstrating 'Continue Work' Handover Modal...")
        continue_btn = page.locator("button:has-text('Continue Work')").first
        if continue_btn.is_visible():
            continue_btn.hover()
            page.wait_for_timeout(800)
            continue_btn.click()
            page.wait_for_timeout(2500)
            page.screenshot(path=str(SCREENSHOTS_DIR / "04_continue_work_handover.png"), full_page=False)
            page.keyboard.press("Escape")
            page.wait_for_timeout(1500)

        # ----------------------------------------------------
        # Scene 5: Tasks Kanban Board
        # ----------------------------------------------------
        print("5. Navigating to Tasks Kanban Board...")
        page.goto("http://localhost:5173/tasks", wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(SCREENSHOTS_DIR / "05_tasks_kanban.png"), full_page=False)

        # Hover & trigger Recommend Next
        rec_btn = page.locator("button:has-text('Recommend Next')").first
        if rec_btn.is_visible():
            rec_btn.hover()
            page.wait_for_timeout(1000)
            rec_btn.click()
            page.wait_for_timeout(2500)
            page.screenshot(path=str(SCREENSHOTS_DIR / "06_tasks_recommend_next.png"), full_page=False)
            page.keyboard.press("Escape")
            page.wait_for_timeout(1200)

        # ----------------------------------------------------
        # Scene 6: Memory Explorer
        # ----------------------------------------------------
        print("6. Navigating to Memory...")
        page.goto("http://localhost:5173/memory", wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(SCREENSHOTS_DIR / "07_memory_explorer.png"), full_page=False)

        adr_item = page.locator("text=ADR-004").first
        if adr_item.is_visible():
            adr_item.hover()
            page.wait_for_timeout(800)
            adr_item.click()
            page.wait_for_timeout(2200)
            page.screenshot(path=str(SCREENSHOTS_DIR / "08_memory_detail_drawer.png"), full_page=False)
            page.keyboard.press("Escape")
            page.wait_for_timeout(1200)

        # ----------------------------------------------------
        # Scene 7: History Activity Timeline
        # ----------------------------------------------------
        print("7. Navigating to History...")
        page.goto("http://localhost:5173/history", wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(SCREENSHOTS_DIR / "09_history_timeline.png"), full_page=False)

        # ----------------------------------------------------
        # Scene 8: Agents Roster
        # ----------------------------------------------------
        print("8. Navigating to Agents...")
        page.goto("http://localhost:5173/agents", wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(SCREENSHOTS_DIR / "10_agents_roster.png"), full_page=False)

        # ----------------------------------------------------
        # Scene 9: Advanced - Knowledge Graph
        # ----------------------------------------------------
        print("9. Navigating to Advanced: Knowledge Graph...")
        page.goto("http://localhost:5173/graph", wait_until="networkidle")
        page.wait_for_timeout(3500)
        smooth_move(900, 450)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(SCREENSHOTS_DIR / "11_falkordb_knowledge_graph.png"), full_page=False)

        # ----------------------------------------------------
        # Scene 10: Advanced - Version Control & Branches
        # ----------------------------------------------------
        print("10. Navigating to Advanced: Version Control...")
        page.goto("http://localhost:5173/version-control", wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(SCREENSHOTS_DIR / "12_version_control_dag.png"), full_page=False)

        # ----------------------------------------------------
        # Scene 11: Advanced - Checkpoints
        # ----------------------------------------------------
        print("11. Navigating to Advanced: Checkpoints...")
        page.goto("http://localhost:5173/checkpoints", wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(SCREENSHOTS_DIR / "13_checkpoints.png"), full_page=False)

        # ----------------------------------------------------
        # Scene 12: Smooth Return to Project Overview
        # ----------------------------------------------------
        print("12. Returning to Overview for finale...")
        page.goto("http://localhost:5173/", wait_until="networkidle")
        page.wait_for_timeout(3000)
        page.screenshot(path=str(SCREENSHOTS_DIR / "14_overview_finale.png"), full_page=False)

        print("Finalizing video recording...")
        video = page.video
        video_path = video.path() if video else None

        page.close()
        context.close()
        browser.close()

        if video_path and os.path.exists(video_path):
            final_video_name = RECORDING_DIR / "barsa_complete_product_tour.webm"
            if final_video_name.exists():
                try:
                    final_video_name.unlink()
                except Exception:
                    pass
            shutil.copy2(video_path, str(final_video_name))
            print(f"SUCCESS: Tour video saved to {final_video_name}")
            print(f"File size: {os.path.getsize(str(final_video_name)) / (1024*1024):.2f} MB")
        else:
            print("Video path not found or empty.")

if __name__ == "__main__":
    record_tour()
