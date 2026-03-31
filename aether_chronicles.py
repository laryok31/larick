"""
AETHER CHRONICLES: Грани Бесконечности

Эпическая 3D-игра на движке Ursina, где вы - Хранитель Пустоты, способный перемещаться между измерениями.

СЦЕНАРИЙ:
Вы пробудились в Разломе - месте между мирами. Древняя цивилизация Эфирных Создателей 
оставила после себя порталы к разным измерениям. Ваша миссия - собрать фрагменты Ключа Времени,
чтобы предотвратить коллапс мультивселенной.

МИРЫ:
1. НЕБЕСНЫЕ ОСТРОВА - парящие в небе острова с водопадами, уходящими в бесконечность
2. КРИСТАЛЬНЫЕ ПЕЩЕРЫ - подземный мир с сияющими кристаллами и левитирующими платформами  
3. КОСМИЧЕСКАЯ ПУСТОТА - невесомость среди гигантских астероидов и туманностей
4. ЗАБРОШЕННЫЙ ГОРОД - руины древней цивилизации с работающими механизмами

МЕХАНИКИ:
- Свободное перемещение: ходьба по земле и полёт в режиме Хранителя
- Переключение миров через порталы
- Сбор коллекционных фрагментов
- Динамическое освещение и атмосферные эффекты
"""

from ursina import *
from ursina.shaders import lit_with_shadows_shader
import random
import math

# Инициализация приложения
app = Ursina(title='AETHER CHRONICLES: Грани Бесконечности', borderless=False, fullscreen=False, 
             icon=None, vsync=True, fps=120)

# Глобальные переменные
current_world = 'void'
collected_fragments = 0
total_fragments = 15
player_speed = 8
fly_speed = 15
is_flying = False
world_entities = []
portal_entities = []
fragment_entities = []

# Настройка камеры
camera.fov = 90
camera.clip_plane_near = 0.1
camera.clip_plane_far = 1000

# Небо будет меняться в зависимости от мира
sky = Sky(texture='sky_sunset', brightness=0.8)

# Игрок (Хранитель Пустоты)
class Player(Entity):
    def __init__(self):
        super().__init__()
        self.model = 'cube'
        self.color = color.cyan
        self.scale = (0.6, 1.8, 0.6)
        self.position = (0, 2, 0)
        self.speed = player_speed
        self.fly_speed = fly_speed
        self.velocity = Vec3(0, 0, 0)
        self.grounded = False
        self.flying = False
        self.camera_pivot = Entity(parent=self, y=1.5)
        camera.parent = self.camera_pivot
        camera.position = (0, 0, 0)
        camera.rotation = (0, 0, 0)
        
        # Эффект свечения для Хранителя
        self.glow = Entity(parent=self, model='sphere', color=color.cyan, 
                          scale=1.2, alpha=0.3, double_sided=True)
        
    def update(self):
        # Управление движением
        self.handle_movement()
        self.handle_flight()
        
        # Применение скорости
        self.position += self.velocity * time.dt
        
        # Гравитация (если не летим)
        if not self.flying and self.grounded:
            self.velocity.y = lerp(self.velocity.y, 0, time.dt * 10)
        elif not self.flying:
            self.velocity.y -= 20 * time.dt
        
        # Проверка столкновений с землёй
        self.check_ground_collision()
        
        # Ограничение по высоте в некоторых мирах
        if current_world == 'sky' and self.y < -10:
            self.position = (self.x, 10, self.z)
            
    def handle_movement(self):
        direction = Vec3(0, 0, 0)
        
        if held_keys['w']:
            direction += self.forward
        if held_keys['s']:
            direction -= self.forward
        if held_keys['a']:
            direction -= self.right
        if held_keys['d']:
            direction += self.right
            
        if direction != Vec3(0, 0, 0):
            direction = direction.normalized()
            
        speed = self.fly_speed if self.flying else self.speed
        self.velocity.x = lerp(self.velocity.x, direction.x * speed, time.dt * 8)
        self.velocity.z = lerp(self.velocity.z, direction.z * speed, time.dt * 8)
        
    def handle_flight(self):
        global is_flying
        
        # Переключение режима полёта (пробел)
        if held_keys['space'] and self.grounded:
            self.flying = True
            is_flying = True
            self.glow.color = color.gold
            self.glow.scale = 1.5
            
        # Удержание пробела для набора высоты в режиме полёта
        if self.flying and held_keys['space']:
            self.velocity.y = lerp(self.velocity.y, self.fly_speed, time.dt * 5)
        elif self.flying and held_keys['shift']:
            self.velocity.y = lerp(self.velocity.y, -self.fly_speed/2, time.dt * 5)
        else:
            if self.flying:
                self.velocity.y = lerp(self.velocity.y, 0, time.dt * 3)
                
        # Отключение полёта при приземлении
        if self.grounded and not held_keys['space']:
            self.flying = False
            is_flying = False
            self.glow.color = color.cyan
            self.glow.scale = 1.2
            
    def check_ground_collision(self):
        ground_y = get_ground_level(self.position)
        if self.y <= ground_y + 1 and self.velocity.y <= 0:
            self.position = (self.x, ground_y + 1, self.z)
            self.velocity.y = 0
            self.grounded = True
        else:
            self.grounded = False
            
    def input(self, key):
        if key == 'left mouse down':
            # Телепортация к точке взгляда (способность Хранителя)
            self.teleport_ability()

    def teleport_ability(self):
        """Телепортация в направлении взгляда"""
        if self.flying or current_world == 'void':
            ray_origin = self.world_position + Vec3(0, 1, 0)
            hit_info = raycast(ray_origin, self.forward, distance=50, ignore=[self, ])
            if hit_info.hit:
                self.position = hit_info.world_point
                create_teleport_effect(hit_info.world_point)

