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
import logging as logs
import os
import os.path
import ugc_updater
import ugc_crypt
from config import config
from requests.utils import DEFAULT_CA_BUNDLE_PATH
from dataclasses import dataclass
#####################################################################################################
######################## V !! DO NOT CHANGE ANY OF THIS !! V ########################################
@dataclass
class _config:
    SEND_TO_URL = 'https://api.ugc-tools.de/api/v1/QLS'
    STATE_URL = 'https://api.ugc-tools.de/api/v1/State'
    TICK = 'https://api.ugc-tools.de/api/v1/Tick'
    G_CMD = 'https://api.ugc-tools.de/api/v1/PluginControll'
    __VERSION__ = "3.0" # DONT TOUCH ME !!
    __MINOR__ = "0" # DONT TOUCH ME !!
    __BRANCH__ = "rel.3"# DONT TOUCH ME !!
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
    CMDr = None
    Hash = None
    UUID = None
    Crypt = None
    hwID = None
    send_cmdr = None
    send_cmdr_cfg = None
    verify_token = ""
ugc = _config()
ugc.paras = {'Content-type': 'application/json', 'Accept': 'text/plain', 'version':ugc.__VERSION__, "br":ugc.__MINOR__,"branch":ugc.__BRANCH__, "cmdr":str(ugc.send_cmdr), "uuid":ugc.UUID, "token":ugc.Hash}
#####################################################################################################
############################ V !! New Logging function !! V #########################################
######################## V !! NEVER EVER CHANGE ANY OF THIS !! V ####################################
#####################################################################################################
ugc_log = logs.getLogger(f'{ugc.plugin_name}')
if not ugc_log.hasHandlers():
    level = logs.DEBUG
    ugc_log.setLevel(level)
    ugc_log_channel = logs.StreamHandler()
    ugc_log_channel.setLevel(level)
    ugc_log_formatter = logs.Formatter(f'%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ugc_log_formatter.default_time_format = '%Y-%m-%d %H:%M:%S'
    ugc_log_formatter.default_msec_format = '%s.%03d'
    ugc_log_channel.setFormatter(ugc_log_formatter)
    ugc_log.addHandler(ugc_log_channel)
    #ugc_log.debug("debug") #Seems to works only on EDMC Debug mode
    #ugc_log.warning("Stawarningrting")
    #ugc_log.error("error")
    #ugc_log.critical("critical")
    #ugc_log.info("info")

def plugin_start(plugin_dir):
    ugc_log.info(""+str(ugc.__VERSION__)+"."+ugc.__MINOR__+" "+str(ugc.__BRANCH__))
    ugc.Crypt = ugc_crypt.ugc_crypt()
    fetch_debug()
    ugc_log.debug(str(ugc.debug))
    fetch_gl_cmd()
    fetch_update()
    get_ugc_tick()
    fetch_send_cmdr()
    ugc.plugin_dir = plugin_dir
    if not config.get_str("ugc_wurl"):
        config.set("ugc_wurl", ugc.SEND_TO_URL)
    if not config.get_str("ugc_rurl"):
        config.set("ugc_rurl", ugc.STATE_URL)
    ugc.rurl = config.get_str("ugc_rurl")
    ugc.wurl = config.get_str("ugc_wurl")
    if ugc.debug:
        ugc_log.debug(str(ugc.rurl))
        ugc_log.debug(str(ugc.wurl))
        ugc_log.debug(str(ugc.cmd))
        ugc_log.debug(str(ugc.tick))
    if config.get_str("ugc_cmdr"):
        ugc.CMDr = config.get_str("ugc_cmdr")
        crypter()
    fetch_show_all()
    get_sys_state()
    return ("UGC-Plugin")

def crypter():
    if not ugc.hwID:
            ugc.hwID = ugc.Crypt.ghwid()
    if not ugc.UUID:
            ugc.UUID = str(ugc.Crypt.muuid(ugc.CMDr,ugc.hwID)).replace("'","|")
    if not config.get_str("ugc_token"):
        config.set("ugc_token", ugc.Crypt.sign(ugc.CMDr,ugc.hwID))
        ugc.Hash = config.get_str("ugc_token")
    else:
        ugc.Hash = config.get_str("ugc_token")
    if ugc.debug:
        ugc_log.info(ugc.CMDr)
        ugc_log.info(ugc.UUID)
        ugc_log.info(ugc.Hash)
    if not ugc.Crypt.verify(ugc.CMDr, ugc.Hash):
        ugc.Hash = ugc.Crypt.sign(ugc.CMDr,ugc.hwID)

def fetch_gl_cmd():
    r_cmd = requests.get(ugc.G_CMD)
    if(r_cmd.status_code > 202):
        updateMainUi(tick_color="red", systems_color="red")
    ugc.cmd = r_cmd.content.decode()
    ugc.cmd = json.loads(ugc.cmd)
    if ugc.cmd['force_url']:
        ugc_log.info("REURL")
        config.set("ugc_wurl", ugc.SEND_TO_URL)
        config.set("ugc_rurl", ugc.STATE_URL)
    if ugc.cmd['force_update']:
        plugin_update()
    return(ugc.cmd)

# start python3
def plugin_start3(plugin_dir):
    return plugin_start(plugin_dir)

# plugin stop
def plugin_stop():
    ugc_log.debug("Closing")
    if ugc.update:
        if ugc.debug:
            ugc_log.debug("Updating on close")
        plugin_update()
# plugin prefs
def plugin_prefs(parent, cmdr, is_beta):
    if not config.get_str("ugc_cmdr"):
        config.set("ugc_cmdr", cmdr)
        ugc.CMDr = cmdr
        crypter()
    ugc.paras = {'Content-type': 'application/json', 'Accept': 'text/plain', 'version':ugc.__VERSION__, "br":ugc.__MINOR__,"branch":ugc.__BRANCH__,"cmdr":str(ugc.send_cmdr), "uuid":ugc.UUID, "token":ugc.Hash}
    PADX = 10
    BUTTONX = 12	# indent Checkbuttons and Radiobuttons
    PADY = 2
    ugc.wurl = config.get_str("ugc_wurl")
    ugc.rurl = config.get_str("ugc_rurl")
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
    #Config Entry for Verify-Token
    ugc.vtk_label = nb.Label(frame, text="Verify Token")
    ugc.vtk_label.grid(row=13, padx=PADX, sticky=tk.W)
    ugc.vtk_cfg = nb.Entry(frame)
    ugc.vtk_cfg.grid(row=13, column=1, padx=PADX, pady=PADY, sticky=tk.EW)
    ugc.vtk_cfg.insert(0,"")
    #config interface
    nb.Checkbutton(frame, text="CMDr Namen übertragen", variable=ugc.send_cmdr_cfg).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Checkbutton(frame, text="Alle Zeigen", variable=ugc.show_all).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Checkbutton(frame, text="Auto Update", variable=ugc.update_cfg).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Checkbutton(frame, text="Debug", variable=ugc.debug_cfg).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Label(frame, text="Textfarben: ").grid(columnspan=2, padx=5, pady=(2,0), sticky=tk.W)
    nb.Label(frame, text="Green: Start Up").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="Orange: Bussy").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="White: Idle").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="Red: Error").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="Version: "+str(ugc.__VERSION__)+"."+ugc.__MINOR__+" "+str(ugc.__BRANCH__)).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Label(frame, text="CMDr: "+str(cmdr)).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    
    nb.Button(frame, text="Test", command=lambda:send_test()).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    return frame
