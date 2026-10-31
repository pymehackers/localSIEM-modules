#!/bin/bash

# localSIEM privesc: command hook of the interactive bash shells.
#
# Installed by the privesc module of localSIEM (manage.py setup-modules
# --configure-privesc) as /etc/localsiem-privesc/hook.bash, and loaded from
# /etc/profile.d/localsiem-privesc.sh and from the bashrc of the system.
#
# This file is sourced by every interactive bash, it is not run as a script:
# it must never change the options of the shell (no set -e, set -u or
# pipefail), never take the EXIT trap, never print anything and never fork for
# each command. That is why it does not follow the template of the scripts.
#
# Every command, builtins included (pwd, cd, unset HISTFILE, trap), is
# appended to /var/log/localsiem-privesc/<uid>.log: a file of the user, of the
# group localsiem and with mode 640, in a folder where every user can create a
# file but none can list or delete the files of the others. localSIEM reads it.
# A user can switch the hook off in their own shell (bash --norc, trap - DEBUG):
# it complements auditd and snoopy, it does not replace them.
#
# One line per entry, tab separated, with tabs, newlines and backslashes of
# the folder and of the command escaped (\t, \n, \r, \\):
#
#   v1 kind time pid ppid uid euid line tty ssh_client sudo_user parent
#   parent_uid cwd command
#
# kind is start (the shell starts: parent is the program that started it) or
# command (a command is about to run). time is UTC, in the native format of
# the project (2026-10-29@13-59-59.723). line is HISTCMD: the commands of one
# typed line (a pipeline) share it. At most 30 entries per second are written,
# so a loop cannot fill the disk.

[ -n "${BASH_VERSION-}" ] || return 0
case "$-" in
  *i*) ;;
  *) return 0 ;;
esac
# Loaded once per shell (from profile.d and from the bashrc). The variable is
# not exported: every new shell loads the hook again.
[ -z "${vLocalsiemPrivescFile-}" ] || return 0
[ -d /var/log/localsiem-privesc ] || return 0

vLocalsiemPrivescFile="/var/log/localsiem-privesc/${UID}.log"
if [ ! -e "${vLocalsiemPrivescFile}" ]; then
  ( umask 0137; : >> "${vLocalsiemPrivescFile}" ) 2>/dev/null
fi
# Never write into a file of another user: someone may have created it to read
# the commands of this user or to block them. localSIEM warns about it.
if [ ! -O "${vLocalsiemPrivescFile}" ] || [ ! -w "${vLocalsiemPrivescFile}" ]; then
  unset vLocalsiemPrivescFile
  return 0
fi

vLocalsiemPrivescEscaped=""
vLocalsiemPrivescSecond=""
vLocalsiemPrivescCount=0

fLocalsiemPrivescEscape() {
  vLocalsiemPrivescEscaped="${1//\\/\\\\}"
  vLocalsiemPrivescEscaped="${vLocalsiemPrivescEscaped//$'\t'/\\t}"
  vLocalsiemPrivescEscaped="${vLocalsiemPrivescEscaped//$'\n'/\\n}"
  vLocalsiemPrivescEscaped="${vLocalsiemPrivescEscaped//$'\r'/\\r}"
  return 0
}

