"""
POU FLOW — jogo de conectar cores
---------------------------------
Um jogo de lógica inspirado nos jogos de ligar pontos coloridos.

Como jogar:
1. Instale Python 3.10+ e Pygame:
       python -m pip install pygame
2. Salve este arquivo como pou_flow.py
3. Execute:
       python pou_flow.py

Regras:
- Ligue cada par de pontos da mesma cor.
- Arraste o mouse pelas casas vizinhas para desenhar o caminho.
- Caminhos não podem se cruzar nem ocupar a mesma casa.
- Para vencer, conecte todos os pares E preencha todas as casas do tabuleiro.
- Clique em Reiniciar para tentar de novo ou Próximo para avançar após vencer.

Controles:
- Botão esquerdo + arrastar: desenhar caminho
- Arrastar de volta para a casa anterior: desfazer o último trecho
- R: reiniciar fase
- ESC: sair
"""

import pygame
import sys
from dataclasses import dataclass

# --------------------------- Configurações ---------------------------

pygame.init()
pygame.display.set_caption("Pou Flow — Conecte as cores")

WIDTH, HEIGHT = 900, 760
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
CLOCK = pygame.time.Clock()
FPS = 60

ROWS, COLS = 6, 6
CELL = 76
GRID_W = COLS * CELL
GRID_H = ROWS * CELL
GRID_X = (WIDTH - GRID_W) // 2
GRID_Y = 175

BG = (247, 249, 255)
PANEL = (255, 255, 255)
TEXT = (48, 55, 80)
MUTED = (112, 121, 148)
GRID_LINE = (218, 224, 239)
EMPTY = (239, 243, 251)
WHITE = (255, 255, 255)
GREEN = (45, 174, 118)
RED = (224, 83, 96)
SHADOW = (226, 231, 243)

COLORS = [
    (239, 82, 116),   # rosa
    (49, 156, 224),   # azul
    (255, 174, 54),   # laranja
    (112, 91, 219),   # roxo
    (49, 190, 139),   # verde
    (235, 194, 56),   # amarelo
]

FONT = pygame.font.SysFont("arial", 23, bold=True)
SMALL = pygame.font.SysFont("arial", 17)
TINY = pygame.font.SysFont("arial", 14)
TITLE = pygame.font.SysFont("arial", 38, bold=True)
BIG = pygame.font.SysFont("arial", 28, bold=True)


@dataclass
class Level:
    name: str
    segments: list


def make_levels():
    """
    Cada fase é criada a partir de um percurso serpenteante que passa por
    todas as casas. O percurso é dividido em caminhos coloridos; assim, há
    pelo menos uma solução que conecta todos os pares e preenche o tabuleiro.
    """
    snake = []
    for r in range(ROWS):
        columns = range(COLS) if r % 2 == 0 else range(COLS - 1, -1, -1)
        for c in columns:
            snake.append((r, c))

    # Quantidade de casas em cada caminho; cada caminho tem pelo menos 2 casas.
    patterns = [
        [8, 10, 8, 10],
        [6, 8, 10, 6, 6],
        [12, 8, 8, 8],
        [6, 6, 8, 8, 8],
        [10, 6, 6, 8, 6],
        [8, 8, 6, 6, 8],
        [6, 10, 6, 8, 6],
        [8, 6, 8, 6, 8],
        [6, 6, 6, 6, 6, 6],
        [10, 8, 6, 6, 6],
    ]
    levels = []
    for idx, pattern in enumerate(patterns):
        assert sum(pattern) == ROWS * COLS
        segments = []
        start = 0
        for size in pattern:
            segments.append(snake[start:start + size])
            start += size
        levels.append(Level(f"Fase {idx + 1}", segments))
    return levels


LEVELS = make_levels()