#store config
def prefs_changed(cmdr, is_beta):
    config.set('ugc_wurl', ugc.wurl_cfg.get().strip())
    config.set('ugc_rurl', ugc.rurl_cfg.get().strip())
    config.set('ugc_debug', ugc.debug_cfg.get())
    config.set('ugc_update', ugc.update_cfg.get())
    config.set('ugc_show_all', ugc.show_all.get())
    config.set('ugc_send_cmdr', ugc.send_cmdr_cfg.get())
    ugc.verify_token = ugc.vtk_cfg.get().strip()
    fetch_debug()
    fetch_send_cmdr()
    ugc.paras = {'Content-type': 'application/json', 'Accept': 'text/plain', 'version':ugc.__VERSION__, "br":ugc.__MINOR__,"branch":ugc.__BRANCH__,"cmdr":str(ugc.send_cmdr), "uuid":ugc.UUID, "token":ugc.Hash} 
    fetch_show_all()
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
    ugc.debug_cfg = tk.IntVar(value=config.get_int("ugc_debug"))
    ugc.debug_cfg = ugc.debug_cfg.get()
    config.set("ugc_debug", ugc.debug_cfg)
    ugc.debug_cfg = tk.IntVar(value=config.get_int("ugc_debug"))
    ugc.debug = ugc.debug_cfg.get()
    if ugc.debug == 1:
        ugc.debug = True
    else:
        ugc.debug = False
    
    return(ugc.debug)

