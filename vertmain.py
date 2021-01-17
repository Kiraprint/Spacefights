import os
import random
import sys
import pygame

pygame.init()
size = width, height = 1200, 800
screen = pygame.display.set_mode(size)
pygame.display.set_caption('Spacefights')

bonuses = ['multishot', 'cd_buff', 'heal']
active_bonuses = bonuses[:-1].copy()
FPS = 120
coords = [(random.random() * width, random.random() * height) for i in range(1000)]
multiplier = 15
spawn_enemies = FPS
score = 0
with open('data/highscore.txt', mode='r') as f:
    try:
        high = int(f.readline())
    except ValueError:
        high = score - 1
speeds = [0, 0, 0, 0]
can_pick = False

clock = pygame.time.Clock()
all_sprites = pygame.sprite.Group()
enemy_group = pygame.sprite.Group()
projectile_group = pygame.sprite.Group()
buf_group = pygame.sprite.Group()


class Buff(pygame.sprite.Sprite):
    def __init__(self, b_type, x, y):
        super().__init__()
        self.image = pygame.transform.scale(load_image(f'{b_type}.png'), (50, 50))
        self.type = b_type
        self.x, self.y = x, y
        self.vx, self.vy = 0, 4
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def update(self):
        self.rect = self.rect.move(self.vx, self.vy)


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__(*all_sprites)
        self.bonuses = dict.fromkeys(bonuses, 0)
        self.start_x, self.start_y = x, y
        self.hp = 3
        self.invulnerable = 0
        self.death_time = FPS * 2
        self.killed = 0
        self.invulnerability_duration = FPS * 5
        self.cooldown = 0
        self.r_cooldown = 0
        self.cd_time = FPS * 3
        self.orig_cd_time = FPS * 3
        self.cd_time_fixed = FPS
        self.speed = 600
        self.image = player_image
        self.rect = self.image.get_rect()
        self.rect.y = y
        self.rect.x = x
        self.buf_time = FPS * 7
        self.timer1 = 0
        self.timer2 = 0

    def check(self):
        if self.rect.x <= 0:
            self.rect.x = 0
        elif self.rect.x + self.rect.w >= width:
            self.rect.x = width - self.rect.w

        if self.rect.y <= 0:
            self.rect.y = 0
        elif self.rect.y + self.rect.h >= height:
            self.rect.y = height - self.rect.h

    def attack(self, attack_mode=''):
        if not attack_mode:
            if not self.cooldown and not self.killed:
                if self.bonuses['multishot'] == 0:
                    Projectile(self.rect.x + self.rect.w / 1.5, self.rect.y + self.rect.h // 2, 'ally', vx=0)

                else:
                    Projectile(self.rect.x + self.rect.w / 1.5, self.rect.y + self.rect.h // 2, 'ally', vx=1)
                    Projectile(self.rect.x + self.rect.w / 1.5, self.rect.y + self.rect.h // 2, 'ally', vx=-1)
                    Projectile(self.rect.x + self.rect.w / 1.5, self.rect.y + self.rect.h // 2, 'ally', vx=0)
                self.cooldown = self.cd_time
        else:
            if not self.r_cooldown and not self.killed:
                if self.bonuses['multishot'] == 0:
                    Projectile(self.rect.x + self.rect.w / 10, self.rect.y + self.rect.h // 2, 'ally', vx=0,
                               mode=attack_mode)
                elif self.bonuses['multishot'] == 1:
                    Projectile(self.rect.x + self.rect.w / 10, self.rect.y + self.rect.h // 2, 'ally', vx=1,
                               mode=attack_mode)
                    Projectile(self.rect.x + self.rect.w / 10, self.rect.y + self.rect.h // 2, 'ally', vx=-1,
                               mode=attack_mode)
                else:
                    Projectile(self.rect.x + self.rect.w / 10, self.rect.y + self.rect.h // 2, 'ally', vx=1,
                               mode=attack_mode)
                    Projectile(self.rect.x + self.rect.w / 10, self.rect.y + self.rect.h // 2, 'ally', vx=-1,
                               mode=attack_mode)
                    Projectile(self.rect.x + self.rect.w / 10, self.rect.y + self.rect.h // 2, 'ally', vx=0,
                               mode=attack_mode)
                self.r_cooldown = self.cd_time

    def move(self, up, down, left, right, time):
        if not self.killed:
            self.rect.y += (down - up) * self.speed * time
            self.rect.x += (right - left) * self.speed * time
            self.check()

    def lower_cd(self):
        self.cd_time = max(50, int(self.cd_time // 2))

    def upgrade_shooting(self):
        if not self.bonuses['multishot']:
            self.bonuses['multishot'] += 1

    def kill(self):
        global active_bonuses
        self.cd_time = self.cd_time_fixed
        self.bonuses = dict.fromkeys(bonuses, 0)
        active_bonuses = bonuses.copy()
        self.hp -= 1
        self.image = explosion
        self.killed = self.death_time

    def respawn(self):
        self.rect.x = self.start_x
        self.rect.y = self.start_y
        self.image = player_image

    def update(self):
        if self.cooldown:
            self.cooldown -= 1
        if self.r_cooldown:
            self.r_cooldown -= 1
        if self.timer1:
            self.timer1 -= 1
        else:
            self.cd_time = self.orig_cd_time
        if self.timer2:
            self.timer2 -= 1
        else:
            self.bonuses['multishot'] = 0

        if self.invulnerable:
            self.invulnerable -= 1
        if self.killed:
            self.killed -= 1
            if not self.killed:
                self.respawn()
                self.invulnerable = self.invulnerability_duration
        buf = pygame.sprite.spritecollideany(self, buf_group)
        if buf:
            if buf.type == 'heal':
                self.hp += 1
            elif buf.type == 'cd_buff':
                self.lower_cd()
                self.timer1 = self.buf_time
            elif buf.type == 'multishot':
                self.upgrade_shooting()
                self.timer2 = self.buf_time
            buf_group.remove(buf)
            all_sprites.remove(buf)


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy):
        super().__init__(enemy_group, all_sprites)
        self.death_time = FPS // 2
        self.killed = 0
        self.vx = vx
        self.image = enemy_image
        self.rect = self.image.get_rect()
        self.x, self.y = x, y
        self.rect.x, self.rect.y = x, y
        self.vy = vy
        self.up = FPS

    def move(self, time):
        if not self.killed:
            self.x += self.vx * time
            self.y += self.vy * time

    def update(self):
        self.rect.x, self.rect.y = int(self.x), int(self.y)
        if self.up:
            self.up -= 1
            if not self.up:
                self.up = FPS
                self.vy = -self.vy
        if self.killed:
            self.killed -= 1
            if not self.killed:
                drop = random.random()
                if drop >= 0:
                    drop = random.randint(0, 2)
                    buf = Buff(bonuses[drop], self.x, self.y)
                    all_sprites.add(buf)
                    buf_group.add(buf)
                enemy_group.remove(self)
                all_sprites.remove(self)

    def kill(self):
        self.image = explosion
        self.killed = self.death_time


class Boss(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__(all_sprites)

        self.cd = 0
        self.boss_cd = FPS * 3
        self.image = load_image('boss.png')
        self.x = 400
        self.y = 0
        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = self.x, self.y
        self.vx = 100
        self.vy = 100
        self.hp = 150
        enemy_group.add(self)
        self.killed = False

    def move(self, time, kx=0, ky=0):
        if not self.killed:
            self.x += self.vx * time * kx
            self.y += self.vy * time * ky

    def update(self):
        self.rect.x, self.rect.y = self.x, self.y
        dmg = pygame.sprite.spritecollideany(self, projectile_group)
        if dmg:
            self.hp -= 1
            all_sprites.remove(dmg)
            projectile_group.remove(dmg)
            if not self.hp:
                self.killed = True
        if self.boss_cd:
            self.boss_cd -= 1


class Projectile(pygame.sprite.Sprite):
    def __init__(self, x, y, t, vx=0, mode=None):
        super().__init__(projectile_group, all_sprites)

        self.x, self.y = x, y
        self.vx = vx
        self.type = t
        if self.type == 'ally':
            self.vy = -5
            self.image = r_shot if mode == 'r' else shot
        else:
            self.vy = 5
            self.image = enemy_shot
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def update(self):
        self.rect = self.rect.move(self.vx, self.vy)


def load_image(name, colorkey=None):
    fullname = os.path.join('data', name)
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    if colorkey is not None:
        image = image.convert()
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()
    return image


explosion = pygame.transform.scale(load_image('explosion.png'), (50, 50))
player_image = pygame.transform.scale(load_image('plane.png'), (70, 70))
enemy_image = pygame.transform.scale(load_image('enemy.png'), (70, 50))
enemy_shot = pygame.transform.rotozoom(load_image('enemy_shot.png'), -90, 0.05)
shot = pygame.transform.rotozoom(load_image('shot.png'), 90, 0.05)
r_shot = pygame.transform.rotozoom(load_image('red_blaster.jpg'), 90, 0.025)

boss_time = FPS * 120


def update_background():
    global coords
    coords = list(map(lambda x: (x[0], x[1] + 5 if x[1] < height else height - x[1]), coords))


def terminate():
    pygame.quit()
    sys.exit()


def start_screen():
    fon = pygame.transform.scale(load_image('start.png'), (width, height))
    screen.blit(fon, (5, 0))
    while True:
        for eve in pygame.event.get():
            if eve.type == pygame.QUIT:
                terminate()
            elif eve.type == pygame.KEYDOWN or \
                    eve.type == pygame.MOUSEBUTTONDOWN:
                return  # начинаем игру
        pygame.display.flip()
        clock.tick(FPS)


boss_fight = False
start_screen()
player = Player(600, 700)
all_sprites.add(player)
bonus_text = None
bonus_text_time = FPS
bonus_text_current_time = 0
bonus_name = None
while True:
    time_delta = clock.get_time() / 1000.0
    boss_time -= 1
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            terminate()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                player.attack()
        if event.type == pygame.MOUSEBUTTONDOWN:
            player.attack(attack_mode='r')

    keys = pygame.key.get_pressed()

    w = keys[pygame.K_w]
    s = keys[pygame.K_s]
    a = keys[pygame.K_a]
    d = keys[pygame.K_d]

    player.move(w, s, a, d, time_delta)

    if spawn_enemies:
        spawn_enemies -= 1
    else:
        enemy_vy = random.choice(speeds)
        enemy_x = 1200
        enemy_y = random.randint(enemy_vy + 100, height - (enemy_vy + 100))
        Projectile(enemy_x, enemy_y + 25, 'enemy')
        for i in range(3):
            Enemy(enemy_x, enemy_y, -200, enemy_vy)
            enemy_x += 150
        for j in range(4):
            Enemy(0, enemy_y, 200, enemy_vy)
        if multiplier // 1.1 >= 3:
            multiplier //= 1.1
            speeds.append(random.choice([100, 200, 300]))
        else:
            multiplier = 3
        spawn_enemies = FPS * multiplier

    for enemy in enemy_group:
        can_pick = True
        if type(enemy) != Boss:
            enemy.move(time_delta)
            if enemy.rect.x <= -enemy.rect.w:
                all_sprites.remove(enemy)
                enemy_group.remove(enemy)
            elif col := pygame.sprite.spritecollideany(enemy, projectile_group):
                if col.type == 'ally' and not enemy.killed:
                    score += 100
                    if random.choice([0, 1, 0, 0]):
                        Projectile(enemy.rect.x, enemy.rect.y + enemy.rect.h // 2, 'enemy')
                    enemy.kill()
                    col.kill()

    for proj in projectile_group:
        if proj.rect.x > width:
            proj.kill()

    if collide := pygame.sprite.spritecollideany(player, projectile_group):
        if collide.type != 'ally' and not player.killed and not player.invulnerable:
            player.kill()

    player_collide_enemy = pygame.sprite.spritecollideany(player, enemy_group)
    if player_collide_enemy and not player.killed and not player.invulnerable and not player_collide_enemy.killed:
        player.kill()
        if type(player_collide_enemy) != Boss:
            player_collide_enemy.kill()

    screen.fill((0, 0, 0))
    if not boss_time:
        boss = Boss()
        boss_fight = True
        on = False

    score_font = pygame.font.Font(None, 50)
    score_text = score_font.render(f'SCORE: {score}', True, (255, 255, 255))
    hp_text = score_font.render(f'HP: {player.hp}', True, (255, 0, 0))
    high_text = score_font.render(f'HI-SCORE: {high}', True, (255, 255, 255))
    if bonus_text_current_time:
        bonus_text_current_time -= 1
        bonus_text = score_font.render(f'You gained: {bonus_name}', True, (255, 255, 255))
        screen.blit(bonus_text, (width // 2 - bonus_text.get_width() // 2, height // 2 - bonus_text.get_height() // 2))
    screen.blit(score_text, (0, 0))
    screen.blit(hp_text, (width // 2 - hp_text.get_width() // 2, 0))
    screen.blit(high_text, (width - high_text.get_width(), 0))

    if boss_fight:
        if not boss.hp:
            screen.fill('white')
            score += 100000
            terminate()
        else:
            if not boss.cd:
                boss.cd = boss.boss_cd
                attack_type = 'ram'
                on = attack_type
        if on == 'ram':
            if player.rect.x > boss.x:
                k1 = 1
            elif player.rect.x == boss.x:
                k1 = 0
            else:
                k1 = -1
            if player.rect.y > boss.y:
                k2 = 1
            elif player.rect.y == boss.y:
                k2 = 0
            else:
                k2 = -1
            boss.move(time_delta, k1, k2)
            if boss.x == player.rect.x and boss.y == player.rect.y:
                on = False
                boss.x, boss.y = 400, 0

    for i in coords:
        screen.fill('white', (*i, 1, 1))
    if player.hp != 0:
        if player.invulnerable:
            pygame.draw.circle(screen, (66, 172, 173),
                               (player.rect.x + player.rect.w // 2, player.rect.y + player.rect.h // 2),
                               player.rect.w // 2)
        update_background()
        all_sprites.draw(screen)
        all_sprites.update()
    else:
        font = pygame.font.Font(None, width // 10)
        text = font.render('Game Over!', True, (255, 255, 255))
        screen.blit(text, (width // 2 - text.get_width() // 2, height // 2 - text.get_height() // 2))
        if high < score:
            with open('data/highscore.txt', mode='w') as f1:
                print(score, file=f1)
    clock.tick(FPS)
    pygame.display.flip()
