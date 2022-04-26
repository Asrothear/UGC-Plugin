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
from config import config
from typing import TYPE_CHECKING, Any, List, Literal, Mapping, MutableMapping, Optional, Set, Tuple, Union, cast
import ugc_updater
import ugc_crypt


class This:

    def __init__(self):

        self.SEND_TO_URL = 'https://api.ugc-tools.de/api/v1/QLS'
        self.STATE_URL = 'https://api.ugc-tools.de/api/v1/State'
        self.TICK = 'https://api.ugc-tools.de/api/v1/Tick'
        self.G_CMD = 'https://api.ugc-tools.de/api/v1/PluginControll'
        self.__VERSION__ = "3.0" # DONT TOUCH ME !!
        self.__MINOR__ = "1" # DONT TOUCH ME !!
        self.__BRANCH__ = "ThreadSafe rel.1"# DONT TOUCH ME !!
        self.CONFIG_MAIN = 'UGC-Plugin' # DONT TOUCH ME !!
        self.HOME = str(Path.home()).replace("\\", "/")
        self.send_cmdr_cfg = None
        self.send_cmdr = None
        self.show_all = None
        self.update_cfg = None
        self.update = None
        self.debug_cfg = None
        self.debug = None
        self.shutting_down = False
        self.sys_state = "Start Up"
        self.tick = "Start Up"
        self.vtk_cfg = None
        #
        self.session: requests.Session = requests.Session()
        self.queue: Queue = Queue()		# Items to be sent by worker thread
        self.lastlookup: requests.Response  # Result of last system lookup
        self.plugin_name = os.path.basename(os.path.dirname(__file__))
        self.Crypt = ugc_crypt.ugc_crypt()
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
        self.get_sys_state: Optional[threading.Thread] = None
        self.QLS: Optional[threading.Thread] = None

        self.log = logs.getLogger(f'{self.plugin_name}')

        self.hwID = None
        self.UUID = None
        self.Hash = None
        self.verify_token = ""

        self.paras = {'Content-type': 'application/json', 'Accept': 'text/plain', 'version':self.__VERSION__, "br":self.__MINOR__,"branch":self.__BRANCH__, "cmdr":str(self.send_cmdr), "uuid":self.UUID, "token":self.Hash}

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
    get_ugc_tick()
    if not config.get_str("ugc_wurl"):
        config.set("ugc_wurl", this.SEND_TO_URL)
    if not config.get_str("ugc_rurl"):
        config.set("ugc_rurl", this.STATE_URL)
    this.rurl = config.get_str("ugc_rurl")
    this.wurl = config.get_str("ugc_wurl")
    if this.debug:
        this.log.debug(str(this.rurl))
        this.log.debug(str(this.wurl))
        this.log.debug(str(this.cmd))
        this.log.debug(str(this.tick))
    if config.get_str("ugc_cmdr"):
        this.CMDr = config.get_str("ugc_cmdr").encode("ascii","replace").decode()
        crypter()
    this.thread = Thread(target=worker, name='UGC worker')
    this.thread.daemon = True
    this.thread.start()
    this.get_sys_state = Thread(target=get_sys_state, name='UGC worker')
    this.get_sys_state.daemon = True
    this.get_sys_state.start()
    this.log.debug('Done.')
    return this.CONFIG_MAIN

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
    frame = tk.Frame(parent)
    this.emptyFrame = tk.Frame(frame)
    frame.columnconfigure(1, weight=1)

    this.widget_tick_label = tk.Label(frame)
    this.widget_tick_value = tk.Label(frame)
    this.widget_systems_label = tk.Label(frame)
    this.widget_systems_value = tk.Label(frame)

    this.frame = frame
    updateMainUi(systems_color="green")
    #ugc.widget_systems_value["foreground"] = "green"
    return this.frame

def updateMainUi(tick_color="orange", systems_color="orange"):
    # Last tick
    get_ugc_tick()
    this.widget_tick_label.grid(row=0, column=0, sticky=tk.W)
    this.widget_tick_label["text"] = "Last Tick:"
    this.widget_tick_value.grid(row=0, column=1, sticky=tk.EW)
    this.widget_tick_value["text"] = this.tick
    this.widget_tick_value["foreground"] = tick_color
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
#

