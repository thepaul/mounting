# mounting
#
# mounting filesystems through direct system-call access, instead of through
# the 'mount' binary.
#
# Useful, it seems, only because mount() is usable with an euid of 0, while
# mount requires a full uid of 0.
#
# Copyright (c) 2006 paul cannon <paul@nafpik.com>
# Released under the MIT license. See COPYRIGHT for details.

from ctypes import *
from ctypes.util import find_library
import os
import re

class error(Exception):
    pass

libc = cdll.LoadLibrary(find_library('c'))
mountcall = libc.mount
mountcall.argtypes = [c_char_p, c_char_p, c_char_p, c_ulong, c_char_p]
mountcall.restype = c_int
umountcall = libc.umount
umountcall.argtypes = [c_char_p]
umountcall.restype = c_int
umount2call = libc.umount2
umount2call.argtypes = [c_char_p, c_int]
umount2call.restype = c_int

# See sys/mount.h, linux/fs.h
MS_RDONLY = 1
MS_NOSUID = 2
MS_NODEV = 4
MS_NOEXEC = 8
MS_SYNCHRONOUS = 16
MS_REMOUNT = 32
MS_MANDLOCK = 64
MS_DIRSYNC = 128
MS_NOATIME = 1024
MS_NODIRATIME = 2048
MS_BIND = 4096
MS_MOVE = 8192

str_flags_to_bin = {
    'async': 0,
    'atime': 0,
    'auto': 0,
    'defaults': 0,
    'dev': 0,
    'exec': 0,
    'group': 0,
    'mand': MS_MANDLOCK,
    '_netdev': 0,
    'noatime': MS_NOATIME,
    'noauto': 0,
    'nodev': MS_NODEV,
    'noexec': MS_NOEXEC,
    'nomand': 0,
    'nosuid': MS_NOSUID,
    'nouser': 0,
    'owner': 0,
    'remount': MS_REMOUNT,
    'ro': MS_RDONLY,
    'rw': 0,
    'suid': 0,
    'sync': MS_SYNCHRONOUS,
    'dirsync': MS_DIRSYNC,
    'user': 0,
    'users': 0,
    'bind': MS_BIND
}

def mount(srcdir, target, fstype='none', flags=0):
    strflags = []
    binflags = 0
    if isinstance(flags, str):
        for flag in flags.split(','):
            flag = flag.strip()
            try:
                binflags |= str_flags_to_bin[flag]
            except KeyError:
                strflags.append(flag)
    else:
        binflags = flags
    res = mountcall(srcdir, target, fstype, binflags, ','.join(strflags))
    if res != 0:
        # Can't get errno until ctypes makes it available some special way,
        # or else doesn't clear it after the call!
        raise error("mount failed")

MNT_FORCE = 1
MNT_DETACH = 2
MNT_EXPIRE = 4

def umount(target, flags=0):
    if flags:
        res = umount2call(target, flags)
    else:
        res = umountcall(target)
    if res != 0:
        # Can't get errno- see above!
        raise error("umount failed")

# safe since \ never appears in /proc/mounts except in an octal escape.
# \ itself appears as \134 == chr 92.
octal_escape_re = re.compile(r'\\[0-9][0-9][0-9]')
def eval_octal_escapes(s):
    return octal_escape_re.sub(lambda n: chr(int(n.group(0)[1:], 8)), s)

def current_mounts():
    """
    Returns a list of info tuples about current mounts. Each looks like

       (dev, mountpoint, fstype, flags, dump, passno)

    """
    points = []
    f = open('/proc/mounts', 'r')
    try:
        for line in f:
            info = map(eval_octal_escapes, line.split())
            # As hinted before, this is accurate since whitespace and other
            # special chars only show up in /proc/mounts as octal escapes.
            assert len(info) == 6
            points.append(info)
        return points
    finally:
        f.close()

def ismount(d):
    """
    Returns true if the given directory is a mount point. More reliable than
    os.path.ismount, since that one can't detect bind mounts.
    """
    d = os.path.abspath(d)
    for dev, mntpnt, fstype, flags, dump, passno in current_mounts():
        if os.path.abspath(mntpnt) == d:
            return True
    return False
