#!/bin/sh

# localSIEM privesc: loads the command hook in the interactive bash shells.
# Installed as /etc/profile.d/localsiem-privesc.sh by manage.py setup-modules
# --configure-privesc. Every login shell reads this file (sh, dash and ash
# too), so it only uses POSIX syntax and does nothing outside bash.

if [ -n "${BASH_VERSION-}" ] && [ -r /etc/localsiem-privesc/hook.bash ]; then
  . /etc/localsiem-privesc/hook.bash
fi