player = Player()

# Функция получения уровня земли в зависимости от мира
def get_ground_level(position):
    if current_world == 'sky':
        # Небесные острова имеют разную высоту
        return get_island_height(position)
    elif current_world == 'crystal':
        return -5  # Уровень пещеры
    elif current_world == 'void':
        return -100  # Космос без дна
    elif current_world == 'city':
        return 0  # Уровень города
    return 0

def get_island_height(position):
    # Простая проверка принадлежности к острову
    x, z = position[0], position[2]
    
    # Главный остров
    if -30 < x < 30 and -30 < z < 30:
        return 0
    
    # Малые острова
    island_positions = [
        (50, 10), (-50, 15), (40, -40), (-40, -35),
        (0, 60), (0, -60), (70, 0), (-70, 5)
    ]
    
    for ix, iz in island_positions:
        if abs(x - ix) < 15 and abs(z - iz) < 15:
            return random.uniform(5, 15)
    
    return -100  # Падение в пустоту

# Создание эффектов
def create_teleport_effect(position):
    effect = Entity(model='sphere', color=color.cyan, position=position, 
                   scale=0.1, alpha=0.8)
    effect.animate_scale(3, duration=0.5, curve=curve.out_quad)
    effect.animate_alpha(0, duration=0.5, curve=curve.out_quad)
    destroy(effect, delay=0.5)

def create_collection_effect(position):
    for i in range(8):
        particle = Entity(model='cube', color=color.gold, position=position, 
                         scale=0.2, alpha=0.8)
        particle.animate_position(position + Vec3(random.uniform(-2, 2), random.uniform(1, 3), random.uniform(-2, 2)), 
                                 duration=0.6, curve=curve.out_quad)
        particle.animate_alpha(0, duration=0.6)
        destroy(particle, delay=0.6)

# Создание миров
def create_sky_islands():
    """Небесные острова с водопадами"""
    entities = []
    
    # Главный остров
    main_island = Entity(model='terrain', texture='grass', scale=(60, 1, 60), 
                        position=(0, 0, 0), color=color.green, texture_scale=(10, 10))
    entities.append(main_island)
    
    # Деревья на главном острове
    for i in range(15):
        x = random.uniform(-25, 25)
        z = random.uniform(-25, 25)
        tree_trunk = Entity(model='cylinder', color=color.brown, scale=(0.5, 4, 0.5),
                           position=(x, 2, z))
        tree_leaves = Entity(model='sphere', color=color.dark_green, scale=(3, 3, 3),
                            position=(x, 5, z))
        entities.extend([tree_trunk, tree_leaves])
    
    # Малые парящие острова
    island_positions = [
        (50, 10), (-50, 15), (40, -40), (-40, -35),
        (0, 60), (0, -60), (70, 0), (-70, 5)
    ]
    
    for i, (ix, iz) in enumerate(island_positions):
        iy = random.uniform(5, 15)
        island = Entity(model='cube', texture='grass', scale=(random.uniform(20, 30), 3, random.uniform(20, 30)),
                       position=(ix, iy, iz), color=color.green)
        entities.append(island)
        
        # Водопады
        if random.random() > 0.5:
            waterfall = Entity(model='cube', color=color.cyan, 
                              scale=(2, random.uniform(20, 40), 1),
                              position=(ix + random.uniform(-8, 8), iy - 10, iz + random.uniform(-8, 8)),
                              alpha=0.7)
            entities.append(waterfall)
    
    return entities

