#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    settings = "config.test_settings" if sys.argv[1:2] == ["test"] else "config.settings"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings)
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
