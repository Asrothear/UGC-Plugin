import tkinter as tk
from pathlib import Path
import myNotebook as nb
import requests
import json
import logging as logs
import os
import os.path
from queue import Queue
import threading
from threading import Thread
from time import sleep
import plug
from config import applongname, appname, appversion_nobuild, config, debug_senders, user_agent
from typing import TYPE_CHECKING, Any, List, Literal, Mapping, MutableMapping, Optional, Set, Tuple, Union, cast
import ugc_updater

class This:
    def __init__(self):
        self.parent: tk.Tk
        self.SEND_TO_URL = 'https://api.ugc-tools.de/api/v1/QLS'
        self.STATE_URL = 'https://api.ugc-tools.de/api/v1/State'
        self.TICK = 'https://api.ugc-tools.de/api/v1/Tick'
        self.G_CMD = 'https://api.ugc-tools.de/api/v1/PluginControll'
        self.__VERSION__ = "1.0" # DONT TOUCH ME !!
        self.__MINOR__ = "0" # DONT TOUCH ME !!
        self.__BRANCH__ = ""# DONT TOUCH ME !!
        self.CONFIG_MAIN = 'UGC-Plugin' # DONT TOUCH ME !!
        self.HOME = str(Path.home()).replace("\\", "/")
        self.send_cmdr_cfg = None
        self.send_cmdr = None
        self.show_all = None
        self.show_all_cfg = None
        self.show_all_bgs_cfg = None
        self.show_all_bgs = None
        self.update_cfg = None
        self.update = None
        self.debug_cfg = None
        self.debug = None
        self.shutting_down = False
        self.slow_state_cfg = None
        self.slow_state = None
        self.sys_state = "Start Up"
        self.sys_state_data = None
        self.tick = "Start Up"
        self.vtk_cfg = None
        self.token = None
        self.status = None
        self.old_status = None
        #
        self.session: requests.Session = requests.Session()
        self.queue: Queue = Queue()		# Items to be sent by worker thread
        self.lastlookup: requests.Response  # Result of last system lookup
        self.plugin_name = os.path.basename(os.path.dirname(__file__))        
        #
        self.first = True
        # Game state
        self.multicrew: bool = False  # don't send captain's ship info to EDSM while on a crew
        self.coordinates: Optional[Tuple[int, int, int]] = None
        self.newgame: bool = False  # starting up - batch initial burst of events
        self.newgame_docked: bool = False  # starting up while docked
        self.navbeaconscan: int = 0		# batch up burst of Scan events after NavBeaconScan
        self.system_link: tk.Widget = None
        self.system: tk.Tk = None
        self.system_address: Optional[int] = None  # Frontier SystemAddress
        self.system_population: Optional[int] = None
        self.station_link: tk.Widget = None
        self.station: Optional[str] = None
        self.station_marketid: Optional[int] = None  # Frontier MarketID
        self.on_foot = False
        self.thread: Optional[threading.Thread] = None
        self.dstate: Optional[threading.Thread] = None
        self.lstate: Optional[threading.Thread] = None
        self.get_sys_state: Optional[threading.Thread] = None
        self.QLS: Optional[threading.Thread] = None
        self.log = logs.getLogger(f'{self.plugin_name}')
        self.paras = {'Content-type': 'application/json', 'Accept': 'text/plain', 'version':self.__VERSION__, "br":self.__MINOR__,"branch":self.__BRANCH__, "cmdr":str(self.send_cmdr), "token":self.token}

this = This()

