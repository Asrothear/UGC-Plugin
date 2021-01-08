#################################### UGC BGS Companion ##############################################
#####################################################################################################
######################## V !! DO NOT CHANGE ANY OF THIS !! V ########################################
import sys
from urllib.parse import quote
from urllib.request import urlopen
import tkinter.messagebox as tkMessageBox
import tkinter as tk
import tkinter.ttk as ttk
from pathlib import Path
import myNotebook as nb
import requests
import json
import logging
import os.path
import ugc_updater
from config import config
from requests.utils import DEFAULT_CA_BUNDLE_PATH
from dataclasses import dataclass
#####################################################################################################
######################## V !! DO NOT CHANGE ANY OF THIS !! V ########################################
@dataclass
class _config:
    SEND_TO_URL = 'https://asrothear.de/ugc/qls.php'
    STATE_URL = 'https://asrothear.de/ugc/get_state.php'
    TICK = 'https://asrothear.de/ugc/tick.php'
    G_CMD = 'https://asrothear.de/ugc/plugin.php'
    __VERSION__ = 2.0 # DONT TOUCH ME !!
    __BRANCH__ = "beta"# DONT TOUCH ME !!
    CONFIG_MAIN = 'UGC-Plugin' # DONT TOUCH ME !!
    HOME = str(Path.home()).replace("\\", "/")
    plugin_name = os.path.basename(os.path.dirname(__file__))
    paras = None
    rurl = None
    wurl = None
    plugin_dir = None
    debug = False
    debug_cfg = None
    cmd = None
    update = None
    update_cfg = None

ugc = _config()
ugc.paras = {'pv':ugc.__VERSION__, "br":ugc.__BRANCH__}
#####################################################################################################
############################ V !! New Logging function !! V #########################################
######################## V !! NEVER EVER CHANGE ANY OF THIS !! V ####################################
#####################################################################################################
ugc_log = logging.getLogger(f'{ugc.plugin_name}')
if not ugc_log.hasHandlers():
    level = logging.DEBUG
    ugc_log.setLevel(level)
    logger_channel = logging.StreamHandler()
    logger_channel.setLevel(level)
    logger_formatter = logging.Formatter(f'%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger_formatter.default_time_format = '%Y-%m-%d %H:%M:%S'
    logger_formatter.default_msec_format = '%s.%03d'
    logger_channel.setFormatter(logger_formatter)
    ugc_log.addHandler(logger_channel)
    #ugc_log.debug("debug") #Seems to works only on EDMC Debug mode
    #ugc_log.warning("Stawarningrting")
    #ugc_log.error("error")
    #ugc_log.critical("critical")
    #ugc_log.info("info")

def plugin_start(plugin_dir):
    ugc_log.info(""+str(ugc.__VERSION__)+" "+str(ugc.__BRANCH__))
    fetch_debug()
    ugc_log.debug(str(ugc.debug))
    fetch_gl_cmd()
    fetch_update()
    get_ugc_tick()
    ugc.plugin_dir = plugin_dir
    if not config.get("ugc_wurl"):
        config.set("ugc_wurl", ugc.SEND_TO_URL)
    if not config.get("ugc_rurl"):
        config.set("ugc_rurl", ugc.STATE_URL)
    if ugc.cmd['force_url']:
        ugc_log.info("REURL")
        config.set("ugc_wurl", ugc.SEND_TO_URL)
        config.set("ugc_rurl", ugc.STATE_URL)
    ugc.rurl = config.get("ugc_rurl")
    ugc.wurl = config.get("ugc_wurl")
    if ugc.debug:
        ugc_log.debug(str(ugc.rurl))
        ugc_log.debug(str(ugc.wurl))
        ugc_log.debug(str(ugc.cmd))
        ugc_log.debug(str(ugc.tick))
    get_sys_state()
    return ("UGC-Plugin")

def fetch_gl_cmd():
    ugc.cmd = requests.get(ugc.G_CMD, verify=False)
    ugc.cmd = ugc.cmd.content.decode()
    ugc.cmd = json.loads(ugc.cmd)
    print(ugc.cmd['force_url'])
    return(ugc.cmd)

# start python3
def plugin_start3(plugin_dir):
    return plugin_start(plugin_dir)

# plugin stop
def plugin_stop():
    if ugc.update:
        if ugc.debug:
            ugc_log.debug("Updating on close")
        plugin_update()
# plugin prefs
def plugin_prefs(parent, cmdr, is_beta):
    PADX = 10
    BUTTONX = 12	# indent Checkbuttons and Radiobuttons
    PADY = 2
    ugc.wurl = config.get("ugc_wurl")
    ugc.rurl = config.get("ugc_rurl")
    frame = nb.Frame(parent)
    #Config Entry for Data-Receiver URL
    ugc.wurl_label = nb.Label(frame, text="Sende URL")
    ugc.wurl_label.grid(row=11, padx=PADX, sticky=tk.W)
    ugc.wurl_cfg = nb.Entry(frame)
    ugc.wurl_cfg.grid(row=11, column=1, padx=PADX, pady=PADY, sticky=tk.EW)
    ugc.wurl_cfg.insert(0,ugc.wurl)
    #Config Entry for Data-Receiver URL
    ugc.rurl_label = nb.Label(frame, text="State URL")
    ugc.rurl_label.grid(row=12, padx=PADX, sticky=tk.W)
    ugc.rurl_cfg = nb.Entry(frame)
    ugc.rurl_cfg.grid(row=12, column=1, padx=PADX, pady=PADY, sticky=tk.EW)
    ugc.rurl_cfg.insert(0,ugc.rurl)
    #config interface
    nb.Checkbutton(frame, text="Alle Zeigen", variable=ugc.show_all).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Checkbutton(frame, text="Auto Update", variable=ugc.update_cfg).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Checkbutton(frame, text="Debug", variable=ugc.debug_cfg).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Label(frame, text="Textfarben: ").grid(columnspan=2, padx=5, pady=(2,0), sticky=tk.W)
    nb.Label(frame, text="Green: Start Up").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="Orange: Bussy").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="White: Idle").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="Version: "+str(ugc.__VERSION__)+" "+str(ugc.__BRANCH__)).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    return frame
