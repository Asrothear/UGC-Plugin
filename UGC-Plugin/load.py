#################################### UGC BGS Companion ##############################################
#####################################################################################################
######################## V !! DO NOT CHANGE ANY OF THIS !! V ########################################
from __future__ import print_function
DEBUG = False
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

#####################################################################################################
######################## V !! DO NOT CHANGE ANY OF THIS !! V ########################################
RE_URL = 'https://asrothear.de/ugc/plugin.php' # DONT TOUCH ME !!
SEND_TO_URL = 'https://asrothear.de/ugc/qls.php' #for config init. can be changed in plugin cfg-tab
STATE_URL = 'https://asrothear.de/ugc/api_state.php' #for config init. can be changed in plugin cfg-tab
TICK = 'https://asrothear.de/ugc/api_tick.php' #for config init. can be changed in plugin cfg-tab
__VERSION__ = 2.0 # DONT TOUCH ME !!
__BRANCH__ = "beta"# DONT TOUCH ME !!
PARAMS = {'pv':__VERSION__, "br":__BRANCH__} # DONT TOUCH ME !!
this = sys.modules[__name__] # DONT TOUCH ME !!
this.CONFIG_MAIN = 'UGC-Plugin' # DONT TOUCH ME !!
HOME = str(Path.home())
HOME = HOME.replace("\\", "/")
#####################################################################################################
############################ V !! New Logging function !! V #########################################
######################## V !! NEVER EVER CHANGE ANY OF THIS !! V ####################################
#####################################################################################################
plugin_name = os.path.basename(os.path.dirname(__file__))
ugc_log = logging.getLogger(f'{plugin_name}')
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
    ugc_log.info(""+str(__VERSION__)+" "+str(__BRANCH__))
    fetch_debug()
    ugc_log.debug(str(this.debug))
    fetch_gl_cmd()
    fetch_update()
    get_ugc_tick()
    this.plugin_dir = plugin_dir
    if not config.get("ugc_wurl"):
        config.set("ugc_wurl", SEND_TO_URL)
    if not config.get("ugc_rurl"):
        config.set("ugc_rurl", STATE_URL)
    if this.re_url:
        ugc_log.info("REURL")
        config.set("ugc_wurl", SEND_TO_URL)
        config.set("ugc_rurl", STATE_URL)
    this.ugc_rurl = config.get("ugc_rurl")
    this.ugc_wurl = config.get("ugc_wurl")
    if this.debug:
        ugc_log.debug(str(this.ugc_rurl))
        ugc_log.debug(str(this.ugc_wurl))
        ugc_log.debug(str(this.re_url))
        ugc_log.debug(str(this.ugc_tick))
    get_sys_state(PARAMS)
    return ("UGC-Plugin")

def fetch_gl_cmd():
    this.re_url = requests.get(RE_URL, verify=False)
    this.re_url = this.re_url.content.decode()
    this.re_url = json.loads(this.re_url)
    this.re_url = json.loads(this.re_url)
    this.re_url = json.loads(this.re_url)
    return(this.re_url)

# start python3
def plugin_start3(plugin_dir):
    return plugin_start(plugin_dir)

# plugin stop
def plugin_stop():
    if this.update:
        if this.debug:
            ugc_log.debug("Updating on close")
        plugin_update()
# plugin prefs
def plugin_prefs(parent, cmdr, is_beta):
    PADX = 10
    BUTTONX = 12	# indent Checkbuttons and Radiobuttons
    PADY = 2
    this.ugc_wurl = config.get("ugc_wurl")
    this.ugc_rurl = config.get("ugc_rurl")
    frame = nb.Frame(parent)
    #Config Entry for Data-Receiver URL
    this.ugc_wurl_label = nb.Label(frame, text="Sende URL")
    this.ugc_wurl_label.grid(row=11, padx=PADX, sticky=tk.W)
    this.ugc_wurl_cfg = nb.Entry(frame)
    this.ugc_wurl_cfg.grid(row=11, column=1, padx=PADX, pady=PADY, sticky=tk.EW)
    this.ugc_wurl_cfg.insert(0,this.ugc_wurl)
    #Config Entry for Data-Receiver URL
    this.ugc_rurl_label = nb.Label(frame, text="State URL")
    this.ugc_rurl_label.grid(row=12, padx=PADX, sticky=tk.W)
    this.ugc_rurl_cfg = nb.Entry(frame)
    this.ugc_rurl_cfg.grid(row=12, column=1, padx=PADX, pady=PADY, sticky=tk.EW)
    this.ugc_rurl_cfg.insert(0,this.ugc_rurl)
    #config interface
    nb.Checkbutton(frame, text="Alle Zeigen", variable=this.ugc_show_all).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Checkbutton(frame, text="Auto Update", variable=this.ugc_update).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Checkbutton(frame, text="Debug", variable=this.ugc_debug).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Label(frame, text="Textfarben: ").grid(columnspan=2, padx=5, pady=(2,0), sticky=tk.W)
    nb.Label(frame, text="Green: Start Up").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="Orange: Bussy").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="White: Idle").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="Version: "+str(__VERSION__)+" "+str(__BRANCH__)).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    return frame
#store config
def prefs_changed(cmdr, is_beta):
    paras = {'pv':__VERSION__, "br":__BRANCH__, 'user':cmdr}
    config.set('ugc_wurl', this.ugc_wurl_cfg.get().strip())
    config.set('ugc_rurl', this.ugc_rurl_cfg.get().strip())
    config.set('ugc_debug', this.ugc_debug.get())
    config.set('ugc_update', this.ugc_update.get())
    config.set('ugc_show_all', this.ugc_show_all.get())
    fetch_debug()
    get_sys_state(paras)
    updateMainUi()