if not this.log.hasHandlers():
    level = logs.DEBUG
    this.log.setLevel(level)
    this_log_channel = logs.StreamHandler()
    this_log_channel.setLevel(level)
    this_log_formatter = logs.Formatter(f'%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    this_log_formatter.default_time_format = '%Y-%m-%d %H:%M:%S'
    this_log_formatter.default_msec_format = '%s.%03d'
    this_log_channel.setFormatter(this_log_formatter)
    this.log.addHandler(this_log_channel)
    #this.log.debug("debug") #Seems to works only on EDMC Debug mode
    #this.log.warning("Stawarningrting")
    #this.log.error("error")
    #this.log.critical("critical")
    #this.log.info("info")

def plugin_start3(plugin_dir: str) -> str:
    this.log.info(""+str(this.__VERSION__)+"."+this.__MINOR__+" "+str(this.__BRANCH__))
    this.log.debug('Starting worker thread...')
    fetch_debug()
    fetch_gl_cmd()
    fetch_update()
    fetch_send_cmdr()
    fetch_show_all()
    fetch_slow_state() 
    #get_ugc_tick()
    if not config.get_str("ugc_wurl"):
        config.set("ugc_wurl", this.SEND_TO_URL)
    if not config.get_str("ugc_rurl"):
        config.set("ugc_rurl", this.STATE_URL)
    if not config.get_str("ugc_token"):
        config.set("ugc_token", "")
    this.rurl = config.get_str("ugc_rurl")
    this.wurl = config.get_str("ugc_wurl")
    this.token = config.get_str("ugc_token")
    if this.debug:
        this.log.debug(str(this.rurl))
        this.log.debug(str(this.wurl))
        this.log.debug(str(this.cmd))
        this.log.debug(str(this.tick))
    if config.get_str("ugc_cmdr"):
        this.CMDr = config.get_str("ugc_cmdr").encode("ascii","replace").decode()
    this.thread = Thread(target=worker, name='UGC worker')
    this.thread.daemon = True
    this.thread.start()
    #get_sys_state()
    this.dstate = Thread(target=Late_State, name='UGC worker')
    this.dstate.daemon = True
    this.dstate.start()
    this.lstate = Thread(target=Loop_State, name='UGC loop worker')
    this.lstate.daemon = True
    this.lstate.start()

    this.log.debug('Done.')
    return this.CONFIG_MAIN

def send_status(Text: str) -> None:
    if not this.status: 
        this.status = this.parent.nametowidget(f".{appname.lower()}.status")
    """Update status text."""
    if not Text:
        Text = this.old_status
    else:
        this.old_status = this.status['text']
    this.status['text'] = Text
    this.status.update_idletasks()

def plugin_stop() -> None:
    """Stop this plugin."""
    this.log.debug('Closing...')
    # Signal thread to close and wait for it
    this.shutting_down = True
    this.queue.put(None)  # Still necessary to get `this.queue.get()` to unblock
    this.thread.join()  # type: ignore
    this.thread = None
    this.session.close()
    this.log.debug('Done.')
    if this.update:
        if this.debug:
            this.log.debug("Updating on close")
        plugin_update()

def plugin_app(parent):
    this.parent = parent
    frame = tk.Frame(parent)
    this.emptyFrame = tk.Frame(frame)
    frame.columnconfigure(1, weight=1)

    this.widget_tick_label = tk.Label(frame)
    this.widget_tick_value = tk.Label(frame)
    this.widget_systems_label = tk.Label(frame)
    this.widget_systems_value = tk.Label(frame)
    this.widget_spacer1 = tk.Label(frame)
    this.widget_spacer2 = tk.Label(frame)
    this.frame = frame
    updateMainUi(systems_color="green")
    #ugc.widget_systems_value["foreground"] = "green"
    return this.frame

def updateMainUi(tick_color="orange", systems_color="orange"):
    # Last tick
    #get_ugc_tick()
    this.widget_tick_label.grid(row=0, column=0, sticky=tk.W)
    this.widget_tick_label["text"] = "Last Tick:"
    this.widget_tick_value.grid(row=0, column=1, sticky=tk.EW)
    this.widget_tick_value["text"] = this.tick
    this.widget_tick_value["foreground"] = tick_color
    this.widget_spacer1["text"] = ""
    this.widget_spacer1.grid(row=2, column=0)
    this.widget_spacer2["text"] = "________________________________________"
    this.widget_spacer2.grid(row=2, column=1)
    #ugc.widget_tick_label["background"] = "black"
    #ugc.widget_tick_value["background"] = "black"

    # List systems
    this.widget_systems_label.grid(row=1, column=0, sticky=tk.W)
    this.widget_systems_label["text"] = "Systems:"
    this.widget_systems_value.grid(row=1, column=1, sticky=tk.EW)
    this.widget_systems_value["text"] = this.sys_state
    this.widget_systems_value["foreground"] = systems_color
    #ugc.widget_systems_label["background"] = "black"
    #ugc.widget_systems_value["background"] = "black"

def plugin_prefs(parent, cmdr, is_beta):
    if not config.get_str("ugc_cmdr"):
        config.set("ugc_cmdr", cmdr.encode("ascii","replace").decode())
        this.CMDr = config.get_str("ugc_cmdr")
    this.paras = {'Content-type': 'application/json', 'Accept': 'text/plain', 'version':this.__VERSION__, "br":this.__MINOR__,"branch":this.__BRANCH__,"cmdr":str(this.send_cmdr),  "token":this.token, "onlyBGS": str(this.show_all_bgs)}
    PADX = 10
    BUTTONX = 12	# indent Checkbuttons and Radiobuttons
    PADY = 2
    this.wurl = config.get_str("ugc_wurl")
    this.rurl = config.get_str("ugc_rurl")
    frame = nb.Frame(parent)
    #Config Entry for Data-Receiver URL
    this.wurl_label = nb.Label(frame, text="Sende URL")
    this.wurl_label.grid(row=11, padx=PADX, sticky=tk.W)
    this.wurl_cfg = nb.Entry(frame)
    this.wurl_cfg.grid(row=11, column=1, padx=PADX, pady=PADY, sticky=tk.EW)
    this.wurl_cfg.insert(0,this.wurl)
    #Config Entry for Data-Receiver URL
    this.rurl_label = nb.Label(frame, text="State URL")
    this.rurl_label.grid(row=12, padx=PADX, sticky=tk.W)
    this.rurl_cfg = nb.Entry(frame)
    this.rurl_cfg.grid(row=12, column=1, padx=PADX, pady=PADY, sticky=tk.EW)
    this.rurl_cfg.insert(0,this.rurl)
    #Config Entry for Verify-Token
    this.vtk_label = nb.Label(frame, text="Token")
    this.vtk_label.grid(row=13, padx=PADX, sticky=tk.W)
    this.vtk_cfg = nb.Entry(frame)
    this.vtk_cfg.grid(row=13, column=1, padx=PADX, pady=PADY, sticky=tk.EW)
    this.vtk_cfg.insert(0,this.token)
    #config interface
    nb.Checkbutton(frame, text="CMDr Namen übertragen", variable=this.send_cmdr_cfg).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Checkbutton(frame, text="Gesamte Liste Zeigen", variable=this.show_all_cfg).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Checkbutton(frame, text="Nur BGS relevante zeigen", variable=this.show_all_bgs_cfg).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Checkbutton(frame, text="Auto Update", variable=this.update_cfg).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Checkbutton(frame, text="Slow State", variable=this.slow_state_cfg).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Checkbutton(frame, text="Debug", variable=this.debug_cfg).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Label(frame, text="Textfarben: ").grid(columnspan=2, padx=5, pady=(2,0), sticky=tk.W)
    nb.Label(frame, text="Green: Start Up").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="Orange: Bussy").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="White: Idle").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="Red: Error").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="Version: "+str(this.__VERSION__)+"."+this.__MINOR__+" "+str(this.__BRANCH__)).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Label(frame, text="CMDr: "+str(cmdr)).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    
    nb.Button(frame, text="Test", command=lambda:send_testth()).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    return frame

