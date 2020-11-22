#################################### UGC BGS Companion ##############################################
#####################################################################################################
######################## V !! DO NOT CHANGE ANY OF THIS !! V ########################################
from __future__ import print_function
DEBUG = False
import sys
if (sys.version_info.major == 2):
    # Python 2
    PY2 = True
    PY3 = False
    from urllib2 import quote
    from urllib2 import urlopen
    import Tkinter as tk
    import tkMessageBox
    import ttk
else:
    # Python 3
    PY3 = True
    PY2 = False
    from urllib.parse import quote
    from urllib.request import urlopen
    import tkinter.messagebox as tkMessageBox
    import tkinter as tk
    import tkinter.ttk as ttk
#
#
import myNotebook as nb
import requests
import json
import os.path
import ugc_updater
from config import config
from requests.utils import DEFAULT_CA_BUNDLE_PATH

#####################################################################################################
######################## V !! DO NOT CHANGE ANY OF THIS !! V ########################################

SEND_TO_URL = 'https://asrothear.de/ugc/qls.php' #for config init. can be changed in plugin cfg-tab
STATE_URL = 'https://asrothear.de/ugc/get_state.php' #for config init. can be changed in plugin cfg-tab
TICK = 'https://asrothear.de/ugc/tick.php' #for config init. can be changed in plugin cfg-tab
__VERSION__ = "1.4" # DONT TOUCH ME !!
__BRANCH__ = "dev" # DONT TOUCH ME !!
PARAMS = {'pv':__VERSION__, "br":__BRANCH__} # DONT TOUCH ME !!
this = sys.modules[__name__] # DONT TOUCH ME !!
this.CONFIG_MAIN = 'UGC-Plugin' # DONT TOUCH ME !!

def plugin_start(plugin_dir):
    fetch_debug()
    fetch_update()
    get_ugc_tick()
    this.plugin_dir = plugin_dir
    if not config.get("ugc_wurl"):
        config.set("ugc_wurl", SEND_TO_URL)
    if not config.get("ugc_rurl"):
        config.set("ugc_rurl", STATE_URL)
    this.ugc_rurl = config.get("ugc_rurl")
    this.ugc_wurl = config.get("ugc_wurl")
    get_sys_state(PARAMS)
    return ("UGC-Plugin")

# start python3
def plugin_start3(plugin_dir):
    return plugin_start(plugin_dir)

# plugin stop
def plugin_stop():
    if this.update:
        if this.debug:
            print("Updating on close")
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
            print("Updating")
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
    if PY2:
        if (type(liste) == unicode):
            return liste
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
    if PY2:
        jsonstring = str(this.sys_state.content)
        systemlist = json.loads(jsonstring)
    else:
        jsonstring = this.sys_state.content.decode()
        systemlist = json.loads(jsonstring)
    if this.ugc_show_all.get():
        this.sys_state   = pprint_list(systemlist)
    else:
        this.sys_state = pprint_list(systemlist[0])
    return(this.sys_state)

def get_ugc_tick():
    this.ugc_tick = requests.get(TICK, verify=False)
    if PY2:
        this.ugc_tick = str(this.ugc_tick.content)
        this.ugc_tick = json.loads(this.ugc_tick)
    else:
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

    updateMainUi(systems_color="orange")

    entry['user'] = cmdr
    entry['ugc_p_version'] = __VERSION__
    entry['station_data'] = station
    entry['system_data'] = system
    entry['state_data'] = state
    entry['is_beta_data'] = is_beta
    headers = { 'Content-type': 'application/json', 'Accept': 'text/plain' }
    jsonString = json.dumps(entry).encode('utf-8')

    if this.debug:
        print("UGC-DEBUG: PATH: "+DEFAULT_CA_BUNDLE_PATH)
        print("UGC-DEBUG: start req...")
        print("UGC-DEBUG: JSON:", jsonString)
    if PY2:
        jsonString = str(jsonString).replace("'", "")
    response = requests.post(this.ugc_wurl, data=jsonString, headers=headers, verify=False)

    if this.debug:
        print("UGC-DEBUG: req sent. ERROR:"+str(response.status_code))
        print("UGC-DEBUG: "+this.sys_state)
    get_sys_state(paras)
    updateMainUi(systems_color="white")
