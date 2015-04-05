#!/usr/bin/python3

from logging import exception
from curses import wrapper, noecho, echo, nocbreak, cbreak, A_BOLD
from json import loads, dumps

from os import listdir, makedirs
from os.path import exists, isdir
from shutil import copyfile
from datetime import datetime
from math import ceil

###   CONFIGURATION   ###

# Path to the game's own save path.
GAME_SAVE_PATH = ""
# Path to where the manager should save.
MANAGER_PATH   = ""

### END CONFIGURATION ###

PROMPT = "> "

def chunks(l, n):
    # noinspection PyArgumentList
    for i in range(0, len(l), n):
        yield l[i:i + n]

# noinspection PyUnusedLocal
def good_quit(screen):
    quit()

def addstr(screen, string, *args, newline=True):
    yx = screen.getyx()
    if yx[0] == 0 and yx[1] == 0: newline = False
    screen.addstr(yx[0] + (1 if newline else 0), 0 if newline else yx[1], string, *args)

def get_str(screen, prompt=PROMPT, header=None, default=None, clear=False):
    if not header: header = []
    if clear: screen.clear()
    for item in header:
        if item is None: continue
        if isinstance(item, tuple):
            addstr(screen, "{}".format(item[0]), item[1])
        else:
            addstr(screen, "{}".format(item))
    addstr(screen, prompt)
    screen.refresh()
    data = screen.getstr().decode("utf-8")
    if len(data) < 1 and default: return default
    return data

def get_dir(screen, header=None, prompt=PROMPT, clear=False, default=None):
    if not header: header = []
    error = None
    wanted_dir = None
    while True:
        wanted_dir = get_str(screen, header=header + [error], prompt=prompt, clear=clear, default=default)
        if exists(wanted_dir) and isdir(wanted_dir): break
        if not exists(wanted_dir):
            error = "That directory didn't exist!"
        elif not isdir(wanted_dir):
            error = "That is not a directory."
    return wanted_dir

def main(screen):
    screen.scrollok(True)
    echo()
    nocbreak()
    welcome(screen)

def welcome(screen):
    tasks = {
        1: ("Save the current game (save in-game first)", (save_game_menu,)),
        2: ("Load a previous game", (load_game_menu,)),
        3: ("Exit", (good_quit,))
    }
    menu(screen, tasks, header=[
        ("Welcome to the NEO Scavenger save manager (v0.1.0).", A_BOLD),
        "Please select a task from the list below."
    ])

def save_game_menu(screen):
    tasks = {
        1: ("Save game", (save_game,)),
        2: ("Return", (welcome,))
    }
    menu(
        screen, tasks, header=[
            "Ensure that you have saved in the game before continuing."
        ]
    )

def get_save(save_number):
    save_path = '{}/{}'.format(MANAGER_PATH, save_number)
    save_metadata_path = '{}/metadata'.format(save_path)
    with open(save_metadata_path, 'r') as f:
        return loads(f.read())

def get_saves():
    metadata_path = '{}/metadata'.format(MANAGER_PATH)
    if not exists(metadata_path):
        return []
    last_save = get_last_save_number()
    saves = {}
    for save_number in range(last_save):
        save = get_save(save_number + 1)
        saves[save['save_number']] = save
    return saves

def get_load_page(screen, number):
    # Get rows and subtract 4 (headers, etc.)
    amount = screen.getmaxyx()[0] - 4
    # Make the page
    page = []
    # Get all the saves
    saves = get_saves()
    # Figure out when the next page will start
    next_start = max(amount * (number - 1), 0) # Should be less than this page's end
    # Determine when this page should start
    start = len(saves) - next_start
    while len(page) < amount and start <= len(saves) and start > 0:
        if start not in saves:
            start -= 1
            continue
        page.append(saves[start])
        start -= 1
    return page

def get_max_page(screen):
    amount = screen.getmaxyx()[0] - 4
    saves = get_saves()
    return ceil(len(saves) / float(amount))

page = 1

def next_page(screen):
    global page
    max_page = get_max_page(screen)
    page = min(page + 1, max_page)
    load_game_menu(screen)

def previous_page(screen):
    global page
    page = max(page - 1, 1)
    load_game_menu(screen)