def prefs_changed(cmdr, is_beta):
    config.set('ugc_wurl', this.wurl_cfg.get().strip())
    config.set('ugc_rurl', this.rurl_cfg.get().strip())
    config.set('ugc_debug', this.debug_cfg.get())
    config.set('ugc_update', this.update_cfg.get())
    config.set('ugc_show_all', this.show_all_cfg.get())
    config.set('ugc_show_all_bgs', this.show_all_bgs_cfg.get())
    config.set('ugc_send_cmdr', this.send_cmdr_cfg.get())
    config.set("ugc_slow_state", this.slow_state_cfg.get())
    if(this.vtk_cfg.get().strip() != ""):
        config.set('ugc_token', this.vtk_cfg.get().strip())
    this.token = this.vtk_cfg.get().strip()
    this.rurl = config.get_str("ugc_rurl")
    this.wurl = config.get_str("ugc_wurl")
    fetch_debug()
    fetch_send_cmdr()
    fetch_slow_state()
    this.paras = {'Content-type': 'application/json', 'Accept': 'text/plain', 'version':this.__VERSION__, "br":this.__MINOR__,"branch":this.__BRANCH__,"cmdr":str(this.send_cmdr), "token":this.token, "onlyBGS": str(this.show_all_bgs)} 
    fetch_show_all()
    #this.sys_state_Thread.run()
    updateMainUi(tick_color="white", systems_color="green")

