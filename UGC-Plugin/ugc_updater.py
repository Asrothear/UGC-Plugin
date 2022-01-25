from __future__ import absolute_import

import requests
import zipfile
import errno
import os
import json
import datetime
import utils2to3


class ugc_updater(object):
    REPO = "Asrothear/UGC-Plugin"
    UPDATES = utils2to3.abspathmaker(__file__, 'updates')
    LATEST = utils2to3.abspathmaker(__file__, 'updates', 'latest.zip')
    BACKUP = utils2to3.abspathmaker(__file__, 'backup')
    ugc_PATH = os.path.abspath(os.path.dirname(__file__))

    def __init__(self):
        self.updates = ugc_updater.UPDATES
        self.output = ugc_updater.LATEST


    def download_latest(self):
        if not os.path.exists(self.updates):
            try:
                os.makedirs(self.updates)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    return False

        download_url = self.__latest_release_url()
        if not download_url:
            return False
        response = requests.get(download_url, stream=True)
        response.raise_for_status()

        if response.status_code != requests.codes.ok:
            return False

        with open(self.output, 'wb') as handle:
            for block in response.iter_content(32768):
                handle.write(block)
        return True

    def clean_old_backups(self):
        files = os.listdir(ugc_updater.BACKUP)
        files = [os.path.join(ugc_updater.BACKUP, f) for f in files]
        files.sort(key=lambda x: os.path.getctime(x))
        nbfiles = len(files)
        max_backups = 2
        for i in range(0, nbfiles - max_backups):
            f = files[i]
            os.unlink(f)

    def make_backup(self):
        if not os.path.exists(ugc_updater.BACKUP):
            try:
                os.makedirs(ugc_updater.BACKUP)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    return False
        name = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S') + '.zip'
        backup_file = os.path.join(ugc_updater.BACKUP, name)
        zipf = zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED)
        self.__zipdir(ugc_updater.ugc_PATH, zipf)
        zipf.close()

    def __zipdir(self, path, ziph):
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if (("updates" not in d) and ("backup" not in d))]
            for file in files:
                if file.endswith(".pyc") or file.endswith(".pyo"):
                    continue
                fp = os.path.join(root, file)
                ziph.write(fp, os.path.relpath(fp, ugc_updater.ugc_PATH))

    def extract_latest(self):
        with zipfile.ZipFile(self.output, "r") as latest:
            latest.extractall(ugc_updater.ugc_PATH)

    def __latest_release_url(self):
        latest_release_api = "https://api.github.com/repos/{}/releases/latest".format(self.REPO)
        response = requests.get(latest_release_api)
        if response.status_code != requests.codes.ok:
            return None
        json_resp = json.loads(response.content)
        assets = json_resp.get("assets", None)
        if not assets:
            return None
        return assets[0].get("browser_download_url", None)
