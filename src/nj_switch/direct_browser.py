"""Ordinary Chrome attachment for Direct Energy's public shopping flow.

Direct's storefront currently rejects Chrome processes launched by Playwright,
while the same public form works in an ordinary Chrome process.  This module
launches an isolated, scraper-owned Chrome profile with Chrome's documented
local debugging interface and then attaches Playwright for deterministic DOM
collection.  It never opens the user's normal browser profile and does not
patch browser fingerprints or solve access challenges.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen


def chrome_candidates() -> list[Path]:
    """Return ordinary Google Chrome locations without assuming one machine."""
    candidates: list[Path] = []
    override = os.environ.get("NJ_SWITCH_CHROME")
    if override:
        candidates.append(Path(override).expanduser())

    for command in ("chrome", "google-chrome", "google-chrome-stable"):
        found = shutil.which(command)
        if found:
            candidates.append(Path(found))

    if sys.platform == "win32":
        for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(variable)
            if base:
                candidates.append(Path(base) / "Google/Chrome/Application/chrome.exe")
    elif sys.platform == "darwin":
        candidates.append(Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"))
    else:
        candidates.extend((
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/google-chrome-stable"),
            Path("/opt/google/chrome/google-chrome"),
        ))

    return list(dict.fromkeys(path.resolve() for path in candidates))


def chrome_executable() -> Path:
    candidates = chrome_candidates()
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    searched = ", ".join(str(path) for path in candidates) or "no candidate locations"
    raise FileNotFoundError(
        "Google Chrome is required for Direct Energy collection. "
        "Install Chrome or set NJ_SWITCH_CHROME to its executable. "
        f"Searched: {searched}"
    )


def available_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


@dataclass
class DirectChromeSession:
    browser: object
    context: object
    process: subprocess.Popen
    profile: Path
    port: int

    @classmethod
    def launch(cls, playwright, profile: Path) -> "DirectChromeSession":
        profile.mkdir(parents=True, exist_ok=True)
        marker = profile / ".direct-homepage-initialized-v1"
        if not marker.is_file():
            # A brand-new Chrome profile must visit Direct's public homepage
            # once before the ordinary Chrome/CDP process is started. Direct's
            # edge then issues the same first-party visitor state received by a
            # new human browser. No values are copied from another profile.
            initial = playwright.chromium.launch_persistent_context(
                str(profile.resolve()), channel="chrome", headless=False,
                accept_downloads=True, viewport={"width": 1360, "height": 900},
            )
            try:
                page = initial.pages[0] if initial.pages else initial.new_page()
                page.goto(
                    "https://www.directenergy.com/",
                    wait_until="domcontentloaded", timeout=30000,
                )
                page.locator(
                    "form#zipcode-form, form.zipcode-form, form.zip-widget-form"
                ).first.wait_for(state="attached", timeout=15000)
            finally:
                initial.close()
            marker.write_text(
                "Initialized only from Direct Energy's public homepage.\n",
                encoding="utf-8",
            )
        port = available_loopback_port()
        process = subprocess.Popen(
            [
                str(chrome_executable()),
                f"--remote-debugging-port={port}",
                "--remote-debugging-address=127.0.0.1",
                f"--user-data-dir={profile.resolve()}",
                "--no-first-run",
                "--no-default-browser-check",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        endpoint = f"http://127.0.0.1:{port}"
        try:
            for _ in range(40):
                if process.poll() is not None:
                    raise RuntimeError("Direct Chrome process exited during startup")
                try:
                    with urlopen(endpoint + "/json/version", timeout=1):
                        break
                except OSError:
                    time.sleep(0.25)
            else:
                raise RuntimeError("Direct Chrome debugging endpoint did not start")
            browser = playwright.chromium.connect_over_cdp(endpoint)
            if len(browser.contexts) != 1:
                raise RuntimeError("Direct Chrome did not expose exactly one isolated context")
            return cls(browser, browser.contexts[0], process, profile, port)
        except Exception:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            raise

    def close(self) -> None:
        try:
            self.browser.close()
        finally:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill()

