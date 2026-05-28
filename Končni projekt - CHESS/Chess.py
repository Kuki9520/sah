import pygame
import chess
import chess.engine
import os
import random
import threading
import time

BOARD_SIZE = 800
SIDE_WIDTH = 420
WIDTH = BOARD_SIZE + SIDE_WIDTH
HEIGHT = BOARD_SIZE
SQ_SIZE = BOARD_SIZE // 8
FPS = 60

START_TIME_SEC = 30 * 60

STOCKFISH_PATH = "stockfish-windows-x86-64-avx2.exe"

engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

def ai_move_stockfish(board, elo=1600, movetime=0.05):
    limit = chess.engine.Limit(time=movetime)
    try:
        info = engine.play(board, limit)
        return info.move
    except:
        return None

def load_images():
    pieces = {}
    names = ["wp","bp","wn","bn","wb","bb","wr","br","wq","bq","wk","bk"]
    for name in names:
        img = pygame.image.load(os.path.join("pieces", name + ".png"))
        pieces[name] = pygame.transform.smoothscale(img, (SQ_SIZE, SQ_SIZE))
    return pieces

def board_to_screen(square, flipped):
    file = square % 8
    rank = square // 8
    if not flipped:
        r = 7 - rank
        c = file
    else:
        r = rank
        c = 7 - file
    return r, c

def screen_to_square(pos, flipped):
    x, y = pos
    if x >= BOARD_SIZE or y >= BOARD_SIZE:
        return None
    c = x // SQ_SIZE
    r = y // SQ_SIZE
    if not flipped:
        rank = 7 - r
        file = c
    else:
        rank = r
        file = 7 - c
    return rank * 8 + file

def draw_board(screen):
    colors = [pygame.Color("#f0d9b5"), pygame.Color("#b58863")]
    for r in range(8):
        for c in range(8):
            pygame.draw.rect(screen, colors[(r+c)%2],
                             (c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE))

