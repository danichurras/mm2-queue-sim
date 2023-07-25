from math import log
from random import random
from typing import Union

from pandas import DataFrame, read_csv
from pygame import Color, Vector2, Rect, display, time, event as pygame_event, quit as pg_quit, font as pg_font, \
    Surface, SurfaceType, init as pg_init, QUIT, KEYDOWN, K_RIGHT, K_LEFT
from pygame.draw import line, circle, rect
from pygame.math import clamp, lerp

# region Globals
TEMPO_SIMULACAO = 7 * 8 * 60
linhas = [[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]]
WIDTH: int
HEIGHT: int
screen: Union[Surface, SurfaceType]
t: int
TILE: float
GRID_LEN: int
SPEED_FACTOR: float
DADOS: DataFrame
buffer: DataFrame
shift_offset = 1


# endregion


def generator_line():
    global linhas
    while True:
        linha_anterior = linhas[-1]
        r = round(-log(random()) * 14.666)
        ic = 1 if r == 0 else r
        r = round(-log(random()) * 10.03)
        ta = 1 if r == 0 else r
        tc = ic + linha_anterior[3]
        ia = max(tc, min(linha_anterior[6], linha_anterior[7]))
        fa = ta + ia
        fa1 = fa if linha_anterior[6] <= linha_anterior[7] else linha_anterior[6]
        fa2 = fa if linha_anterior[6] > linha_anterior[7] else linha_anterior[7]
        tf = ia - tc
        ts = fa - tc
        to = 0 if fa < min(fa1, fa2) else ia - min(linha_anterior[6], linha_anterior[7])
        to1 = 0 if fa1 == linha_anterior[6] else ia - linha_anterior[6]
        to2 = 0 if fa2 == linha_anterior[7] else ia - linha_anterior[7]
        yield [len(linhas), ic, ta, tc, ia, fa, fa1, fa2, tf, ts, to, to1, to2]


def gerar_dados():
    global linhas
    while max(linhas[-1][5], linhas[-1][6], linhas[-1][7]) < TEMPO_SIMULACAO:
        linhas.append(next(generator_line()))

    # criar um DataFrame com as linhas com os headers
    headers = ["i", "IC", "TA", "TC", "IA", "FA", "FA1", "FA2", "TF", "TS", "TO", "TO1", "TO2"]
    df = DataFrame(linhas, columns=headers)
    df.to_csv("dados.csv", index=False)
    print(df)

    # calcular as medias de todas as colunas
    medias = df.mean()
    print(medias)


def animar():
    pg_init()

    # region setup
    global GRID_LEN, SPEED_FACTOR, WIDTH, HEIGHT, TILE, screen, t
    WIDTH = 1080
    HEIGHT = 720
    GRID_LEN = 12
    SPEED_FACTOR = 10
    screen = display.set_mode((WIDTH, HEIGHT))
    display.set_caption('Simulacao')
    TILE = screen.get_width() / GRID_LEN
    clock = time.Clock()
    t = 0
    # endregion

    running = True
    while running:
        for event in pygame_event.get():
            if event.type == QUIT:
                running = False
            if event.type == KEYDOWN:
                if event.key == K_RIGHT:
                    SPEED_FACTOR += 0.5
                if event.key == K_LEFT:
                    SPEED_FACTOR -= 0.5
        draw()
        display.flip()
        t += 1 / 60 * SPEED_FACTOR

        # region Update buffer
        global buffer, shift_offset
        if buffer.iloc[-1]['FA'] < t:
            # shift buffer by one
            buffer = DADOS.iloc[shift_offset:150 + shift_offset]
            shift_offset += 1
        # endregion

        clock.tick(60)

    pg_quit()