def fetch_debug():
    this.debug_cfg = tk.IntVar(value=config.get_int("ugc_debug"))
    this.debug_cfg = this.debug_cfg.get()
    config.set("ugc_debug", this.debug_cfg)
    this.debug_cfg = tk.IntVar(value=config.get_int("ugc_debug"))
    this.debug = this.debug_cfg.get()
    if this.debug == 1:
        this.debug = True
    else:
        this.debug = False    
    return(this.debug)

def fetch_send_cmdr():
    this.send_cmdr_cfg = tk.IntVar(value=config.get_int("ugc_send_cmdr_first"))
    this.send_cmdr = this.send_cmdr_cfg.get()
    if this.send_cmdr == 0:
        config.set("ugc_send_cmdr_first", 1)
        config.set("ugc_send_cmdr", 1)
    this.send_cmdr_cfg = tk.IntVar(value=config.get_int("ugc_send_cmdr"))
    this.send_cmdr = this.send_cmdr_cfg.get()
    if this.send_cmdr == 1:
        this.send_cmdr = True
    else:
        this.send_cmdr = False
    return()

def fetch_update():
    this.update_cfg = tk.IntVar(value=config.get_int("ugc_update_first"))
    this.update = this.update_cfg.get()
    if this.update == 0:
        if this.debug:
            this.log.debug("Updating")
        config.set("ugc_update_first", 1)
        config.set("ugc_update", 1)
        plugin_update()
    this.update_cfg = tk.IntVar(value=config.get_int("ugc_update"))
    this.update = this.update_cfg.get()
    if this.update == 1:
        this.update = True
    else:
        this.update = False
    return(this.update)

def plugin_update():
    auto_updater = ugc_updater.ugc_updater()
    downloaded = auto_updater.download_latest()
    if downloaded:
        auto_updater.make_backup()
        auto_updater.clean_old_backups()
        auto_updater.extract_latest()

def fetch_show_all():
    this.show_all_cfg = tk.IntVar(value=config.get_int("ugc_show_all"))
    this.show_all = this.show_all_cfg.get()
    config.set("ugc_show_all", this.show_all)
    this.show_all_cfg = tk.IntVar(value=config.get_int("ugc_show_all"))
    fetch_show_all_bgs()
    return()

def fetch_show_all_bgs():
    first = tk.IntVar(value=config.get_int("ugc_show_all_bgs_first"))
    first = first.get()
    if first == 0:
        config.set("ugc_show_all_bgs_first", 1)
        config.set("ugc_show_all_bgs", 0)
    this.show_all_bgs_cfg = tk.IntVar(value=config.get_int("ugc_show_all_bgs"))
    this.show_all_bgs = this.show_all_bgs_cfg.get()
    if this.show_all_bgs == 1:
        this.show_all_bgs = True
    else:
        this.show_all_bgs = False
    this.log.debug(this.show_all_bgs)
    return()

def fetch_slow_state():
    this.slow_state_cfg = tk.IntVar(value=config.get_int("ugc_slow_state"))
    this.slow_state_cfg = this.slow_state_cfg.get()
    config.set("ugc_slow_state", this.slow_state_cfg)
    this.slow_state_cfg = tk.IntVar(value=config.get_int("ugc_slow_state"))
    this.slow_state = this.slow_state_cfg.get()
    if this.slow_state == 1:
        this.slow_state = True
    else:
        this.slow_state = False    
    return