def plugin_prefs(parent, cmdr, is_beta):
    if not config.get_str("ugc_cmdr"):
        config.set("ugc_cmdr", cmdr.encode("ascii","replace").decode())
        this.CMDr = config.get_str("ugc_cmdr")
        crypter()
    this.paras = {'Content-type': 'application/json', 'Accept': 'text/plain', 'version':this.__VERSION__, "br":this.__MINOR__,"branch":this.__BRANCH__,"cmdr":str(this.send_cmdr), "uuid":this.UUID, "token":this.Hash}
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
    this.vtk_label = nb.Label(frame, text="Verify Token")
    this.vtk_label.grid(row=13, padx=PADX, sticky=tk.W)
    this.vtk_cfg = nb.Entry(frame)
    this.vtk_cfg.grid(row=13, column=1, padx=PADX, pady=PADY, sticky=tk.EW)
    this.vtk_cfg.insert(0,"")
    #config interface
    nb.Checkbutton(frame, text="CMDr Namen übertragen", variable=this.send_cmdr_cfg).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Checkbutton(frame, text="Alle Zeigen", variable=this.show_all).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Checkbutton(frame, text="Auto Update", variable=this.update_cfg).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Checkbutton(frame, text="Debug", variable=this.debug_cfg).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Label(frame, text="Textfarben: ").grid(columnspan=2, padx=5, pady=(2,0), sticky=tk.W)
    nb.Label(frame, text="Green: Start Up").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="Orange: Bussy").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="White: Idle").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="Red: Error").grid(columnspan=2, padx=5, pady=(0,0))
    nb.Label(frame, text="Version: "+str(this.__VERSION__)+"."+this.__MINOR__+" "+str(this.__BRANCH__)).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    nb.Label(frame, text="CMDr: "+str(cmdr)).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    
    nb.Button(frame, text="Test", command=lambda:send_test()).grid(columnspan=2, padx=BUTTONX, pady=(5,0), sticky=tk.W)
    return frame

def prefs_changed(cmdr, is_beta):
    config.set('ugc_wurl', this.wurl_cfg.get().strip())
    config.set('ugc_rurl', this.rurl_cfg.get().strip())
    config.set('ugc_debug', this.debug_cfg.get())
    config.set('ugc_update', this.update_cfg.get())
    config.set('ugc_show_all', this.show_all.get())
    config.set('ugc_send_cmdr', this.send_cmdr_cfg.get())
    this.verify_token = this.vtk_cfg.get().strip()
    fetch_debug()
    fetch_send_cmdr()
    this.paras = {'Content-type': 'application/json', 'Accept': 'text/plain', 'version':this.__VERSION__, "br":this.__MINOR__,"branch":this.__BRANCH__,"cmdr":str(this.send_cmdr), "uuid":this.UUID, "token":this.Hash} 
    fetch_show_all()
    #this.sys_state_Thread.run()
    updateMainUi()

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
    return(this.send_cmdr)

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
    this.show_all = tk.IntVar(value=config.get_int("ugc_show_all"))
    this.show_all = this.show_all.get()
    config.set("ugc_show_all", this.show_all)
    this.show_all = tk.IntVar(value=config.get_int("ugc_show_all"))
    return(this.show_all)

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
            this.tick = "API-Server ERROR"
        return(this.tick)
    if(tick.status_code > 202):
        a = "WIP"
        #updateMainUi(tick_color="white", systems_color="red")
    if(tick.status_code > 405):
        this.tick = "API-Server ERROR"
    else: 
        this.tick = tick.content.decode()
        this.tick = json.loads(this.tick)
        this.tick   = pprint_list(this.tick)
    return(this.tick)

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

def cmdr_data(data, is_beta):
    if data.get('commander') is None or data['commander'].get('name') is None:
        raise ValueError("this isn't possible")
    CMDr = data['commander']['name']
    if not config.get_str("ugc_cmdr"):
        config.set("ugc_cmdr", CMDr.encode("ascii","replace").decode())
        this.CMDr = config.get_str("ugc_cmdr")
        crypter()

def crypter():
    if not this.hwID:
            this.hwID = this.Crypt.ghwid()
    if not this.UUID:
            this.UUID = str(this.Crypt.muuid(this.CMDr,this.hwID)).replace("'","|")
    if not config.get_str("ugc_token"):
        config.set("ugc_token", this.Crypt.sign(this.CMDr,this.hwID))
        this.Hash = config.get_str("ugc_token")
    else:
        this.Hash = config.get_str("ugc_token")
    if this.debug:
        this.log.info(this.CMDr)
        this.log.info(this.UUID)
        this.log.info(this.Hash)
    if not this.Crypt.verify(this.CMDr, this.Hash):
        this.Hash = this.Crypt.sign(this.CMDr,this.hwID)

def worker () -> None:
    closing = False
    if this.shutting_down:
            this.log.debug(f'{this.shutting_down=}, so setting closing = True')
            closing = True
    sleep(20)
    get_sys_state()
    #updateMainUi()
    if closing:
        return
    
    #this.thread.run()

def get_sys_state():
    if(this.debug):
        this.log.debug("get_sys_state")
    this.rurl = config.get_str("ugc_rurl")
    try:
        sys_state = requests.get(this.rurl, headers=this.paras)
    except:
        if(this.sys_state ==""):
            this.sys_state = "API-Server ERROR"
    if(sys_state.status_code > 202):
        try:
            updateMainUi(tick_color="white", systems_color="red")
        except:
            print("BGS-Plugin")
    if(sys_state.status_code > 405):
        this.sys_state = "API-Server ERROR"
    else:        
        jsonstring = sys_state.content.decode()
        systemlist = json.loads(jsonstring)
        if this.show_all.get():
            this.sys_state   = pprint_list(systemlist)
        else:
            this.sys_state = pprint_list(systemlist[0])
    return