def load_game_menu(screen):
    tasks = {
        0: ("Return", (welcome,)),
        'n': (None, (next_page,)),
        'p': (None, (previous_page,))
    }
    saves = get_saves()
    all_saves = len(saves)
    for save in get_load_page(screen, page):
        tasks[save['save_number']] = (
            '[{}] {}'.format(save['date'], save['description']),
            (load_game, screen, save['save_number'])
        )
    menu(
        screen, tasks, header=[
            "Page {} of {} ({} save{}).".format(page, get_max_page(screen), all_saves, "" if all_saves == 1 else "s"),
            "Choose a game to restore. Use n (next) or p (previous)"
        ], reverse=True
    )

def load_game(screen, number):
    menu(
        screen,
        {
            1: ('Yes', (do_nothing,)),
            2: ('No', (load_game_menu,))
        },
        header=[
            'Do you want to restore save {}?'.format(number)
        ]
    )
    save_path = '{}/{}'.format(MANAGER_PATH, number)
    file_path = '{}/files'.format(save_path)
    for name in listdir(file_path):
        copyfile('{}/{}'.format(file_path, name), '{}/{}'.format(GAME_SAVE_PATH, name))
    pause(screen, 'Game restored. Press enter to return.')
    welcome(screen)

def do_nothing(screen):
    pass

def pause(screen, message=None):
    if message is not None:
        addstr(screen, message)
    nocbreak()
    noecho()
    screen.getch()
    cbreak()
    echo()

def save_game(screen):
    if not exists(GAME_SAVE_PATH) or not isdir(GAME_SAVE_PATH):
        tasks = {
            1: ("Return", (welcome,))
        }
        menu(
            screen, tasks, header=[
                "The game save path did not exist."
            ]
        )
    if not exists(MANAGER_PATH):
        makedirs(MANAGER_PATH)
    description = ""
    while description.strip() == "":
        description = get_str(screen, prompt="Enter a save description: ")
    save_number, path, file_path = make_new_save(description)
    for name in listdir(GAME_SAVE_PATH):
        copyfile('{}/{}'.format(GAME_SAVE_PATH, name), '{}/{}'.format(file_path, name))
    pause(screen, 'Game saved. Press enter to return.')
    welcome(screen)

def make_new_save(description: str):
    save_number = get_last_save_number() + 1
    path = '{}/{}'.format(MANAGER_PATH, save_number)
    if not exists(path):
        makedirs(path)
    file_path = '{}/files'.format(path)
    if not exists(file_path):
        makedirs(file_path)
    metadata_path = '{}/metadata'.format(path)
    with open(metadata_path, 'w') as f:
        f.write(dumps({
            'save_number': save_number,
            'date': str(datetime.now().replace(microsecond=0)),
            'description': description
        }))
    set_last_save_number(save_number)
    return (save_number, path, file_path)

def set_last_save_number(number: int):
    metadata_path = '{}/metadata'.format(MANAGER_PATH)
    if not exists(metadata_path):
        with open(metadata_path, 'w') as f:
            f.write(dumps({
                'last_save_number': number
            }))
    with open(metadata_path, 'r') as f:
        j = loads(f.read())
    j['last_save_number'] = number
    with open(metadata_path, 'w') as f:
        f.write(dumps(j))

def get_last_save_number():
    metadata_path = '{}/metadata'.format(MANAGER_PATH)
    if not exists(metadata_path):
        with open(metadata_path, 'w') as f:
            f.write(dumps({
                'last_save_number': 0
            }))
        return 0
    with open(metadata_path, 'r') as f:
        return loads(f.read())['last_save_number']

def menu(screen, tasks, header=None, reverse=False):
    if not header: header = []
    task = None
    args = (screen,)
    while task is None:
        screen.clear()
        for item in header:
            if item is None: continue
            if isinstance(item, tuple):
                addstr(screen, "{}".format(item[0]), item[1])
            else:
                addstr(screen, "{}".format(item))
        for k in sorted(tasks, key=lambda k: int(k) if str(k).isdigit() else float('-inf'), reverse=reverse):
        #for k, v in tasks.items():
            v = tasks[k]
            if k is None or v[0] is None: continue
            if len(v) > 2:
                addstr(screen, "{}. {}".format(k, v[0]), v[1])
            else:
                addstr(screen, "{}. {}".format(k, v[0]))
        data = get_str(screen)
        if data.isnumeric():
            data = int(data)
        if data not in tasks: continue
        selected_task = tasks[data]
        task = selected_task[1 if len(selected_task) < 3 else 2]
        if len(task) > 1: args = tuple(task[1:])
        task = task[0]
    if task is None: return menu(screen, tasks, header)
    task(*args)

if __name__ == "__main__":
    try:
        wrapper(main)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        pass
    except Exception as e:
        exception(e)