def create_crystal_caves():
    """Кристальные пещеры с подсветкой"""
    entities = []
    
    # Пол пещеры
    cave_floor = Entity(model='plane', texture='rock', scale=(200, 200), 
                       position=(0, -5, 0), color=color.gray, texture_scale=(20, 20))
    entities.append(cave_floor)
    
    # Потолок пещеры
    cave_ceiling = Entity(model='plane', texture='rock', scale=(200, 200), 
                         position=(0, 30, 0), color=color.dark_gray, texture_scale=(20, 20))
    entities.append(cave_ceiling)
    
    # Кристаллы разных цветов
    crystal_colors = [color.cyan, color.magenta, color.yellow, color.lime]
    for i in range(40):
        x = random.uniform(-80, 80)
        z = random.uniform(-80, 80)
        height = random.uniform(5, 15)
        crystal_color = random.choice(crystal_colors)
        
        crystal = Entity(model='cone', color=crystal_color, 
                        scale=(random.uniform(2, 4), height, random.uniform(2, 4)),
                        position=(x, -5 + height/2, z),
                        emissive=True)
        entities.append(crystal)
        
        # Свет от кристаллов
        light = PointLight(parent=crystal, position=(0, height/2, 0), 
                          color=crystal_color, range=15)
    
    # Сталактиты и сталагмиты
    for i in range(30):
        x = random.uniform(-70, 70)
        z = random.uniform(-70, 70)
        
        # Сталагмиты (снизу)
        stalagmite = Entity(model='cone', color=color.light_gray, 
                           scale=(random.uniform(1, 3), random.uniform(3, 8), random.uniform(1, 3)),
                           position=(x, -5, z))
        entities.append(stalagmite)
        
        # Сталактиты (сверху)
        stalactite = Entity(model='cone', color=color.light_gray, rotation=(180, 0, 0),
                           scale=(random.uniform(1, 3), random.uniform(3, 8), random.uniform(1, 3)),
                           position=(x, 30, z))
        entities.append(stalactite)
    
    return entities

def create_void_space():
    """Космическая пустота с астероидами"""
    entities = []
    
    # Тёмный фон космоса
    sky.texture = 'sky_default'
    sky.color = color.black
    
    # Астероиды
    for i in range(50):
        x = random.uniform(-100, 100)
        y = random.uniform(-50, 50)
        z = random.uniform(-100, 100)
        
        asteroid = Entity(model='sphere', texture='rock', 
                         scale=random.uniform(3, 12),
                         position=(x, y, z),
                         color=color.gray)
        # Вращение астероидов
        asteroid.animate_rotation((random.randint(10, 50), random.randint(10, 50), random.randint(10, 50)), 
                                 duration=random.uniform(10, 30), loop='loop')
        entities.append(asteroid)
    
    # Звёзды (частицы)
    for i in range(200):
        x = random.uniform(-200, 200)
        y = random.uniform(-100, 100)
        z = random.uniform(-200, 200)
        
        star = Entity(model='cube', color=color.white, scale=0.1, 
                     position=(x, y, z), alpha=random.uniform(0.3, 1))
        entities.append(star)
    
    # Большая планета на фоне
    planet = Entity(model='sphere', texture='earth', scale=40, 
                   position=(0, 0, -150))
    entities.append(planet)
    
    return entities

def create_abandoned_city():
    """Заброшенный город древней цивилизации"""
    entities = []
    
    # Земля
    ground = Entity(model='plane', texture='brick', scale=(200, 200), 
                   position=(0, 0, 0), color=color.gray, texture_scale=(30, 30))
    entities.append(ground)
    
    # Здания-руины
    for i in range(20):
        x = random.uniform(-80, 80)
        z = random.uniform(-80, 80)
        
        # Пропускаем центр (там портал)
        if -15 < x < 15 and -15 < z < 15:
            continue
            
        height = random.uniform(10, 40)
        width = random.uniform(8, 15)
        
        building = Entity(model='cube', texture='brick', 
                         scale=(width, height, width),
                         position=(x, height/2, z),
                         color=color.rgb(random.randint(80, 120), random.randint(80, 120), random.randint(80, 120)))
        entities.append(building)
        
        # Окна со светом
        for window_y in range(int(height/5)):
            if random.random() > 0.5:
                window = Entity(model='quad', color=color.yellow, 
                               scale=(1, 1),
                               position=(x + width/2 + 0.1, window_y * 5 + 3, z + random.uniform(-width/3, width/3)),
                               rotation=(0, 90 if random.random() > 0.5 else -90, 0),
                               double_sided=True, emissive=True)
                entities.append(window)
    
    # Дороги
    for i in range(5):
        road = Entity(model='plane', color=color.dark_gray, 
                     scale=(10, random.uniform(50, 100)),
                     position=(random.uniform(-40, 40), 0.1, random.uniform(-40, 40)),
                     rotation=(random.uniform(0, 30), 0, 0))
        entities.append(road)
    
    return entities

