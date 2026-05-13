from dataclasses import dataclass
from typing import Callable

import pygame

try:
    from .settings import BLUE, CYAN, DANGER, LINE, SUCCESS, TEXT, TEXT_DIM, TEXT_MUTED
    from .utils import clamp, mix_color
except ImportError:
    from settings import BLUE, CYAN, DANGER, LINE, SUCCESS, TEXT, TEXT_DIM, TEXT_MUTED
    from utils import clamp, mix_color


def fit_text(text: str, font: pygame.font.Font, max_width: int) -> str:
    if font.size(text)[0] <= max_width:
        return text

    trimmed = text
    while trimmed and font.size(trimmed + "...")[0] > max_width:
        trimmed = trimmed[:-1]

    return trimmed + "..." if trimmed else "..."


def draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color: tuple[int, int, int],
    anchor: tuple[int, int],
    align: str = "topleft",
    max_width: int | None = None,
) -> pygame.Rect:
    display_text = fit_text(text, font, max_width) if max_width else text
    image = font.render(display_text, True, color)
    rect = image.get_rect()
    setattr(rect, align, anchor)
    surface.blit(image, rect)
    return rect


@dataclass
class Button:
    rect: pygame.Rect
    label: str | Callable[[], str]
    on_click: Callable[[], None]
    enabled: bool | Callable[[], bool] = True
    active: bool | Callable[[], bool] = False
    kind: str = "secondary"
    pressed: bool = False

    def is_enabled(self) -> bool:
        return bool(self.enabled()) if callable(self.enabled) else bool(self.enabled)

    def is_active(self) -> bool:
        return bool(self.active()) if callable(self.active) else bool(self.active)

    def text(self) -> str:
        return self.label() if callable(self.label) else self.label

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and self.is_enabled():
                self.pressed = True
                return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self.pressed
            self.pressed = False
            if was_pressed and self.rect.collidepoint(event.pos) and self.is_enabled():
                self.on_click()
                return True

        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, mouse_pos: tuple[int, int]) -> None:
        enabled = self.is_enabled()
        active = self.is_active()
        hovered = self.rect.collidepoint(mouse_pos) and enabled

        if self.kind == "danger":
            base = (92, 48, 55)
            accent = DANGER
        elif self.kind == "primary":
            base = (43, 84, 151)
            accent = BLUE
        else:
            base = (43, 51, 61)
            accent = CYAN

        if active:
            fill = mix_color(base, SUCCESS, 0.45)
        elif hovered:
            fill = mix_color(base, accent, 0.28)
        else:
            fill = base

        if self.pressed:
            fill = mix_color(fill, (8, 10, 13), 0.18)

        if not enabled:
            fill = (34, 38, 45)

        pygame.draw.rect(surface, fill, self.rect, border_radius=7)
        border = accent if active or hovered else LINE
        pygame.draw.rect(surface, border, self.rect, width=1, border_radius=7)

        label_color = TEXT if enabled else TEXT_DIM
        draw_text(
            surface,
            font,
            self.text(),
            label_color,
            self.rect.center,
            align="center",
            max_width=self.rect.width - 16,
        )


@dataclass
class Slider:
    rect: pygame.Rect
    label: str
    minimum: float
    maximum: float
    value: float
    on_change: Callable[[float], None]
    format_value: Callable[[float], str]
    dragging: bool = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.dragging = True
            self.set_from_x(event.pos[0])
            return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_dragging = self.dragging
            self.dragging = False
            return was_dragging

        if event.type == pygame.MOUSEMOTION and self.dragging:
            self.set_from_x(event.pos[0])
            return True

        return False

    def set_from_x(self, x: int) -> None:
        track = self.track_rect()
        ratio = clamp((x - track.left) / track.width, 0.0, 1.0)
        self.value = self.minimum + ratio * (self.maximum - self.minimum)
        self.on_change(self.value)

    def track_rect(self) -> pygame.Rect:
        return pygame.Rect(self.rect.left, self.rect.bottom - 17, self.rect.width, 6)

    def draw(
        self,
        surface: pygame.Surface,
        label_font: pygame.font.Font,
        value_font: pygame.font.Font,
        mouse_pos: tuple[int, int],
    ) -> None:
        hovered = self.rect.collidepoint(mouse_pos) or self.dragging
        draw_text(surface, label_font, self.label, TEXT_MUTED, (self.rect.left, self.rect.top))
        draw_text(
            surface,
            value_font,
            self.format_value(self.value),
            TEXT,
            (self.rect.right, self.rect.top),
            align="topright",
        )

        track = self.track_rect()
        pygame.draw.rect(surface, (45, 53, 63), track, border_radius=4)

        ratio = (self.value - self.minimum) / (self.maximum - self.minimum)
        filled = pygame.Rect(track.left, track.top, int(track.width * ratio), track.height)
        pygame.draw.rect(surface, BLUE if hovered else CYAN, filled, border_radius=4)

        knob_x = track.left + int(track.width * ratio)
        pygame.draw.circle(surface, (17, 20, 25), (knob_x, track.centery), 9)
        pygame.draw.circle(surface, BLUE if hovered else TEXT, (knob_x, track.centery), 6)
