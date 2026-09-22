#!/usr/bin/env python3
"""Heliodor Rink — neon air-hockey arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "HELIODOR RINK"
HANDLE = "x.com/ElbowOS"

INK = (8, 6, 22)
NAVY = (16, 14, 48)
VIOLET = (72, 36, 140)
GOLD = (255, 196, 48)
AMBER = (255, 150, 32)
CREAM = (255, 244, 214)
MAG = (255, 70, 160)
CYAN = (64, 230, 255)
TEAL = (20, 170, 190)
ROSE = (255, 130, 170)

PAD = 56
GOAL_W = 340
RINK = pygame.Rect(PAD, 220, W - 2 * PAD, H - 420)


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "col")

    def __init__(self, x, y, vx, vy, life, col):
        self.x, self.y, self.vx, self.vy, self.life, self.col = x, y, vx, vy, life, col


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 68)
        self.font_md = pygame.font.Font(None, 52)
        self.font_sm = pygame.font.Font(None, 32)
        self.reset()
        self.screen = None
        if not record:
            self.screen = pygame.display.set_mode((W, H))
            pygame.display.set_caption(TITLE)

    def reset(self) -> None:
        self.t = 0.0
        self.you = 0
        self.cpu = 0
        self.flash = 0.0
        self.shake = 0.0
        self.sparks: list[Spark] = []
        self.trail: list[tuple[float, float, float]] = []
        self.pops: list[tuple[str, float, float, float]] = []
        cx, mid = RINK.centerx, RINK.centery
        self.px, self.py = float(cx), float(RINK.bottom - 160)
        self.pvx = self.pvy = 0.0
        self.ax, self.ay = float(cx), float(RINK.top + 160)
        self.avx = self.avy = 0.0
        self.bx, self.by = float(cx), float(mid)
        self.bvx, self.bvy = random.choice([-1, 1]) * 280, random.choice([-320, 320])
        self.pr, self.ar, self.br = 58, 58, 28
        self.stars = [(random.randint(0, W), random.randint(0, H), random.random()) for _ in range(70)]
        self.running = True

    def burst(self, x, y, col, n=12) -> None:
        for _ in range(n):
            a = random.uniform(0, 6.28)
            sp = random.uniform(90, 420)
            self.sparks.append(Spark(x, y, math.cos(a) * sp, math.sin(a) * sp, random.uniform(0.18, 0.5), col))

    def serve(self, toward_you: bool) -> None:
        self.bx, self.by = float(RINK.centerx), float(RINK.centery)
        self.bvx = random.uniform(-220, 220)
        self.bvy = 380 if toward_you else -380
        self.burst(self.bx, self.by, CYAN, 16)

    def bounce_mallet(self, mx, my, mvx, mvy, rad) -> None:
        dx, dy = self.bx - mx, self.by - my
        d = math.hypot(dx, dy) or 1.0
        if d >= rad + self.br:
            return
        nx, ny = dx / d, dy / d
        self.bx = mx + nx * (rad + self.br + 1)
        self.by = my + ny * (rad + self.br + 1)
        relx, rely = self.bvx - mvx, self.bvy - mvy
        vn = relx * nx + rely * ny
        if vn < 0:
            self.bvx -= 1.85 * vn * nx
            self.bvy -= 1.85 * vn * ny
        self.bvx += mvx * 0.35
        self.bvy += mvy * 0.35
        spd = math.hypot(self.bvx, self.bvy)
        cap = 980
        if spd > cap:
            self.bvx *= cap / spd
            self.bvy *= cap / spd
        if spd < 260:
            self.bvx += nx * 80
            self.bvy += ny * 80
        self.burst(self.bx, self.by, GOLD if my > RINK.centery else MAG, 8)

    def autoplay(self) -> tuple[float, float]:
        pred = self.by + self.bvy * 0.18
        tx = self.bx + self.bvx * 0.12
        if self.bvy > 40:
            ty = min(RINK.bottom - 90, pred + 20)
        else:
            ty = RINK.bottom - 170
            tx = RINK.centerx * 0.35 + tx * 0.65
        return tx - self.px, ty - self.py

    def cpu_think(self) -> tuple[float, float]:
        pred = self.by + self.bvy * 0.16
        tx = self.bx + self.bvx * 0.10
        if self.bvy < -40:
            ty = max(RINK.top + 90, pred - 16)
        else:
            ty = RINK.top + 160
            tx = RINK.centerx * 0.4 + tx * 0.6
        return tx - self.ax, ty - self.ay

    def update(self, dt: float) -> None:
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        self.shake = max(0.0, self.shake - dt)
        if self.record:
            dx, dy = self.autoplay()
        else:
            keys = pygame.key.get_pressed()
            dx = dy = 0.0
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                dx -= 1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                dx += 1
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                dy -= 1
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                dy += 1
            if dx or dy:
                n = math.hypot(dx, dy)
                dx, dy = dx / n * 900 * dt * 40, dy / n * 900 * dt * 40
        self.pvx = self.pvx * 0.55 + dx * 7.2
        self.pvy = self.pvy * 0.55 + dy * 7.2
        self.px += self.pvx * dt
        self.py += self.pvy * dt
        self.px = max(RINK.left + self.pr, min(RINK.right - self.pr, self.px))
        self.py = max(RINK.centery + 40, min(RINK.bottom - self.pr, self.py))

        cdx, cdy = self.cpu_think()
        self.avx = self.avx * 0.58 + cdx * 6.6
        self.avy = self.avy * 0.58 + cdy * 6.6
        cap = 720
        cs = math.hypot(self.avx, self.avy)
        if cs > cap:
            self.avx *= cap / cs
            self.avy *= cap / cs
        self.ax += self.avx * dt
        self.ay += self.avy * dt
        self.ax = max(RINK.left + self.ar, min(RINK.right - self.ar, self.ax))
        self.ay = max(RINK.top + self.ar, min(RINK.centery - 40, self.ay))

        self.bx += self.bvx * dt
        self.by += self.bvy * dt
        self.bvx *= 0.999
        self.bvy *= 0.999
        gl, gr = RINK.centerx - GOAL_W / 2, RINK.centerx + GOAL_W / 2
        if self.bx - self.br < RINK.left:
            self.bx = RINK.left + self.br
            self.bvx = abs(self.bvx) * 0.96
            self.burst(self.bx, self.by, CYAN, 6)
        elif self.bx + self.br > RINK.right:
            self.bx = RINK.right - self.br
            self.bvx = -abs(self.bvx) * 0.96
            self.burst(self.bx, self.by, CYAN, 6)
        scored = False
        if self.by - self.br < RINK.top:
            if gl < self.bx < gr:
                self.you += 1
                self.flash = 0.28
                self.shake = 0.22
                self.pops.append(("YOU +1", self.bx, RINK.top + 80, 0.7))
                self.burst(self.bx, RINK.top, GOLD, 22)
                self.serve(toward_you=False)
                scored = True
            else:
                self.by = RINK.top + self.br
                self.bvy = abs(self.bvy) * 0.96
                self.burst(self.bx, self.by, MAG, 6)
        elif self.by + self.br > RINK.bottom:
            if gl < self.bx < gr:
                self.cpu += 1
                self.flash = 0.28
                self.shake = 0.22
                self.pops.append(("CPU +1", self.bx, RINK.bottom - 80, 0.7))
                self.burst(self.bx, RINK.bottom, MAG, 22)
                self.serve(toward_you=True)
                scored = True
            else:
                self.by = RINK.bottom - self.br
                self.bvy = -abs(self.bvy) * 0.96
                self.burst(self.bx, self.by, GOLD, 6)
        if not scored:
            self.bounce_mallet(self.px, self.py, self.pvx, self.pvy, self.pr)
            self.bounce_mallet(self.ax, self.ay, self.avx, self.avy, self.ar)
        self.trail.append((self.bx, self.by, 0.28))
        self.trail = [(x, y, l - dt) for x, y, l in self.trail if l - dt > 0][-40:]
        live = []
        for sp in self.sparks:
            sp.x += sp.vx * dt
            sp.y += sp.vy * dt
            sp.life -= dt
            if sp.life > 0:
                live.append(sp)
        self.sparks = live[-200:]
        self.pops = [(a, x, y - 50 * dt, life - dt) for a, x, y, life in self.pops if life - dt > 0]

    def draw_rink(self, s: pygame.Surface, ox: int, oy: int) -> None:
        s.fill(INK)
        for sx, sy, tw in self.stars:
            yy = int((sy + self.t * (12 + tw * 18)) % H)
            pygame.draw.circle(s, (40 + int(tw * 50), 30, 80), (sx, yy), 1 + int(tw * 2))
        r = RINK.move(ox, oy)
        pygame.draw.rect(s, NAVY, r, border_radius=36)
        pygame.draw.rect(s, VIOLET, r, 8, border_radius=36)
        pygame.draw.rect(s, CYAN, r, 3, border_radius=36)
        pygame.draw.line(s, (80, 50, 160), (r.left + 18, r.centery), (r.right - 18, r.centery), 3)
        pygame.draw.circle(s, (80, 50, 160), r.center, 90, 3)
        gl = r.centerx - GOAL_W // 2
        pygame.draw.rect(s, GOLD, (gl, r.bottom - 14, GOAL_W, 18), border_radius=8)
        pygame.draw.rect(s, MAG, (gl, r.top - 4, GOAL_W, 18), border_radius=8)
        pygame.draw.rect(s, CREAM, (gl, r.bottom - 14, GOAL_W, 18), 2, border_radius=8)
        pygame.draw.rect(s, CREAM, (gl, r.top - 4, GOAL_W, 18), 2, border_radius=8)

    def mallet(self, s, x, y, col, rim) -> None:
        pygame.draw.circle(s, (20, 10, 30), (int(x), int(y) + 6), 60)
        pygame.draw.circle(s, col, (int(x), int(y)), 58)
        pygame.draw.circle(s, rim, (int(x), int(y)), 58, 4)
        pygame.draw.circle(s, CREAM, (int(x), int(y)), 18)
        pygame.draw.circle(s, rim, (int(x), int(y)), 18, 2)

    def draw(self, s: pygame.Surface) -> None:
        ox = int(math.sin(self.t * 40) * 8 * self.shake)
        oy = int(math.cos(self.t * 33) * 6 * self.shake)
        self.draw_rink(s, ox, oy)
        for x, y, life in self.trail:
            pygame.draw.circle(s, CYAN, (int(x + ox), int(y + oy)), 6 + int(10 * life), 0)
        for sp in self.sparks:
            pygame.draw.circle(s, sp.col, (int(sp.x + ox), int(sp.y + oy)), 4)
        self.mallet(s, self.ax + ox, self.ay + oy, MAG, ROSE)
        self.mallet(s, self.px + ox, self.py + oy, AMBER, GOLD)
        pygame.draw.circle(s, TEAL, (int(self.bx + ox), int(self.by + oy)), self.br + 6)
        pygame.draw.circle(s, CYAN, (int(self.bx + ox), int(self.by + oy)), self.br)
        pygame.draw.circle(s, CREAM, (int(self.bx - 6 + ox), int(self.by - 6 + oy)), 7)
        if self.flash > 0:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((255, 210, 80, int(90 * self.flash / 0.28)))
            s.blit(veil, (0, 0))
        title = self.font_lg.render(TITLE, True, GOLD)
        s.blit(title, title.get_rect(center=(W // 2, 58)))
        handle = self.font_sm.render(HANDLE, True, CYAN)
        s.blit(handle, handle.get_rect(center=(W // 2, 112)))
        s.blit(self.font_md.render(f"YOU  {self.you}", True, GOLD), (72, 1768))
        s.blit(self.font_md.render(f"CPU  {self.cpu}", True, MAG), (W - 280, 1768))
        s.blit(self.font_sm.render(f"SCORE  {self.you * 100 - self.cpu * 40}", True, CREAM), (72, 1826))
        for tag, x, y, life in self.pops:
            img = self.font_md.render(tag, True, GOLD)
            s.blit(img, img.get_rect(center=(int(x + ox), int(y + oy))))
        foot = self.font_sm.render("WASD / arrows  slam the heliodor   R reset", True, (180, 160, 220))
        s.blit(foot, foot.get_rect(center=(W // 2, H - 24)))

    def handle(self, ev) -> None:
        if ev.type == pygame.QUIT:
            self.running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.running = False
            elif ev.key == pygame.K_r:
                rec = self.record
                self.__init__(rec)

    def play(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                self.handle(ev)
            self.update(dt)
            self.draw(self.surf)
            self.screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str) -> None:
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main() -> None:
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    if record:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record)
    if record:
        out = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/HELIODOR_RINK_ElbowOS.mp4")
        g.record_mp4(out)
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