# Порталы для переключения миров
def create_portals():
    """Создание порталов между мирами"""
    portals = []
    
    portal_configs = [
        {'pos': (25, 2, 0), 'target': 'crystal', 'color': color.magenta},
        {'pos': (-25, 2, 0), 'target': 'void', 'color': color.cyan},
        {'pos': (0, 2, 25), 'target': 'city', 'color': color.orange},
        {'pos': (0, 2, -25), 'target': 'sky', 'color': color.white},
    ]
    
    for config in portal_configs:
        # Основа портала
        portal_frame = Entity(model='cylinder', color=config['color'], 
                             scale=(3, 0.5, 3), position=config['pos'],
                             emissive=True)
        
        # Энергетическое поле портала
        portal_field = Entity(model='cylinder', color=config['color'], 
                             scale=(2.5, 4, 2.5), position=config['pos'],
                             alpha=0.5, double_sided=True)
        portal_field.animate_alpha(0.3, duration=1, curve=curve.in_out_sine, loop='pingpong')
        
        # Частицы портала
        for i in range(5):
            particle = Entity(model='sphere', color=config['color'], 
                            scale=0.2, alpha=0.8,
                            position=config['pos'] + Vec3(0, random.uniform(0, 2), 0))
            particle.animate_y(config['pos'][1] + random.uniform(2, 4), duration=random.uniform(1, 2), 
                              curve=curve.out_quad, loop='loop')
            portals.append(particle)
        
        portals.extend([portal_frame, portal_field])
        portal_entities.append({'entity': portal_frame, 'target': config['target'], 'pos': config['pos']})
    
    return portals

# Фрагменты Ключа Времени (коллекционные предметы)
def create_fragments():
    """Создание коллекционных фрагментов"""
    fragments = []
    
    fragment_positions = [
        # Небесные острова
        (0, 5, 0), (50, 15, 0), (-50, 20, 15), (40, 12, -40),
        # Кристальные пещеры
        (30, 0, 30), (-30, 0, -30), (0, 0, 50),
        # Космос
        (60, 20, 60), (-60, -10, -60), (0, 30, 0),
        # Город
        (40, 20, 40), (-40, 25, -40), (50, 15, -50), (-50, 30, 50), (0, 35, 0)
    ]
    
    for i, pos in enumerate(fragment_positions[:total_fragments]):
        fragment = Entity(model='octahedron', color=color.gold, 
                         scale=0.8, position=pos,
                         emissive=True)
        # Вращение фрагмента
        fragment.animate_rotation((0, 360, 0), duration=3, loop='loop')
        
        # Свечение вокруг фрагмента
        glow = Entity(parent=fragment, model='sphere', color=color.gold, 
                     scale=1.5, alpha=0.2, double_sided=True)
        glow.animate_scale(2, duration=1, curve=curve.in_out_sine, loop='pingpong')
        
        fragments.append(fragment)
        fragment_entities.append({'entity': fragment, 'collected': False})
    
    return fragments

# UI интерфейс
class UI:
    def __init__(self):
        # Панель информации
        self.info_panel = Text(text=f'Мир: {current_world.upper()}\nФрагменты: {collected_fragments}/{total_fragments}',
                              position=(-0.85, 0.45), scale=1.5, color=color.white, background=True)
        
        # Подсказки управления
        self.controls_help = Text(text='WASD - Движение | ПРОБЕЛ - Полёт/Вверх | SHIFT - Вниз | ЛКМ - Телепорт | 1-4 - Смена мира',
                                 position=(-0.85, -0.45), scale=1, color=color.azure, background=False)
        
        # Индикатор режима полёта
        self.flight_indicator = Text(text='', position=(0.7, 0.45), scale=2, 
                                    color=color.gold, origin=(0, 0))
        
    def update(self):
        self.info_panel.text = f'Мир: {current_world.upper()}\nФрагменты: {collected_fragments}/{total_fragments}'
        self.flight_indicator.text = '✦ ПОЛЁТ ✦' if player.flying else ''

ui = UI()

# Загрузка миров
current_world_entities = []

