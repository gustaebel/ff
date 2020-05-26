# -----------------------------------------------------------------------
#
# ff - a tool for finding files in the filesystem
# Copyright (C) 2020 Lars Gustäbel <lars@gustaebel.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# -----------------------------------------------------------------------

import os
from ctypes import *

from libff.plugin import *

libc = CDLL("libc.so.6", use_errno=True)

fs_types = {
    # Lifted from src/stat.c from coreutils.
    0x61636673: ("acfs", True), 0xADF5: ("adfs", False), 0xADFF: ("affs", False),
    0x5346414F: ("afs", True), 0x09041934: ("anon-inode FS", False), 0x61756673: ("aufs", True),
    0x0187: ("autofs", False), 0x42465331: ("befs", False), 0x62646576: ("bdevfs", False),
    0x1BADFACE: ("bfs", False), 0xCAFE4A11: ("bpf_fs", False), 0x42494E4D: ("binfmt_misc", False),
    0x9123683E: ("btrfs", False), 0x73727279: ("btrfs_test", False), 0x00C36400: ("ceph", True),
    0x0027E0EB: ("cgroupfs", False), 0xFF534D42: ("cifs", True), 0x73757245: ("coda", True),
    0x012FF7B7: ("coh", False), 0x62656570: ("configfs", False), 0x28CD3D45: ("cramfs", False),
    0x453DCD28: ("cramfs-wend", False), 0x64626720: ("debugfs", False), 0x1373: ("devfs", False),
    0x1CD1: ("devpts", False), 0xF15F: ("ecryptfs", False), 0xDE5E81E4: ("efivarfs", False),
    0x00414A53: ("efs", False), 0x5DF5: ("exofs", False), 0x137D: ("ext", False),
    0xEF53: ("ext2/ext3", False), 0xEF51: ("ext2", False), 0xF2F52010: ("f2fs", False),
    0x4006: ("fat", False), 0x19830326: ("fhgfs", True), 0x65735546: ("fuseblk", True),
    0x65735543: ("fusectl", True), 0x0BAD1DEA: ("futexfs", False), 0x01161970: ("gfs/gfs2", True),
    0x47504653: ("gpfs", True), 0x4244: ("hfs", False), 0x482B: ("hfs+", False),
    0x4858: ("hfsx", False), 0x00C0FFEE: ("hostfs", False), 0xF995E849: ("hpfs", False),
    0x958458F6: ("hugetlbfs", False), 0x11307854: ("inodefs", False), 0x013111A8: ("ibrix", True),
    0x2BAD1DEA: ("inotifyfs", False), 0x9660: ("isofs", False), 0x4004: ("isofs", False),
    0x4000: ("isofs", False), 0x07C0: ("jffs", False), 0x72B6: ("jffs2", False),
    0x3153464A: ("jfs", False), 0x6B414653: ("k-afs", True), 0xC97E8168: ("logfs", False),
    0x0BD00BD0: ("lustre", True), 0x137F: ("minix", False), 0x138F: ("minix (30 char.)", False),
    0x2468: ("minix v2", False), 0x2478: ("minix v2 (30 char.)", False), 0x4D5A: ("minix3", False),
    0x19800202: ("mqueue", False), 0x4D44: ("msdos", False), 0x564C: ("novell", True),
    0x6969: ("nfs", True), 0x6E667364: ("nfsd", True), 0x3434: ("nilfs", False),
    0x6E736673: ("nsfs", False), 0x5346544E: ("ntfs", False), 0x9FA1: ("openprom", False),
    0x7461636F: ("ocfs2", True), 0x794C7630: ("overlayfs", True), 0xAAD7AAEA: ("panfs", True),
    0x50495045: ("pipefs", True), 0x9FA0: ("proc", False), 0x6165676C: ("pstorefs", False),
    0x002F: ("qnx4", False), 0x68191122: ("qnx6", False), 0x858458F6: ("ramfs", False),
    0x52654973: ("reiserfs", False), 0x7275: ("romfs", False), 0x67596969: ("rpc_pipefs", False),
    0x73636673: ("securityfs", False), 0xF97CFF8C: ("selinux", False),
    0x43415D53: ("smackfs", False), 0x517B: ("smb", True), 0xBEEFDEAD: ("snfs", True),
    0x534F434B: ("sockfs", False), 0x73717368: ("squashfs", False), 0x62656572: ("sysfs", False),
    0x012FF7B6: ("sysv2", False), 0x012FF7B5: ("sysv4", False), 0x01021994: ("tmpfs", False),
    0x74726163: ("tracefs", False), 0x24051905: ("ubifs", False), 0x15013346: ("udf", False),
    0x00011954: ("ufs", False), 0x54190100: ("ufs", False), 0x9FA2: ("usbdevfs", False),
    0x01021997: ("v9fs", False), 0xBACBACBC: ("vmhgfs", True), 0xA501FCF5: ("vxfs", True),
    0x565A4653: ("vzfs", False), 0xABBA1974: ("xenfs", False), 0x012FF7B4: ("xenix", False),
    0x58465342: ("xfs", False), 0x012FD16D: ("xia", False), 0x2FC12FC1: ("zfs", False)
}


class Fs(Plugin):
    """Provide information on the filesystem that a file is located in.
    """

    use_cache = False

    attributes = [
        ("fstype", String, "The name of the file system."),
        ("remote", Boolean, "Whether the file system is a remote file system.")
    ]

    def get_fs_type(self, path):
        """Return the name of the filesystem for path and whether it is
           a remote filesystem or not.
        """
        # Create a buffer with approximately the size of the statfs structure,
        # we only care about the first field anyway.
        statfs_struct = (c_uint * 64)()

        path_buf = create_string_buffer(os.fsencode(path))

        ret = libc.statfs64(path_buf, byref(statfs_struct))
        if ret == -1:
            errno = get_errno()
            raise OSError(errno, os.strerror(errno), path)

        f_type = statfs_struct[0]
        return fs_types.get(f_type, ("unknown", False))

    def can_handle(self, entry):
        return True

    def process(self, entry, cached):
        if entry.is_dir():
            path = os.path.abspath(entry.path)
        else:
            path = os.path.abspath(entry.dir)

        name, remote = self.get_fs_type(path)

        yield "fstype", name
        yield "remote", remote