def fetch_send_cmdr():
    ugc.send_cmdr_cfg = tk.IntVar(value=config.get_int("ugc_send_cmdr_first"))
    ugc.send_cmdr = ugc.send_cmdr_cfg.get()
    if ugc.send_cmdr == 0:
        config.set("ugc_send_cmdr_first", 1)
        config.set("ugc_send_cmdr", 1)
    ugc.send_cmdr_cfg = tk.IntVar(value=config.get_int("ugc_send_cmdr"))
    ugc.send_cmdr = ugc.send_cmdr_cfg.get()
    if ugc.send_cmdr == 1:
        ugc.send_cmdr = True
    else:
        ugc.send_cmdr = False
    return(ugc.send_cmdr)

def fetch_update():
    ugc.update_cfg = tk.IntVar(value=config.get_int("ugc_update_first"))
    ugc.update = ugc.update_cfg.get()
    if ugc.update == 0:
        if ugc.debug:
            ugc_log.debug("Updating")
        config.set("ugc_update_first", 1)
        config.set("ugc_update", 1)
        plugin_update()
    ugc.update_cfg = tk.IntVar(value=config.get_int("ugc_update"))
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
    ugc.show_all = tk.IntVar(value=config.get_int("ugc_show_all"))
    ugc.show_all = ugc.show_all.get()
    config.set("ugc_show_all", ugc.show_all)
    ugc.show_all = tk.IntVar(value=config.get_int("ugc_show_all"))
    return(ugc.show_all)

def get_sys_state():
    ugc.rurl = config.get_str("ugc_rurl")
    sys_state = requests.get(ugc.rurl, headers=ugc.paras)
    if(sys_state.status_code > 202):
        try:
            updateMainUi(tick_color="white", systems_color="red")
        except:
            print("BGS-Plugin")
    if(sys_state.status_code > 405):
        ugc.sys_state = "API-Server ERROR"
    else:        
        jsonstring = sys_state.content.decode()
        systemlist = json.loads(jsonstring)
        if ugc.show_all.get():
            ugc.sys_state   = pprint_list(systemlist)
        else:
            ugc.sys_state = pprint_list(systemlist[0])
    return(ugc.sys_state)