# What does not change while the shell lives, read once without forking (the
# terminal needs tty when sshd did not set SSH_TTY).
vLocalsiemPrivescTty="${SSH_TTY-}"
if [ -z "${vLocalsiemPrivescTty}" ]; then
  vLocalsiemPrivescTty="$(tty 2>/dev/null)"
  case "${vLocalsiemPrivescTty}" in
    /dev/*) ;;
    *) vLocalsiemPrivescTty="" ;;
  esac
fi
vLocalsiemPrivescSsh="${SSH_CLIENT-}"
vLocalsiemPrivescSsh="${vLocalsiemPrivescSsh%% *}"
vLocalsiemPrivescParent=""
vLocalsiemPrivescParentUid=""
if [ -r "/proc/${PPID}/comm" ]; then
  read -r vLocalsiemPrivescParent < "/proc/${PPID}/comm" 2>/dev/null
fi
if [ -r "/proc/${PPID}/status" ]; then
  while read -r vLocalsiemPrivescKey vLocalsiemPrivescValue vLocalsiemPrivescRest; do
    if [ "${vLocalsiemPrivescKey}" = "Uid:" ]; then
      vLocalsiemPrivescParentUid="${vLocalsiemPrivescValue}"
      break
    fi
  done < "/proc/${PPID}/status"
  unset vLocalsiemPrivescKey vLocalsiemPrivescValue vLocalsiemPrivescRest
fi
fLocalsiemPrivescEscape "${vLocalsiemPrivescParent}"
vLocalsiemPrivescParent="${vLocalsiemPrivescEscaped}"
fLocalsiemPrivescEscape "${vLocalsiemPrivescTty}"
vLocalsiemPrivescTty="${vLocalsiemPrivescEscaped}"
fLocalsiemPrivescEscape "${vLocalsiemPrivescSsh}"
vLocalsiemPrivescSsh="${vLocalsiemPrivescEscaped}"

fLocalsiemPrivescWrite() {
  # The time in UTC and in the native format of the project
  # (2026-10-29@13-59-59.723), from EPOCHREALTIME (bash 5; its decimal
  # separator follows the locale) without forking.
  local vEpoch="${EPOCHREALTIME-}"
  local vSeconds=""
  local vMillis="000"
  local vTime=""
  local vCwd=""
  local vSudoUser=""
  if [ -n "${vEpoch}" ]; then
    vSeconds="${vEpoch%%[.,]*}"
    vMillis="${vEpoch#*[.,]}000"
    vMillis="${vMillis:0:3}"
  else
    printf -v vSeconds '%(%s)T' -1
  fi
  TZ=UTC0 printf -v vTime '%(%Y-%m-%d@%H-%M-%S)T' "${vSeconds}"
  vTime="${vTime}.${vMillis}"
  fLocalsiemPrivescEscape "${SUDO_USER-}"
  vSudoUser="${vLocalsiemPrivescEscaped}"
  fLocalsiemPrivescEscape "${PWD-}"
  vCwd="${vLocalsiemPrivescEscaped}"
  fLocalsiemPrivescEscape "${2:0:4096}"
  printf 'v1\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "${1}" "${vTime}" "$$" "${PPID}" "${UID}" "${EUID}" "${HISTCMD-}" \
    "${vLocalsiemPrivescTty}" "${vLocalsiemPrivescSsh}" "${vSudoUser}" \
    "${vLocalsiemPrivescParent}" "${vLocalsiemPrivescParentUid}" "${vCwd}" \
    "${vLocalsiemPrivescEscaped}" >> "${vLocalsiemPrivescFile}" 2>/dev/null
  return 0
}

fLocalsiemPrivescLog() {
  # Not the commands of the tab completion, nor more than 30 per second.
  [ -z "${COMP_LINE-}" ] || return 0
  [ -n "${vLocalsiemPrivescFile-}" ] || return 0
  # A file deleted by its user is not created again with the umask of the
  # shell (others could read it): localSIEM reports the deletion.
  [ -f "${vLocalsiemPrivescFile}" ] || return 0
  if [ "${SECONDS}" != "${vLocalsiemPrivescSecond}" ]; then
    vLocalsiemPrivescSecond="${SECONDS}"
    vLocalsiemPrivescCount=0
  fi
  vLocalsiemPrivescCount=$((vLocalsiemPrivescCount + 1))
  [ "${vLocalsiemPrivescCount}" -le 30 ] || return 0
  fLocalsiemPrivescWrite "command" "${BASH_COMMAND}"
  return 0
}

fLocalsiemPrivescWrite "start" ""
trap 'fLocalsiemPrivescLog' DEBUG
