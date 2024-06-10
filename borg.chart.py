# -*- coding: utf-8 -*-
# Description: borg netdata python.d modulue
# Author: Felix Homa
# SPDX-License-Identifier: GPL-3.0-or-later

from subprocess import Popen, PIPE

import json
import datetime

from bases.FrameworkServices.ExecutableService import ExecutableService

BORG_COMMAND = 'borg --bypass-lock info --json '

ORDER = [
    'borg_size',
    'borg_actualsize',
    'borg_ratio',
    'borg_chunks',
    'borg_time',
]

CHARTS = {
    'borg_size': {
        'options': [None, 'Size of Borg Repository', 'bytes', None, 'borg.borg_size', 'area'],
        'lines': [
            ['total_csize', "Total compressed size", 'absolute'],
            ['total_size', "Total size", 'absolute'],
            ['unique_csize', "Unique compressed size", 'absolute'],
            ['unique_size', "Unique size", 'absolute'],
        ]
    },
    'borg_actualsize': {
        'options': [None, 'Size of Borg Repository on disk', 'bytes', None, 'borg.borg_actualsize', 'stacked'],
        'lines': [
            ['unique_csizeA', "Unique compressed size", 'absolute']
        ]
    },
    'borg_ratio': {
        'options': [None, 'Space Ratio', '%', None, 'borg.borg_ratio', 'line'],
        'lines': [
            ['ratio_ts_ucs', "Ratio Total Size - Unique Compressed Size", 'absolute', 1, 1000000],
            ['ratio_tcs_ucs', "Ratio Total Compressed Size - Unique Compressed Size", 'absolute', 1, 1000000],
            ['ratio_ts_us', "Ratio Total Size - Unique Size", 'absolute', 1, 1000000],
            ['ratio_us_ucs', "Ratio Unique Size - Unique Compressed Size", 'absolute', 1, 1000000],
        ]
    },
    'borg_chunks': {
        'options': [None, 'Chunks in Borg Repository', 'chunks', None, 'borg.borg_chunks', 'area'],
        'lines': [
            ['total_chunks', "Total Chunks", 'absolute'],
            ['total_unique_chunks', "Total Unique Chunks", 'absolute'],
        ]
    },
    'borg_time': {
        'options': [None, 'Last Modified', 'seconds', None, 'borg.borg_time', 'area'],
        'lines': [
            ['last_modified_ago', "Time since Last Modified",'absolute'],
        ]
    }
}


class Service(ExecutableService):
    def __init__(self, configuration=None, name=None):
        ExecutableService.__init__(self, configuration=configuration, name=name)
        self.order = ORDER
        self.definitions = CHARTS
        repo = self.configuration.get('repository', None)
        self.command = BORG_COMMAND + repo
        self.environment=dict();
        self.environment["BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK"]="yes";
        self.environment["BORG_RELOCATED_REPO_ACCESS_IS_OK"]="yes";
    # Overriding _get_raw_data, because we need to specificy environment
    def _get_raw_data(self, stderr=False, command=None):
        """
        Get raw data from executed command
        :return: <list>
        """
        command = command or self.command
        self.debug("Executing command '{0}'".format(' '.join(command)))
        try:
            p = Popen(command, stdout=PIPE, stderr=PIPE, env=self.environment)
        except Exception as error:
            self.error('Executing command {0} resulted in error: {1}'.format(command, error))
            return None

        data = list()
        std = p.stderr if stderr else p.stdout
        for line in std:
            try:
                data.append(line.decode('utf-8'))
            except (TypeError, UnicodeDecodeError):
                continue

        return data

    def _get_data(self):
        """
        Format data received from shell command
        :return: dict
        """
        try:
            raw = self._get_raw_data()
            # print(''.join(raw), sep='\n')
            js = json.loads(''.join(raw))
            data = dict()
            data["total_csize"] = js["cache"]["stats"]["total_csize"]
            data["total_size"] = js["cache"]["stats"]["total_size"]
            data["total_chunks"] = js["cache"]["stats"]["total_chunks"]
            data["unique_csize"] = js["cache"]["stats"]["unique_csize"]
            data["unique_csizeA"] = js["cache"]["stats"]["unique_csize"]
            data["unique_size"] = js["cache"]["stats"]["unique_size"]
            data["total_unique_chunks"] = js["cache"]["stats"]["total_unique_chunks"]
            data["ratio_ts_ucs"] = 1000000 * js["cache"]["stats"]["unique_csize"] / js["cache"]["stats"]["total_size"]
            data["ratio_tcs_ucs"] = 1000000 * js["cache"]["stats"]["unique_csize"] / js["cache"]["stats"]["total_csize"]
            data["ratio_ts_us"] = 1000000 * js["cache"]["stats"]["unique_size"] / js["cache"]["stats"]["total_size"]
            data["ratio_us_ucs"] = 1000000 * js["cache"]["stats"]["unique_csize"] / js["cache"]["stats"]["unique_size"]
            #print(data)
#            data["last_modified_ago"] = (datetime.fromisoformat(js["repository"]["last_modified"]) - datetime.utcnow()).total_seconds()
            data["last_modified_ago"] = (datetime.datetime.utcnow() - datetime.datetime.strptime(js["repository"]["last_modified"], "%Y-%m-%dT%H:%M:%S.%f")).total_seconds()
            #print("after")
            #print(data)
            return data
        except (ValueError, AttributeError):
            return None