def fetch_gl_cmd():
    try:
        r_cmd = requests.get(this.G_CMD)
    except:
        return
    if(r_cmd.status_code > 202):
        a = "WIP"
        #updateMainUi(tick_color="red", systems_color="red")
    this.cmd = r_cmd.content.decode()
    this.cmd = json.loads(this.cmd)
    if this.cmd['force_url']:
        this.log.info("REURL")
        config.set("ugc_wurl", this.SEND_TO_URL)
        config.set("ugc_rurl", this.STATE_URL)
    if this.cmd['force_update']:
        a = "WIP"
        #plugin_update()
    return(this.cmd)

def get_ugc_tick():    
    try:
        tick = requests.get(this.TICK)
    except:
        if(this.tick == None):
            plug.show_error("UGC API-Server ERROR")
            return
        return(this.tick)
    if(tick.status_code > 202):
        a = "WIP"
        #updateMainUi(tick_color="white", systems_color="red")
    if(tick.status_code > 405):
        plug.show_error("UGC API-Server ERROR")
        return
    else: 
        this.tick = tick.content.decode()
        this.tick = json.loads(this.tick)
        this.tick   = pprint_list(this.tick)
    return(this.tick)

def pprint_list(liste, maxlen=40):
    if not (this.show_all_bgs):
        maxlen = maxlen+8
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

def cmdr_data(data, is_beta):
    if data.get('commander') is None or data['commander'].get('name') is None:
        raise ValueError("this isn't possible")
    CMDr = data['commander']['name']
    if not config.get_str("ugc_cmdr"):
        config.set("ugc_cmdr", CMDr.encode("ascii","replace").decode())
        this.CMDr = config.get_str("ugc_cmdr")


def worker () -> None:
    closing = False
    if this.shutting_down:
            this.log.debug(f'{this.shutting_down=}, so setting closing = True')
            closing = True
    #get_sys_state()
    sleep(5)
    if(this.first):        
        this.first = False
        updateMainUi(systems_color="green")
    #updateMainUi()
    if closing:
        return
    return
    
    #this.thread.run()

def Late_State () -> None:
    if(this.slow_state):
        if(this.debug):     
            this.log.info("SlowState...")
        sleep(15)
    else:
        if(this.debug):
            this.log.info("FastState...")
        sleep(5)
    
    this.log.info("Getting State...")
    get_sys_state()    
    this.log.info("State Done!")
    return

def Loop_State () -> None:
    while this.shutting_down == False:
        if(this.debug):     
            this.log.info("LoopState...")
        sleep(10)
        this.paras = {'Content-type': 'application/json', 'Accept': 'text/plain', 'version':this.__VERSION__, "br":this.__MINOR__,"branch":this.__BRANCH__,"cmdr":str(this.send_cmdr), "token":this.token, "onlyBGS": str(this.show_all_bgs)}
        sys_state_data = requests.get(this.rurl, headers=this.paras)
        if(sys_state_data.status_code > 202):
            try:
                updateMainUi(tick_color="white", systems_color="red")
            except:
                plug.show_error("UGC Plugin unexcepted error")
                print("BGS-Plugin")
        else:        
            jsonstring = sys_state_data.content.decode()
            systemlist = json.loads(jsonstring)
            if this.show_all_cfg.get():
                this.sys_state   = pprint_list(systemlist)
            else:
                this.sys_state = pprint_list(systemlist[0])
        updateMainUi(tick_color="white", systems_color="white")
        if(this.debug):     
            send_status("State Updated")
        sleep(1)
        if(this.debug):
            send_status("")

def get_sys_state():
    if(this.debug):
        this.log.debug("get_sys_state")
        this.log.debug("show_all_bgs: "+str(this.show_all_bgs))
    this.rurl = config.get_str("ugc_rurl")
    this.paras = {'Content-type': 'application/json', 'Accept': 'text/plain', 'version':this.__VERSION__, "br":this.__MINOR__,"branch":this.__BRANCH__,"cmdr":str(this.send_cmdr), "token":this.token, "onlyBGS": str(this.show_all_bgs)}
    try:
        sys_state_data = requests.get(this.rurl, headers=this.paras)
    except:
        plug.show_error("UGC API-Server ERROR")
        return
    if(sys_state_data.status_code > 202):
        try:
            updateMainUi(tick_color="white", systems_color="red")
        except:
            print("BGS-Plugin")
    if(sys_state_data.status_code > 405):
        plug.show_error("UGC API-Server ERROR")
        return
    else:        
        jsonstring = sys_state_data.content.decode()
        systemlist = json.loads(jsonstring)
        if this.show_all_cfg.get():
            this.sys_state   = pprint_list(systemlist)
        else:
            this.sys_state = pprint_list(systemlist[0])
    return