def draw():
    screen.fill(Color('gray39'))

    # escolher a fonte
    font = pg_font.Font('freesansbold.ttf', 32)

    # region Draw Grid
    for i in range(GRID_LEN):
        # vertical lines: start at (i*TILE,0) to (i*TILE, screen_height)
        start = Vector2(i * TILE, 0)
        end = Vector2(i * TILE, screen.get_height())
        line(screen, Color('darkslategrey'), start_pos=start, end_pos=end)

        # horizontal lines: start at (0,i*TILE) to (screen_width, i*TILE)
        start = Vector2(0, i * TILE)
        end = Vector2(screen.get_width(), i * TILE)
        line(screen, Color('darkslategrey'), start_pos=start, end_pos=end)

    circle(screen, Color('white'), center=(WIDTH / 2, HEIGHT / 2), radius=5, width=5)
    # endregion

    # region Draw Queue Spots
    size = 50
    queue = rect(screen, Color('white'),
                 rect=Rect((3 * TILE + (TILE - size) / 2, 3 * TILE + (TILE - size) / 2, size, size)),
                 width=1)
    screen.blit(font.render("Client", True, Color('white')), (queue.centerx - 20, queue.bottom + 20))
    queue1 = rect(screen, Color('white'),
                  rect=Rect((7 * TILE + (TILE - size) / 2, 2 * TILE + (TILE - 50) / 2, size, size)), width=1)
    screen.blit(font.render("Disk 1", True, Color('white')), (queue1.centerx - 20, queue1.top - 50))
    queue2 = rect(screen, Color('white'),
                  rect=Rect((7 * TILE + (TILE - size) / 2, 5 * TILE + (TILE - 50) / 2, size, size)), width=1)
    screen.blit(font.render("Disk 2", True, Color('white')), (queue2.centerx - 20, queue2.top - 50))
    # endregion

    # region Draw requests in buffer
    queue_count = [0, 0]
    for linha in buffer.iloc():
        # Show point on screen
        if linha['TC'] <= t <= linha['FA']:
            # region Set destiny
            pos_inicial = Vector2(queue.centerx, queue.centery)
            if linha['FA'] == linha['FA1']:
                pos_final = Vector2(queue1.centerx, queue1.centery + queue_count[0] * TILE / 2)
                queue_count[0] += 1
            else:
                pos_final = Vector2(queue2.centerx, queue2.centery + queue_count[1] * TILE / 2)
                queue_count[1] += 1
            # endregion

            # region Calculate trajectory interpolation
            t0 = linha['TC']
            tf = t0 + 1
            dt = tf - t0
            dt = .001 if dt == 0 else dt
            pos = pos_inicial.lerp(pos_final, clamp((t - t0) / dt, 0, 1))
            # endregion

            # region Draw the object
            ponto = circle(screen, Color('purple'), center=pos, radius=5, width=5)
            text = font.render(f"{linha['i']}:({linha['TC']},{linha['FA']})", True, (255, 255, 255))
            screen.blit(text, (ponto.centerx, ponto.centery))
            # endregion

            if t >= linha['IA']:
                # region Draw progress bar on top of the object
                ta = linha['TA'] if linha['TA'] != 0 else 0.001
                bar_width = lerp(0, 20, clamp((t - linha['IA']) / ta, 0, 1))
                progress = rect(screen, Color('darkturquoise'), rect=Rect(pos.x - 10, pos.y - 20, bar_width, 5))
                progress_bar = rect(screen, Color('white'), rect=Rect((pos.x - 10, pos.y - 20, 20, 5)), width=1)
                # endregion

    # endregion

    # region Draw time in the screen
    text = font.render(f"Time: {round(t)} mins  Speed({SPEED_FACTOR}x)", True, Color('white'))
    screen.blit(text, (0, 0))
    # endregion


if __name__ == "__main__":
    # check if dados.csv exists
    try:
        DADOS = read_csv("dados.csv")
        buffer = DADOS.iloc[0:150]
    except FileNotFoundError:
        gerar_dados()
        DADOS = read_csv("dados.csv")
        buffer = DADOS.iloc[0:150]
    animar()