def get_ugc_tick():
    tick = requests.get(ugc.TICK)
    if(tick.status_code > 202):
        updateMainUi(tick_color="white", systems_color="red")
    if(tick.status_code > 405):
        ugc.tick = "API-Server ERROR"
    else: 
        ugc.tick = tick.content.decode()
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
    ugc.paras = {'Content-type': 'application/json', 'Accept': 'text/plain', 'version':ugc.__VERSION__, "br":ugc.__MINOR__,"branch":ugc.__BRANCH__,"cmdr":str(ugc.send_cmdr), "uuid":ugc.UUID, "token":ugc.Hash}
    data = entry
    updateMainUi(systems_color="orange")
    if data['event'] == 'Market':
        with open(''+ugc.HOME+'/Saved Games/Frontier Developments/Elite Dangerous/market.json', 'r') as myfile:
            m_data=myfile.read()
            data = json.loads(m_data)
            if ugc.debug:
                ugc_log.debug(data)
    if ugc.send_cmdr == 1:
        data['user'] = cmdr

    data["ugc_token_v2"] = dict()
    data["ugc_token_v2"]["uuid"] = ugc.UUID
    data["ugc_token_v2"]["token"] = ugc.Hash
    data["ugc_token_v2"]["verify"] = ugc.verify_token
    data['ugc_p_version'] = ugc.__VERSION__
    data['ugc_p_minor'] = ugc.__MINOR__
    data['ugc_p_branch'] = ugc.__BRANCH__
    
    headers = { 'Content-type': 'application/json', 'Accept': 'text/plain' }
    jsonString = json.dumps(data).encode('utf-8')

    if ugc.debug:
        ugc_log.debug("UGC-DEBUG: PATH: "+DEFAULT_CA_BUNDLE_PATH)
        ugc_log.debug("UGC-DEBUG: start req...")
        ugc_log.debug("UGC-DEBUG: JSON:"+ str(jsonString))
    response = requests.post(ugc.wurl, data=jsonString, headers=headers)

    if ugc.debug:
        ugc_log.debug("UGC-DEBUG: req sent. ERROR:"+str(response.status_code))
        ugc_log.debug("UGC-DEBUG: "+ugc.sys_state)
    get_sys_state()
    if(response.status_code <= 202):
        updateMainUi(tick_color="white", systems_color="white")
    else:
        updateMainUi(tick_color="red", systems_color="red")

def cmdr_data(data, is_beta):
    if data.get('commander') is None or data['commander'].get('name') is None:
        raise ValueError("this isn't possible")
    CMDr = data['commander']['name']
    if not config.get_str("ugc_cmdr"):
        config.set("ugc_cmdr", CMDr)
        ugc.CMDr = CMDr
        crypter()

def send_test():
    ugc.paras = {'Content-type': 'application/json', 'Accept': 'text/plain', 'version':ugc.__VERSION__, "br":ugc.__MINOR__,"branch":ugc.__BRANCH__,"cmdr":str(ugc.send_cmdr), "uuid":ugc.UUID, "token":ugc.Hash}
    if ugc.verify_token =="":
        if ugc.vtk_cfg.get().strip() !="":
            ugc.verify_token = ugc.vtk_cfg.get().strip()
    data = dict()
    config.set('ugc_wurl', ugc.wurl_cfg.get().strip())
    config.set('ugc_rurl', ugc.rurl_cfg.get().strip())
    ugc.wurl = config.get_str("ugc_wurl")
    ugc.rurl = config.get_str("ugc_rurl")
    if ugc.send_cmdr == 1:
        data['user'] = ugc.CMDr
    updateMainUi(systems_color="orange")
    data["event"] = "test"
    data["ugc_token_v2"] = dict()
    data["ugc_token_v2"]["uuid"] = ugc.UUID
    data["ugc_token_v2"]["token"] = ugc.Hash
    data["ugc_token_v2"]["verify"] = ugc.verify_token
    
    data['ugc_p_version'] = ugc.__VERSION__
    data['ugc_p_minor'] = ugc.__MINOR__
    data['ugc_p_branch'] = ugc.__BRANCH__
    data['payload'] = "bärenkatapult"
    
    headers = { 'Content-type': 'application/json', 'Accept': 'text/plain' }
    jsonString = json.dumps(data).encode('utf-8')

    ugc_log.debug("UGC-DEBUG:TEST start req...")
    ugc_log.debug("UGC-DEBUG:TEST JSON: "+ str(jsonString))
    response = requests.post(ugc.wurl, data=jsonString, headers=headers)
    if ugc.debug:
        ugc_log.debug("UGC-DEBUG: req sent. ERROR:"+str(response.status_code))
        ugc_log.debug("UGC-DEBUG: "+ugc.sys_state)
    get_sys_state()
    if(response.status_code <= 202):
        updateMainUi(tick_color="white", systems_color="white")
    else:
        updateMainUi(tick_color="red", systems_color="red")