# plugin Display im EDMC Main-Window
def plugin_app(parent):
    frame = tk.Frame(parent)
    this.emptyFrame = tk.Frame(frame)
    frame.columnconfigure(1, weight=1)

    this.widget_tick_label = tk.Label(frame)
    this.widget_tick_value = tk.Label(frame)
    this.widget_systems_label = tk.Label(frame)
    this.widget_systems_value = tk.Label(frame)

    this.frame = frame
    updateMainUi(systems_color="green")
    #this.widget_systems_value["foreground"] = "green"
    return this.frame

# get Debug state for start up
def fetch_debug():
    this.ugc_debug = tk.IntVar(value=config.getint("ugc_debug"))
    this.ugc_debug = this.ugc_debug.get()
    config.set("ugc_debug", this.ugc_debug)
    this.ugc_debug = tk.IntVar(value=config.getint("ugc_debug"))
    this.debug = this.ugc_debug.get()
    if this.debug == 1:
        this.debug = True
    else:
        this.debug = False
    return(this.debug)

def fetch_update():
    ugc_update = tk.IntVar(value=config.getint("ugc_update_first"))
    ugc_update = ugc_update.get()
    if ugc_update == 0:
        if this.debug:
            ugc_log.debug("Updating")
        config.set("ugc_update_first", 1)
        config.set("ugc_update", 1)
        plugin_update()
    this.ugc_update = tk.IntVar(value=config.getint("ugc_update"))
    this.update = this.ugc_update.get()
    if this.update == 1:
        this.update = True
    else:
        this.update = False
    return(this.update)


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
    this.ugc_show_all = tk.IntVar(value=config.getint("ugc_show_all"))
    this.ugc_show_all = this.ugc_show_all.get()
    config.set("ugc_show_all", this.ugc_show_all)
    this.ugc_show_all = tk.IntVar(value=config.getint("ugc_show_all"))
    return(this.ugc_show_all)

def get_sys_state(paras):
    fetch_show_all()
    this.ugc_rurl = config.get("ugc_rurl")
    this.sys_state = requests.get(this.ugc_rurl, params=paras, verify=False)
    jsonstring = this.sys_state.content.decode()
    systemlist = json.loads(jsonstring)
    if this.ugc_show_all.get():
        this.sys_state   = pprint_list(systemlist)
    else:
        this.sys_state = pprint_list(systemlist[0])
    return(this.sys_state)

def get_ugc_tick():
    this.ugc_tick = requests.get(TICK, verify=False)
    this.ugc_tick = this.ugc_tick.content.decode()
    this.ugc_tick = json.loads(this.ugc_tick)
    this.ugc_tick   = pprint_list(this.ugc_tick)
    return(this.ugc_tick)
#
def updateMainUi(tick_color="orange", systems_color="orange"):
    # Last tick
    get_ugc_tick()
    this.widget_tick_label.grid(row=0, column=0, sticky=tk.W)
    this.widget_tick_label["text"] = "Last Tick:"
    this.widget_tick_value.grid(row=0, column=1, sticky=tk.EW)
    this.widget_tick_value["text"] = this.ugc_tick
    this.widget_tick_value["foreground"] = tick_color

    # List systems
    this.widget_systems_label.grid(row=1, column=0, sticky=tk.W)
    this.widget_systems_label["text"] = "Systems:"
    this.widget_systems_value.grid(row=1, column=1, sticky=tk.EW)
    this.widget_systems_value["text"] = this.sys_state
    this.widget_systems_value["foreground"] = systems_color
#
def plugin_update():
    auto_updater = ugc_updater.ugc_updater()
    downloaded = auto_updater.download_latest()
    if downloaded:
        auto_updater.make_backup()
        auto_updater.clean_old_backups()
        auto_updater.extract_latest()

def journal_entry(cmdr, is_beta, system, station, entry, state):
    paras = {'pv':__VERSION__, "br":__BRANCH__, 'user':cmdr}
    data = entry
    updateMainUi(systems_color="orange")
    if data['event'] == 'Market':
        with open(''+HOME+'/Saved Games/Frontier Developments/Elite Dangerous/market.json', 'r') as myfile:
            m_data=myfile.read()
            data = json.loads(m_data)
            if this.debug:
                ugc_log.debug(data)
    data['user'] = cmdr
    data['ugc_p_version'] = __VERSION__
    data['data_system'] = system
    
    headers = { 'Content-type': 'application/json', 'Accept': 'text/plain' }
    jsonString = json.dumps(data).encode('utf-8')

    if this.debug:
        ugc_log.debug("UGC-DEBUG: PATH: "+DEFAULT_CA_BUNDLE_PATH)
        ugc_log.debug("UGC-DEBUG: start req...")
        ugc_log.debug("UGC-DEBUG: JSON:", jsonString)
    response = requests.post(this.ugc_wurl, data=jsonString, headers=headers, verify=False)

    if this.debug:
        ugc_log.debug("UGC-DEBUG: req sent. ERROR:"+str(response.status_code))
        ugc_log.debug("UGC-DEBUG: "+this.sys_state)
    get_sys_state(paras)
    updateMainUi(tick_color="white", systems_color="white")
