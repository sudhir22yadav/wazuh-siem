#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright (C) 2015-2019, Wazuh Inc.
# Created by Wazuh, Inc. <info@wazuh.com>.
# This program is a free software; you can redistribute
# it and/or modify it under the terms of GPLv2

"""Framework module for getting information from Wazuh MITRE database."""

from wazuh import common
from wazuh.utils import WazuhDBBackend, WazuhDBQuery

mitre_fields = {'id': 'id',
                'json': 'json',
                'phase_name': 'phase_name',
                'platform_name': 'platform_name'}

select_fields = "id, json, group_concat(DISTINCT platform_name) " \
                "as platforms, group_concat(DISTINCT phase_name) as phases"

from_fields = "attack LEFT JOIN has_phase ON attack.id = has_phase.attack_id" \
              " LEFT JOIN has_platform ON attack.id = has_platform.attack_id"

group_by_fields = "GROUP BY id"

count_fields = "COUNT(DISTINCT id)"

default_query = f"SELECT {select_fields} FROM {from_fields} {group_by_fields}"

count_query = f"SELECT {count_fields} FROM {from_fields}"


class WazuhDBQueryMitre(WazuhDBQuery):
    """Create a WazuhDB query for getting data from Mitre database."""

    def __init__(self, offset, limit, sort, search, select, query,
                 count, get_data, table='attack',
                 default_query=default_query,
                 default_sort_field='id', filters={},
                 fields=mitre_fields,
                 count_field='id'):
        """Create an instance of WazuhDBQueryMitre query."""
        self.default_query = default_query
        self.count_field = count_field

        WazuhDBQuery.__init__(self, offset=offset, limit=limit,
                              table=table, sort=sort, search=search,
                              select=select, fields=fields,
                              default_sort_field=default_sort_field,
                              default_sort_order='ASC', filters=filters,
                              query=query, count=count, get_data=get_data,
                              backend=WazuhDBBackend(mitre=True))

    def _default_query(self):
        return self.default_query

    def _get_total_items(self):
        final_query = self.query.replace(group_by_fields, '')
        final_query = final_query.replace(select_fields, count_fields)
        self.total_items = self.backend.execute(final_query, self.request)

    def _execute_data_query(self):
        if 'GROUP BY' in self.query:
            final_query = self.query.replace(group_by_fields, '')
            pos_order_by = final_query.find('ORDER BY')
            final_query = final_query[0:pos_order_by] + f' {group_by_fields} '\
                + final_query[pos_order_by:]
        self._data = self.backend.execute(final_query, self.request)


def get_attack(attack=None, phase=None, platform=None, offset=0,
               limit=common.database_limit, sort=None,
               search=None, q='', filters={}):
    """Get information from Mitre database."""
    query = q
    if attack:
        query = f'{query};id={attack}' if query else f'id={attack}'
    if phase:
        query = f'{query};phase_name={phase}' if query else \
            f'phase_name={phase}'
    if platform:
        query = f'{query};platform_name={platform}' if query else \
                f'platform_name={platform}'

    db_query = WazuhDBQueryMitre(offset=offset, limit=limit if limit < 10
                                 else 10, sort=sort, search=search,
                                 select=None, query=query, count=True,
                                 get_data=True, filters=filters)

    return db_query.run()