class FlowGame:
    def __init__(self):
        self.level_index = 0
        self.load_level(0)

    def load_level(self, index):
        self.level_index = index % len(LEVELS)
        self.level = LEVELS[self.level_index]
        self.pairs = {}
        self.endpoints = {}
        for color_index, segment in enumerate(self.level.segments):
            color = COLORS[color_index % len(COLORS)]
            a, b = segment[0], segment[-1]
            self.pairs[color] = (a, b)
            self.endpoints[a] = color
            self.endpoints[b] = color
        self.reset()

    def reset(self):
        self.paths = {color: [] for color in self.pairs}
        self.occupied = {}
        self.active_color = None
        self.won = False
        self.message = "Ligue os pares e preencha todas as casas."
        self.message_color = MUTED
        self.rebuild_solution_paths()

    def rebuild_solution_paths(self):
        # Apenas referência interna para os endpoints originais.
        self.endpoint_positions = set(self.endpoints.keys())

    def cell_center(self, cell):
        r, c = cell
        return GRID_X + c * CELL + CELL // 2, GRID_Y + r * CELL + CELL // 2

    def cell_from_mouse(self, pos):
        x, y = pos
        if not (GRID_X <= x < GRID_X + GRID_W and GRID_Y <= y < GRID_Y + GRID_H):
            return None
        c = (x - GRID_X) // CELL
        r = (y - GRID_Y) // CELL
        return int(r), int(c)

    @staticmethod
    def adjacent(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1

    def color_at(self, cell):
        return self.occupied.get(cell)

    def begin_path(self, cell):
        if cell not in self.endpoints:
            color = self.occupied.get(cell)
            if color is None:
                return
            # Permite continuar um caminho clicando nele.
        else:
            color = self.endpoints[cell]

        # Ao começar em um ponto final, apaga o caminho anterior dessa cor.
        # Se clicar no meio de um caminho, remove apenas o trecho posterior.
        old = self.paths.get(color, [])
        if cell in old:
            idx = old.index(cell)
            self.remove_path(color)
            old = old[:idx + 1]
            self.paths[color] = old
            for p in old:
                self.occupied[p] = color
        else:
            self.remove_path(color)
            old = [cell]
            self.paths[color] = old
            self.occupied[cell] = color

        self.active_color = color
        self.won = False

    def remove_path(self, color):
        for cell in self.paths.get(color, []):
            if self.occupied.get(cell) == color:
                del self.occupied[cell]
        self.paths[color] = []

    def extend_path(self, cell):
        color = self.active_color
        if color is None or cell is None or self.won:
            return
        path = self.paths[color]
        if not path:
            return
        last = path[-1]
        if cell == last:
            return

        # Arrastar para a casa anterior desfaz o último passo.
        if len(path) >= 2 and cell == path[-2]:
            removed = path.pop()
            if self.occupied.get(removed) == color:
                del self.occupied[removed]
            return

        if not self.adjacent(last, cell):
            return

        # Não deixa entrar em uma casa ocupada por outra cor.
        owner = self.occupied.get(cell)
        if owner is not None and owner != color:
            return

        # Não permite repetir casas do próprio caminho, exceto voltar um passo.
        if cell in path:
            return

        # Um endpoint de outra cor não pode ser atravessado.
        if cell in self.endpoints and self.endpoints[cell] != color:
            return

        # Chegou ao endpoint correspondente: fecha o caminho.
        path.append(cell)
        self.occupied[cell] = color
        if cell in self.endpoints and self.endpoints[cell] == color:
            self.active_color = None
            self.check_win()

    def end_drag(self):
        self.active_color = None

    def check_win(self):
        all_connected = True
        for color, (a, b) in self.pairs.items():
            path = self.paths[color]
            if len(path) < 2 or path[0] not in (a, b) or path[-1] not in (a, b):
                all_connected = False
                break
            if set((path[0], path[-1])) != set((a, b)):
                all_connected = False
                break
        all_filled = len(self.occupied) == ROWS * COLS
        if all_connected and all_filled:
            self.won = True
            self.message = "Perfeito! Você completou a fase!"
            self.message_color = GREEN
        elif all_connected:
            self.message = f"Pares conectados! Faltam preencher {ROWS * COLS - len(self.occupied)} casas."
            self.message_color = (190, 126, 36)

    def draw_text(self, text, font, color, center):
        surf = font.render(text, True, color)
        SCREEN.blit(surf, surf.get_rect(center=center))

    def draw_button(self, rect, label, enabled=True, primary=False):
        color = (79, 116, 230) if primary else (255, 255, 255)
        if not enabled:
            color = (225, 229, 239)
        pygame.draw.rect(SCREEN, SHADOW, rect.move(0, 4), border_radius=14)
        pygame.draw.rect(SCREEN, color, rect, border_radius=14)
        txt_color = WHITE if primary and enabled else (TEXT if enabled else MUTED)
        self.draw_text(label, SMALL, txt_color, rect.center)

    def draw(self):
        SCREEN.fill(BG)

        # Cabeçalho
        self.draw_text("POU FLOW", TITLE, (75, 94, 174), (WIDTH // 2, 48))
        self.draw_text("Conecte as cores. Preencha o tabuleiro.", SMALL, MUTED, (WIDTH // 2, 83))

        # Cartão de status
        status_rect = pygame.Rect(100, 106, WIDTH - 200, 48)
        pygame.draw.rect(SCREEN, WHITE, status_rect, border_radius=14)
        pygame.draw.rect(SCREEN, (231, 235, 247), status_rect, width=1, border_radius=14)
        self.draw_text(self.message, SMALL, self.message_color, status_rect.center)

        # Tabuleiro com sombra
        outer = pygame.Rect(GRID_X - 8, GRID_Y - 8, GRID_W + 16, GRID_H + 16)
        pygame.draw.rect(SCREEN, SHADOW, outer.move(0, 5), border_radius=20)
        pygame.draw.rect(SCREEN, PANEL, outer, border_radius=20)

        # Casas
        for r in range(ROWS):
            for c in range(COLS):
                cell = (r, c)
                x = GRID_X + c * CELL
                y = GRID_Y + r * CELL
                rect = pygame.Rect(x + 3, y + 3, CELL - 6, CELL - 6)
                pygame.draw.rect(SCREEN, EMPTY, rect, border_radius=10)

                color = self.occupied.get(cell)
                if color is not None:
                    inner = rect.inflate(-13, -13)
                    pygame.draw.rect(SCREEN, color, inner, border_radius=9)

        # Linhas do caminho por cima das casas
        for color, path in self.paths.items():
            if len(path) >= 2:
                centers = [self.cell_center(p) for p in path]
                pygame.draw.lines(SCREEN, color, False, centers, 17)
                for center in centers:
                    pygame.draw.circle(SCREEN, color, center, 9)

        # Grade fina
        for r in range(ROWS):
            for c in range(COLS):
                x = GRID_X + c * CELL
                y = GRID_Y + r * CELL
                pygame.draw.rect(SCREEN, GRID_LINE, (x, y, CELL, CELL), width=1, border_radius=3)

        # Pontos de início/fim
        for cell, color in self.endpoints.items():
            cx, cy = self.cell_center(cell)
            pygame.draw.circle(SCREEN, WHITE, (cx, cy), 22)
            pygame.draw.circle(SCREEN, color, (cx, cy), 18)
            pygame.draw.circle(SCREEN, WHITE, (cx, cy), 7)

        # Contagem
        filled = len(self.occupied)
        self.draw_text(f"Casas preenchidas: {filled}/{ROWS * COLS}", SMALL, TEXT, (WIDTH // 2, 660))

        # Botões
        y = 690
        btn_w, btn_h, gap = 155, 42, 14
        total = btn_w * 3 + gap * 2
        x0 = (WIDTH - total) // 2
        self.draw_button(pygame.Rect(x0, y, btn_w, btn_h), "Reiniciar")
        self.draw_button(pygame.Rect(x0 + btn_w + gap, y, btn_w, btn_h),
                         "Próxima fase", enabled=self.won, primary=True)
        self.draw_button(pygame.Rect(x0 + 2 * (btn_w + gap), y, btn_w, btn_h), "Como jogar")

        if self.won:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 120))
            SCREEN.blit(overlay, (0, 0))
            box = pygame.Rect(190, 275, WIDTH - 380, 180)
            pygame.draw.rect(SCREEN, SHADOW, box.move(0, 7), border_radius=24)
            pygame.draw.rect(SCREEN, WHITE, box, border_radius=24)
            self.draw_text("FASE COMPLETA!", BIG, GREEN, (WIDTH // 2, 320))
            self.draw_text("Você conectou todos os pares e preencheu tudo.", SMALL, TEXT, (WIDTH // 2, 363))
            self.draw_text("Clique em Próxima fase para continuar.", SMALL, MUTED, (WIDTH // 2, 397))

    def show_help(self):
        # Ajuda em um painel simples; fecha ao clicar ou pressionar uma tecla.
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    waiting = False
            self.draw()
            shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            shade.fill((31, 39, 70, 145))
            SCREEN.blit(shade, (0, 0))
            box = pygame.Rect(130, 225, WIDTH - 260, 300)
            pygame.draw.rect(SCREEN, WHITE, box, border_radius=24)
            self.draw_text("COMO JOGAR", BIG, (75, 94, 174), (WIDTH // 2, 270))
            help_lines = [
                "1. Clique em um ponto colorido e arraste.",
                "2. Passe apenas por casas vizinhas (cima, baixo, esquerda, direita).",
                "3. Ligue cada ponto ao outro ponto da mesma cor.",
                "4. Caminhos não podem se cruzar nem compartilhar casas.",
                "5. Para vencer, todas as casas precisam estar preenchidas.",
                "Dica: arraste para a casa anterior para desfazer um passo.",
            ]
            for i, line in enumerate(help_lines):
                self.draw_text(line, SMALL, TEXT, (WIDTH // 2, 320 + i * 30))
            pygame.display.flip()
            CLOCK.tick(FPS)


def main():
    game = FlowGame()
    buttons_y = 690
    btn_w, btn_h, gap = 155, 42, 14
    total = btn_w * 3 + gap * 2
    x0 = (WIDTH - total) // 2
    restart_rect = pygame.Rect(x0, buttons_y, btn_w, btn_h)
    next_rect = pygame.Rect(x0 + btn_w + gap, buttons_y, btn_w, btn_h)
    help_rect = pygame.Rect(x0 + 2 * (btn_w + gap), buttons_y, btn_w, btn_h)

    dragging = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_r:
                    game.reset()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                if restart_rect.collidepoint(pos):
                    game.reset()
                elif next_rect.collidepoint(pos) and game.won:
                    game.load_level(game.level_index + 1)
                elif help_rect.collidepoint(pos):
                    game.show_help()
                else:
                    cell = game.cell_from_mouse(pos)
                    if cell is not None:
                        game.begin_path(cell)
                        dragging = game.active_color is not None
                        if dragging:
                            game.extend_path(cell)

            if event.type == pygame.MOUSEMOTION and dragging:
                cell = game.cell_from_mouse(event.pos)
                game.extend_path(cell)

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = False
                game.end_drag()

        game.draw()
        pygame.display.flip()
        CLOCK.tick(FPS)


if __name__ == "__main__":
    main()