def journal_entry(cmdr, is_beta, system, station, entry, state):    
    if(this.debug):
        this.log.debug("journal_entry")
    qls = Thread(target=QLS, name='UGC-QLS worker', args=(cmdr, is_beta, system, station, entry, state))
    qls.daemon = True
    qls.start()
    return

def QLS(cmdr, is_beta, system, station, entry, state):
    if(this.debug):
        this.log.debug("QLS")
    this.paras = {'Content-type': 'application/json', 'Accept': 'text/plain', 'version':this.__VERSION__, "br":this.__MINOR__,"branch":this.__BRANCH__,"cmdr":str(this.send_cmdr), "uuid":this.UUID, "token":this.Hash}
    data = entry
    updateMainUi(systems_color="orange")
    if data['event'] == 'Market':
        with open(''+this.HOME+'/Saved Games/Frontier Developments/Elite Dangerous/market.json', 'r') as myfile:
            m_data=myfile.read()
            data = json.loads(m_data)
            if this.debug:
                this.log.debug(data)
    if this.send_cmdr == 1:
        data['user'] = cmdr

    data["ugc_token_v2"] = dict()
    data["ugc_token_v2"]["uuid"] = this.UUID
    data["ugc_token_v2"]["token"] = this.Hash
    data["ugc_token_v2"]["verify"] = this.verify_token
    data["ugc_additional"] = dict()
    data["ugc_additional"]["system"] = system
    data["ugc_additional"]["station"] = station
    data['ugc_p_version'] = this.__VERSION__
    data['ugc_p_minor'] = this.__MINOR__
    data['ugc_p_branch'] = this.__BRANCH__
    
    headers = { 'Content-type': 'application/json', 'Accept': 'text/plain' }
    jsonString = json.dumps(data)
    jsonString = jsonString.replace("'","").encode('utf-8')
    if this.debug:
        this.log.debug("UGC-DEBUG: PATH: ")
        this.log.debug("UGC-DEBUG: start req...")
        this.log.debug("UGC-DEBUG: JSON:"+ str(jsonString))
    response = requests.post(this.wurl, data=jsonString, headers=headers)
    get_sys_state()
    if this.debug:
        this.log.debug("UGC-DEBUG: req sent. ERROR:"+str(response.status_code))
        this.log.debug("UGC-DEBUG: "+this.sys_state)    
    if(response.status_code <= 202):
        updateMainUi(tick_color="white", systems_color="white")
    else:
        updateMainUi(tick_color="red", systems_color="red")
    return

def send_test():
    thread = Thread(target=send_testth, name='UGC-Test worker')
    thread.daemon = True
    thread.start()
    return

def send_testth():
    this.log.debug("UGC-DEBUG:TEST start req...")
    this.paras = {'Content-type': 'application/json', 'Accept': 'text/plain', 'version':this.__VERSION__, "br":this.__MINOR__,"branch":this.__BRANCH__,"cmdr":str(this.send_cmdr), "uuid":this.UUID, "token":this.Hash}
    if this.verify_token =="":
        if this.vtk_cfg.get().strip() !="":
            this.verify_token = this.vtk_cfg.get().strip()
    data = dict()
    config.set('ugc_wurl', this.wurl_cfg.get().strip())
    config.set('ugc_rurl', this.rurl_cfg.get().strip())
    this.wurl = config.get_str("ugc_wurl")
    this.rurl = config.get_str("ugc_rurl")
    if this.send_cmdr == 1:
        data['user'] = this.CMDr
    updateMainUi(systems_color="orange")
    data["event"] = "test"
    data["ugc_token_v2"] = dict()
    data["ugc_token_v2"]["uuid"] = this.UUID
    data["ugc_token_v2"]["token"] = this.Hash
    data["ugc_token_v2"]["verify"] = this.verify_token
    
    data['ugc_p_version'] = this.__VERSION__
    data['ugc_p_minor'] = this.__MINOR__
    data['ugc_p_branch'] = this.__BRANCH__
    data['payload'] = "bärenkatapult"
    
    headers = { 'Content-type': 'application/json', 'Accept': 'text/plain' }
    jsonString = json.dumps(data).encode('utf-8')   
    this.log.debug("UGC-DEBUG:TEST JSON: "+ str(jsonString))
    response = requests.post(this.wurl, data=jsonString, headers=headers)
    get_sys_state()
    if this.debug:
        this.log.debug("UGC-DEBUG: req sent. ERROR:"+str(response.status_code))
        this.log.debug("UGC-DEBUG: "+this.sys_state)
    if(response.status_code <= 202):
        updateMainUi(tick_color="white", systems_color="white")
    else:
        updateMainUi(tick_color="red", systems_color="red")
    return