#store config
def prefs_changed(cmdr, is_beta):
    config.set('ugc_wurl', ugc.wurl_cfg.get().strip())
    config.set('ugc_rurl', ugc.rurl_cfg.get().strip())
    config.set('ugc_debug', ugc.debug_cfg.get())
    config.set('ugc_update', ugc.update_cfg.get())
    config.set('ugc_show_all', ugc.show_all.get())
    fetch_debug()
    get_sys_state()
    updateMainUi()

# plugin Display im EDMC Main-Window
def plugin_app(parent):
    frame = tk.Frame(parent)
    ugc.emptyFrame = tk.Frame(frame)
    frame.columnconfigure(1, weight=1)

    ugc.widget_tick_label = tk.Label(frame)
    ugc.widget_tick_value = tk.Label(frame)
    ugc.widget_systems_label = tk.Label(frame)
    ugc.widget_systems_value = tk.Label(frame)

    ugc.frame = frame
    updateMainUi(systems_color="green")
    #ugc.widget_systems_value["foreground"] = "green"
    return ugc.frame

# get Debug state for start up
def fetch_debug():
    ugc.debug_cfg = tk.IntVar(value=config.getint("ugc_debug"))
    ugc.debug_cfg = ugc.debug_cfg.get()
    config.set("ugc_debug", ugc.debug_cfg)
    ugc.debug_cfg = tk.IntVar(value=config.getint("ugc_debug"))
    ugc.debug = ugc.debug_cfg.get()
    if ugc.debug == 1:
        ugc.debug = True
    else:
        ugc.debug = False
    
    return(ugc.debug)

def fetch_update():
    ugc.update_cfg = tk.IntVar(value=config.getint("ugc_update_first"))
    ugc.update = ugc.update_cfg.get()
    if ugc.update == 0:
        if ugc.debug:
            ugc_log.debug("Updating")
        config.set("ugc_update_first", 1)
        config.set("ugc_update", 1)
        plugin_update()
    ugc.update_cfg = tk.IntVar(value=config.getint("ugc_update"))
    ugc.update = ugc.update_cfg.get()
    if ugc.update == 1:
        ugc.update = True
    else:
        ugc.update = False
    return(ugc.update)


