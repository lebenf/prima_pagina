# Copyright (C) 2026 Lorenzo Benfeati
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.plugins.base import NotificationEvent, NotificationPayload, NotificationPlugin
from app.plugins.manager import plugin_manager

__all__ = [
    "NotificationEvent", "NotificationPayload", "NotificationPlugin", "plugin_manager"
]