def load_world(world_name):
    """Загрузка указанного мира"""
    global current_world, current_world_entities
    
    # Очистка текущего мира
    for entity in current_world_entities:
        destroy(entity)
    current_world_entities.clear()
    
    current_world = world_name
    
    # Загрузка нового мира
    if world_name == 'sky':
        sky.texture = 'sky_sunset'
        sky.brightness = 0.8
        current_world_entities.extend(create_sky_islands())
        player.position = (0, 5, 0)
        
    elif world_name == 'crystal':
        sky.texture = 'sky_default'
        sky.color = color.dark_purple
        sky.brightness = 0.3
        current_world_entities.extend(create_crystal_caves())
        player.position = (0, 5, 0)
        
    elif world_name == 'void':
        current_world_entities.extend(create_void_space())
        player.position = (0, 0, 0)
        player.flying = True  # В космосе всегда режим полёта
        
    elif world_name == 'city':
        sky.texture = 'sky_sunset'
        sky.color = color.orange
        sky.brightness = 0.5
        current_world_entities.extend(create_abandoned_city())
        player.position = (0, 5, 0)
    
    # Пересоздаём порталы и фрагменты
    for p in portal_entities:
        destroy(p['entity'])
    portal_entities.clear()
    create_portals()
    
    for f in fragment_entities:
        destroy(f['entity'])
    fragment_entities.clear()
    create_fragments()
    
    print(f"✓ Мир загружен: {world_name}")

# Обработка ввода для смены миров
def input(key):
    if key == '1':
        load_world('sky')
    elif key == '2':
        load_world('crystal')
    elif key == '3':
        load_world('void')
    elif key == '4':
        load_world('city')
    elif key == 'escape':
        application.quit()

# Проверка сбора фрагментов
def check_fragment_collection():
    global collected_fragments
    
    for frag_data in fragment_entities:
        if not frag_data['collected']:
            fragment = frag_data['entity']
            distance = distance_xz(player.position, fragment.position)
            
            if distance < 3 and abs(player.y - fragment.y) < 3:
                # Сбор фрагмента
                frag_data['collected'] = True
                collected_fragments += 1
                create_collection_effect(fragment.position)
                destroy(fragment)
                
                # Звуковой эффект (визуальный)
                ui.info_panel.animate_color(color.gold, duration=0.2, curve=curve.out_quad)
                ui.info_panel.animate_color(color.white, duration=0.2, delay=0.2)
                
                if collected_fragments >= total_fragments:
                    show_victory_message()

def show_victory_message():
    """Показ сообщения о победе"""
    victory_text = Text(text='🏆 ВСЕ ФРАГМЕНТЫ СОБРАНЫ! 🏆\nМультивселенная спасена!',
                       position=(0, 0), origin=(0, 0), scale=3, color=color.gold, background=True)
    victory_text.animate_scale(4, duration=1, curve=curve.out_back, loop='pingpong')

# Основной цикл обновления
def update():
    # Обновление UI
    ui.update()
    
    # Проверка сбора фрагментов
    check_fragment_collection()
    
    # Проверка входа в портал
    check_portal_entry()
    
    # Вращение камеры мышью
    if mouse.delta_x != 0 or mouse.delta_y != 0:
        player.camera_pivot.rotation_y -= mouse.delta_x * 0.2
        player.camera_pivot.rotation_x -= mouse.delta_y * 0.2
        player.camera_pivot.rotation_x = clamp(player.camera_pivot.rotation_x, -90, 90)

def check_portal_entry():
    """Проверка входа игрока в портал"""
    for portal_data in portal_entities:
        portal_pos = portal_data['pos']
        target_world = portal_data['target']
        
        distance = distance_xz(player.position, portal_pos)
        if distance < 3 and abs(player.y - portal_pos[1]) < 3:
            # Вход в портал
            if target_world != current_world:
                load_world(target_world)
                create_teleport_effect(player.position)
                break

# Инициализация игры
print("🌟 AETHER CHRONICLES: Грани Бесконечности 🌟")
print("Загрузка миров...")

load_world('sky')  # Стартовый мир

print("\n=== УПРАВЛЕНИЕ ===")
print("WASD - Перемещение")
print("ПРОБЕЛ - Полёт / Набор высоты")
print("SHIFT - Снижение (в режиме полёта)")
print("ЛКМ - Телепортация (способность Хранителя)")
print("1-4 - Переключение миров:")
print("  1: Небесные Острова")
print("  2: Кристальные Пещеры")
print("  3: Космическая Пустота")
print("  4: Заброшенный Город")
print("ESC - Выход")
print("\nСоберите все 15 фрагментов Ключа Времени!")
print("====================\n")

# Запуск приложения
app.run()