# more element in one print line
def pprint_list(liste, maxlen=40):
    if isinstance(liste, str):
        return liste
    if (len(liste) == 0):
        return list()
    if (isinstance(liste, list) and
       (len(liste) == 1)):
        return liste[0]
    newlist = list()
    newline = liste[0]
    for element in liste[1:]:
        if (len(newline)+2+len(element)<=maxlen):
            newline += ", "+element
        else:
            newlist.append(newline)
            newline = element
    newlist.append(newline)
    string = ""
    for element in newlist:
        string += element + "\n"
    return string[:-1]

# get all system if list_all
def fetch_show_all():
    ugc.show_all = tk.IntVar(value=config.getint("ugc_show_all"))
    ugc.show_all = ugc.show_all.get()
    config.set("ugc_show_all", ugc.show_all)
    ugc.show_all = tk.IntVar(value=config.getint("ugc_show_all"))
    return(ugc.show_all)

def get_sys_state():
    fetch_show_all()
    ugc.rurl = config.get("ugc_rurl")
    ugc.sys_state = requests.get(ugc.rurl, params=ugc.paras, verify=False)
    jsonstring = ugc.sys_state.content.decode()
    systemlist = json.loads(jsonstring)
    if ugc.show_all.get():
        ugc.sys_state   = pprint_list(systemlist)
    else:
        ugc.sys_state = pprint_list(systemlist[0])
    return(ugc.sys_state)

def get_ugc_tick():
    ugc.tick = requests.get(ugc.TICK, verify=False)
    ugc.tick = ugc.tick.content.decode()
    ugc.tick = json.loads(ugc.tick)
    ugc.tick   = pprint_list(ugc.tick)
    return(ugc.tick)
#
def updateMainUi(tick_color="orange", systems_color="orange"):
    # Last tick
    get_ugc_tick()
    ugc.widget_tick_label.grid(row=0, column=0, sticky=tk.W)
    ugc.widget_tick_label["text"] = "Last Tick:"
    ugc.widget_tick_value.grid(row=0, column=1, sticky=tk.EW)
    ugc.widget_tick_value["text"] = ugc.tick
    ugc.widget_tick_value["foreground"] = tick_color

    # List systems
    ugc.widget_systems_label.grid(row=1, column=0, sticky=tk.W)
    ugc.widget_systems_label["text"] = "Systems:"
    ugc.widget_systems_value.grid(row=1, column=1, sticky=tk.EW)
    ugc.widget_systems_value["text"] = ugc.sys_state
    ugc.widget_systems_value["foreground"] = systems_color
#
def plugin_update():
    auto_updater = ugc_updater.ugc_updater()
    downloaded = auto_updater.download_latest()
    if downloaded:
        auto_updater.make_backup()
        auto_updater.clean_old_backups()
        auto_updater.extract_latest()

def journal_entry(cmdr, is_beta, system, station, entry, state):
    data = entry
    updateMainUi(systems_color="orange")
    if data['event'] == 'Market':
        with open(''+ugc.HOME+'/Saved Games/Frontier Developments/Elite Dangerous/market.json', 'r') as myfile:
            m_data=myfile.read()
            data = json.loads(m_data)
            if ugc.debug:
                ugc_log.debug(data)
    data['user'] = cmdr
    data['ugc_p_version'] = ugc.__VERSION__
    data['ugc_p_branch'] = ugc.__BRANCH__
    data['data_system'] = system
    
    headers = { 'Content-type': 'application/json', 'Accept': 'text/plain' }
    jsonString = json.dumps(data).encode('utf-8')

    if ugc.debug:
        ugc_log.debug("UGC-DEBUG: PATH: "+DEFAULT_CA_BUNDLE_PATH)
        ugc_log.debug("UGC-DEBUG: start req...")
        ugc_log.debug("UGC-DEBUG: JSON:"+ str(jsonString))
    response = requests.post(ugc.wurl, data=jsonString, headers=headers, verify=False)

    if ugc.debug:
        ugc_log.debug("UGC-DEBUG: req sent. ERROR:"+str(response.status_code))
        ugc_log.debug("UGC-DEBUG: "+ugc.sys_state)
    get_sys_state()
    updateMainUi(tick_color="white", systems_color="white")