def draw_pieces(screen, board, images, flipped, dragging_square=None, dragging_pos=None):
    for square, piece in board.piece_map().items():
        if square == dragging_square:
            continue
        r, c = board_to_screen(square, flipped)
        key = ("w" if piece.color else "b") + piece.symbol().lower()
        screen.blit(images[key], (c*SQ_SIZE, r*SQ_SIZE))

    if dragging_square is not None and dragging_pos is not None:
        piece = board.piece_at(dragging_square)
        if piece:
            key = ("w" if piece.color else "b") + piece.symbol().lower()
            x, y = dragging_pos
            screen.blit(images[key], (x - SQ_SIZE//2, y - SQ_SIZE//2))

def draw_legal_moves(screen, board, from_square, flipped):
    moves = [m for m in board.legal_moves if m.from_square == from_square]
    for move in moves:
        r, c = board_to_screen(move.to_square, flipped)
        center = (c*SQ_SIZE + SQ_SIZE//2, r*SQ_SIZE + SQ_SIZE//2)
        pygame.draw.circle(screen, (0, 0, 0, 80), center, 10)

def draw_last_move_highlight(screen, last_move, flipped):
    if not last_move:
        return
    for sq in [last_move.from_square, last_move.to_square]:
        r, c = board_to_screen(sq, flipped)
        rect = pygame.Rect(c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE)
        pygame.draw.rect(screen, (255, 255, 0, 120), rect, 4)

def material_score(board):
    values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9
    }
    score = 0
    for piece_type in values:
        score += len(board.pieces(piece_type, chess.WHITE)) * values[piece_type]
        score -= len(board.pieces(piece_type, chess.BLACK)) * values[piece_type]
    return score

def draw_clocks_and_info(screen, font, white_time, black_time, player_color, flipped, board, moves_san, view_index, elo):
    panel_x = BOARD_SIZE
    panel_rect = pygame.Rect(panel_x, 0, SIDE_WIDTH, HEIGHT)
    pygame.draw.rect(screen, (25, 25, 35), panel_rect)

    def fmt(t):
        t = max(0, int(t))
        m = t // 60
        s = t % 60
        return f"{m:02d}:{s:02d}"

    white_text = fmt(white_time)
    black_text = fmt(black_time)

    box_w, box_h = SIDE_WIDTH - 40, 40
    white_box = pygame.Rect(panel_x + 20, 20, box_w, box_h)
    black_box = pygame.Rect(panel_x + 20, 70, box_w, box_h)

    pygame.draw.rect(screen, (50, 50, 80), white_box, border_radius=8)
    pygame.draw.rect(screen, (220, 220, 220), white_box, 2, border_radius=8)
    pygame.draw.rect(screen, (50, 50, 80), black_box, border_radius=8)
    pygame.draw.rect(screen, (220, 220, 220), black_box, 2, border_radius=8)

    wt = font.render(f"White: {white_text}", True, (255, 255, 255))
    bt = font.render(f"Black: {black_text}", True, (255, 255, 255))
    screen.blit(wt, (white_box.x + 10, white_box.y + 8))
    screen.blit(bt, (black_box.x + 10, black_box.y + 8))

    elo_text = font.render(f"Bot ELO: {elo}", True, (220, 220, 220))
    screen.blit(elo_text, (panel_x + 20, 130))

    score = material_score(board)
    if score > 0:
        mat_str = f"+{score} za bele"
    elif score < 0:
        mat_str = f"+{-score} za črne"
    else:
        mat_str = "Material izenačen"
    mat_text = font.render(mat_str, True, (220, 220, 220))
    screen.blit(mat_text, (panel_x + 20, 160))

    if view_index == len(moves_san):
        view_str = "Pogled: trenutna pozicija"
    else:
        view_str = f"Pogled: poteza {view_index}/{len(moves_san)}"
    view_text = font.render(view_str, True, (200, 200, 200))
    screen.blit(view_text, (panel_x + 20, 190))

    moves_title = font.render("Poteze:", True, (255, 255, 255))
    screen.blit(moves_title, (panel_x + 20, 220))

    y = 250
    line_h = 20
    for i, san in enumerate(moves_san):
        num = i + 1
        txt = font.render(f"{num}. {san}", True, (220, 220, 220))
        screen.blit(txt, (panel_x + 20, y))
        y += line_h
        if y > HEIGHT - 80:
            break

def draw_nav_buttons(screen, font):
    panel_x = BOARD_SIZE
    prev_rect = pygame.Rect(panel_x + 20, HEIGHT - 60, 50, 30)
    next_rect = pygame.Rect(panel_x + 90, HEIGHT - 60, 50, 30)
    live_rect = pygame.Rect(panel_x + 160, HEIGHT - 60, 80, 30)

    for rect, label in [
        (prev_rect, "<"),
        (next_rect, ">"),
        (live_rect, "LIVE")
    ]:
        pygame.draw.rect(screen, (60, 60, 90), rect, border_radius=6)
        pygame.draw.rect(screen, (220, 220, 220), rect, 2, border_radius=6)
        txt = font.render(label, True, (255, 255, 255))
        screen.blit(txt, (rect.x + (rect.width - txt.get_width())//2,
                          rect.y + (rect.height - txt.get_height())//2))
    return prev_rect, next_rect, live_rect

def is_player_piece(board, square, player_color):
    piece = board.piece_at(square)
    if not piece:
        return False
    return (piece.color == chess.WHITE and player_color == "white") or \
           (piece.color == chess.BLACK and player_color == "black")

def draw_button(screen, rect, text, font, active=False):
    color = (80, 80, 120) if not active else (120, 120, 170)
    pygame.draw.rect(screen, color, rect, border_radius=10)
    pygame.draw.rect(screen, (230, 230, 230), rect, 2, border_radius=10)
    label = font.render(text, True, (255, 255, 255))
    screen.blit(label, (rect.x + (rect.width - label.get_width())//2,
                        rect.y + (rect.height - label.get_height())//2))

def start_menu(screen):
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 40, bold=True)
    small_font = pygame.font.SysFont("arial", 24)

    white_btn = pygame.Rect(WIDTH//2 - 160, 230, 320, 50)
    black_btn = pygame.Rect(WIDTH//2 - 160, 300, 320, 50)
    random_btn = pygame.Rect(WIDTH//2 - 160, 370, 320, 50)

    elo_buttons = [
        (800, pygame.Rect(WIDTH//2 - 190, 460, 80, 40)),
        (1200, pygame.Rect(WIDTH//2 - 95, 460, 80, 40)),
        (1600, pygame.Rect(WIDTH//2, 460, 80, 40)),
        (2000, pygame.Rect(WIDTH//2 + 95, 460, 80, 40)),
    ]
    chosen_color = None
    chosen_elo = 1200

    while chosen_color is None:
        clock.tick(FPS)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.MOUSEBUTTONDOWN:
                if white_btn.collidepoint(event.pos):
                    chosen_color = "white"
                elif black_btn.collidepoint(event.pos):
                    chosen_color = "black"
                elif random_btn.collidepoint(event.pos):
                    chosen_color = random.choice(["white", "black"])
                for elo, rect in elo_buttons:
                    if rect.collidepoint(event.pos):
                        chosen_elo = elo

        screen.fill((18, 18, 30))
        title = font.render("Chess: Player vs Bot", True, (255, 255, 255))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 140))

        info = small_font.render("Izberi svojo barvo:", True, (230, 230, 230))
        screen.blit(info, (WIDTH//2 - info.get_width()//2, 195))

        draw_button(screen, white_btn, "Igram kot BELI", small_font, white_btn.collidepoint(mouse_pos))
        draw_button(screen, black_btn, "Igram kot ČRNI", small_font, black_btn.collidepoint(mouse_pos))
        draw_button(screen, random_btn, "Random", small_font, random_btn.collidepoint(mouse_pos))

        elo_label = small_font.render("Izberi ELO bota:", True, (230, 230, 230))
        screen.blit(elo_label, (WIDTH//2 - elo_label.get_width()//2, 425))

        for elo, rect in elo_buttons:
            active = (elo == chosen_elo)
            pygame.draw.rect(screen, (70, 70, 100) if not active else (130, 130, 180),
                             rect, border_radius=8)
            pygame.draw.rect(screen, (230, 230, 230), rect, 2, border_radius=8)
            t = small_font.render(str(elo), True, (255, 255, 255))
            screen.blit(t, (rect.x + (rect.width - t.get_width())//2,
                            rect.y + (rect.height - t.get_height())//2))

        pygame.display.flip()

    return chosen_color, chosen_elo

def animate_move(screen, board, images, move, flipped, move_sound=None):
    start_sq = move.from_square
    end_sq = move.to_square
    piece = board.piece_at(end_sq)
    if not piece:
        return

    start_r, start_c = board_to_screen(start_sq, flipped)
    end_r, end_c = board_to_screen(end_sq, flipped)

    frames = 10
    key = ("w" if piece.color else "b") + piece.symbol().lower()

    for i in range(1, frames + 1):
        t = i / frames
        cur_x = start_c*SQ_SIZE + (end_c - start_c)*SQ_SIZE * t
        cur_y = start_r*SQ_SIZE + (end_r - start_r)*SQ_SIZE * t

        draw_board(screen)
        temp_board = board.copy()
        temp_board.remove_piece_at(end_sq)
        draw_pieces(screen, temp_board, images, flipped)
        screen.blit(images[key], (cur_x, cur_y))
        pygame.display.flip()
        pygame.time.delay(15)

    if move_sound:
        move_sound.play()

def celebration_screen(screen, result, font_big, font_small):
    clock = pygame.time.Clock()
    running = True

    if result == "1-0":
        msg = "WHITE WINS!"
        color = (120, 220, 120)
    elif result == "0-1":
        msg = "BLACK WINS!"
        color = (220, 120, 120)
    else:
        msg = "DRAW"
        color = (220, 220, 120)

    button = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 60, 200, 50)

    particles = []
    for _ in range(120):
        x = random.randint(0, WIDTH)
        y = random.randint(-HEIGHT, 0)
        speed = random.uniform(1, 4)
        col = random.choice([(255, 100, 100), (100, 255, 100), (100, 100, 255),
                             (255, 255, 100), (255, 150, 255)])
        particles.append([x, y, speed, col])

    while running:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.MOUSEBUTTONDOWN:
                if button.collidepoint(event.pos):
                    running = False

        screen.fill((15, 15, 25))

        for p in particles:
            p[1] += p[2]
            if p[1] > HEIGHT:
                p[0] = random.randint(0, WIDTH)
                p[1] = random.randint(-HEIGHT, 0)
                p[2] = random.uniform(1, 4)
            pygame.draw.circle(screen, p[3], (int(p[0]), int(p[1])), 4)

        title = font_big.render("GAME OVER", True, (255, 255, 255))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 120))

        msg_text = font_big.render(msg, True, color)
        screen.blit(msg_text, (WIDTH//2 - msg_text.get_width()//2, HEIGHT//2 - 60))

        pygame.draw.rect(screen, (60, 60, 90), button, border_radius=10)
        pygame.draw.rect(screen, (230, 230, 230), button, 2, border_radius=10)
        bt = font_small.render("Game review", True, (255, 255, 255))
        screen.blit(bt, (button.x + (button.width - bt.get_width())//2,
                         button.y + (button.height - bt.get_height())//2))

        pygame.display.flip()

def main():
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Player vs Bot Chess")
    clock = pygame.time.Clock()

    try:
        move_sound = pygame.mixer.Sound(os.path.join("sounds", "move.wav"))
    except:
        move_sound = None

    images = load_images()
    font_info = pygame.font.SysFont("consolas", 20)
    font_big = pygame.font.SysFont("arial", 48, bold=True)
    font_small = pygame.font.SysFont("arial", 26)

    player_color, bot_elo = start_menu(screen)
    flipped = (player_color == "black")

    board_live = chess.Board()
    running = True

    dragging = False
    dragging_square = None
    dragging_pos = None
    selected_square = None

    player_turn_live = (player_color == "white")
    ai_thinking = False
    last_move_live = None

    white_time_live = START_TIME_SEC
    black_time_live = START_TIME_SEC
    last_tick = time.time()

    moves_uci = []
    moves_san = []
    fens = [board_live.fen()]
    view_index = len(moves_san)

    game_over_handled = False

    while running:
        dt = time.time() - last_tick
        last_tick = time.time()

        if view_index == len(moves_san) and not board_live.is_game_over():
            if board_live.turn == chess.WHITE:
                white_time_live -= dt
            else:
                black_time_live -= dt

        clock.tick(FPS)

        if (view_index == len(moves_san)
            and not player_turn_live
            and not ai_thinking
            and not board_live.is_game_over()):
            ai_thinking = True

            def ai_job():
                nonlocal board_live, player_turn_live, ai_thinking
                nonlocal last_move_live, moves_uci, moves_san, fens, view_index

                move = ai_move_stockfish(board_live, elo=bot_elo, movetime=0.05)
                if move and move in board_live.legal_moves:
                    san = board_live.san(move)
                    board_live.push(move)
                    last_move_live = move
                    moves_uci.append(move.uci())
                    moves_san.append(san)
                    fens.append(board_live.fen())
                    view_index = len(moves_san)
                ai_thinking = False
                player_turn_live = True

            threading.Thread(target=ai_job, daemon=True).start()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                prev_rect, next_rect, live_rect = draw_nav_buttons(screen, font_info)
                if prev_rect.collidepoint((mx, my)):
                    if view_index > 0:
                        view_index -= 1
                elif next_rect.collidepoint((mx, my)):
                    if view_index < len(moves_san):
                        view_index += 1
                elif live_rect.collidepoint((mx, my)):
                    view_index = len(moves_san)

            if (view_index == len(moves_san)
                and player_turn_live
                and not board_live.is_game_over()):
                if event.type == pygame.MOUSEBUTTONDOWN:
                    sq = screen_to_square(event.pos, flipped)
                    if sq is not None and is_player_piece(board_live, sq, player_color):
                        dragging = True
                        dragging_square = sq
                        dragging_pos = event.pos
                        selected_square = sq

                elif event.type == pygame.MOUSEMOTION and dragging:
                    dragging_pos = event.pos

                elif event.type == pygame.MOUSEBUTTONUP and dragging:
                    to_sq = screen_to_square(event.pos, flipped)
                    if to_sq is not None:
                        move = chess.Move(dragging_square, to_sq)
                        if move in board_live.legal_moves:
                            san = board_live.san(move)
                            board_live.push(move)
                            last_move_live = move
                            moves_uci.append(move.uci())
                            moves_san.append(san)
                            fens.append(board_live.fen())
                            view_index = len(moves_san)
                            animate_move(screen, board_live, images, move, flipped, move_sound)
                            player_turn_live = False
                    dragging = False
                    dragging_square = None
                    dragging_pos = None
                    selected_square = None

        if view_index == len(moves_san):
            board_view = board_live
            last_move_view = last_move_live
            white_time_view = white_time_live
            black_time_view = black_time_live
        else:
            board_view = chess.Board()
            for uci in moves_uci[:view_index]:
                board_view.push(chess.Move.from_uci(uci))
            last_move_view = chess.Move.from_uci(moves_uci[view_index-1]) if view_index > 0 else None
            white_time_view = white_time_live
            black_time_view = black_time_live

        draw_board(screen)
        draw_last_move_highlight(screen, last_move_view, flipped)
        draw_pieces(screen, board_view, images, flipped,
                    dragging_square if dragging and view_index == len(moves_san) else None,
                    dragging_pos if dragging and view_index == len(moves_san) else None)

        if dragging and selected_square is not None and view_index == len(moves_san):
            draw_legal_moves(screen, board_live, selected_square, flipped)

        draw_clocks_and_info(screen, font_info,
                             white_time_view, black_time_view,
                             player_color, flipped,
                             board_view, moves_san, view_index, bot_elo)

        prev_rect, next_rect, live_rect = draw_nav_buttons(screen, font_info)

        pygame.display.flip()

        if board_live.is_game_over() and not game_over_handled:
            game_over_handled = True
            result = board_live.result()
            celebration_screen(screen, result, font_big, font_small)
            view_index = len(moves_san)

    engine.quit()
    pygame.quit()

if __name__ == "__main__":
    main()