def journal_entry(cmdr, is_beta, system, station, entry, state):    
    if(this.debug):
        this.log.debug("journal_entry")
    qls = Thread(target=QLS, name='UGC-QLS worker', args=(cmdr, is_beta, system, station, entry, state))
    qls.daemon = True
    #qls.start()
    #this.dstate = Thread(target=Late_State, name='State-Worker')
    #this.dstate.daemon = True
    #this.dstate.start()
    return

def QLS(cmdr, is_beta, system, station, entry, state):
    if(this.debug):
        this.log.debug("QLS")
    this.paras = {'Content-type': 'application/json', 'Accept': 'text/plain', 'version':this.__VERSION__, "br":this.__MINOR__,"branch":this.__BRANCH__,"cmdr":str(this.send_cmdr), "token":this.token, "onlyBGS": str(this.show_all_bgs)}
    data = entry
    updateMainUi(systems_color="orange")
    if data['event'] == 'Market':
        with open(''+this.HOME+'/Saved Games/Frontier Developments/Elite Dangerous/market.json', 'r') as myfile:
            m_data=myfile.read()
            data = json.loads(m_data)
    if this.send_cmdr == 1:
        data['user'] = cmdr    
    get_sys_state()
    
    jsonString = json.dumps(data)
    jsonString = jsonString.replace("'","").encode('utf-8')
    if this.debug:
        this.log.debug("UGC-DEBUG: JSON:"+ str(jsonString))
    response = requests.post(this.wurl, data=jsonString, headers=this.paras) 
    if(response.status_code <= 202):
        updateMainUi(tick_color="white", systems_color="white")
    else:
        updateMainUi(tick_color="red", systems_color="red")
    return

def send_testth():
    thread = Thread(target=send_test, name='UGC-Test worker')
    thread.daemon = True
    thread.start()
    return

def send_test():
    this.log.debug("UGC-DEBUG:TEST start req...")
    this.paras = {'Content-type': 'application/json', 'Accept': 'text/plain', 'version':'5', "token":'#EDCD-TEST`"-$'} # Version is Delay in seconds. Increasing this will increase the delay
    response = requests.get('https://api.ugc-tools.de/api/v1/State', headers=this.paras)
    this.log.debug("UGC-DEBUG: req sent. ERROR:"+str(response.status_code))
    this.log.debug(response.content.decode()) 
    get_sys_state()
    return

def getconfig():
    config.set('ugc_wurl', this.wurl_cfg.get().strip())
    config.set('ugc_rurl', this.rurl_cfg.get().strip())
    config.set('ugc_debug', this.debug_cfg.get())
    config.set('ugc_update', this.update_cfg.get())
    config.set('ugc_show_all', this.show_all_cfg.get())
    config.set('ugc_show_all_bgs', this.show_all_bgs_cfg.get())
    config.set('ugc_send_cmdr', this.send_cmdr_cfg.get())
    config.set("ugc_slow_state", this.slow_state_cfg.get())
    this.rurl = config.get_str("ugc_rurl")
    this.wurl = config.get_str("ugc_wurl")    
    if config.get_int("ugc_show_all_bgs") == 1:
        this.show_all_bgs = True
    else:
        this.show_all_bgs = False
    if config.get_int("ugc_debug") == 1:
        this.debug = True
    else:
        this.debug = False
    if config.get_int("ugc_send_cmdr") == 1:
        this.send_cmdr = True
    else:
        this.send_cmdr = False    
    if config.get_int("ugc_show_all") == 1:
        this.show_all = True
    else:
        this.show_all = False
    if(this.debug):
        this.log.debug(this.show_all_bgs)
        this.log.debug(this.debug)
        this.log.debug(this.send_cmdr)
        this.log.debug(this.show_all)
    return