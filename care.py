#!/usr/bin/python3

__author__ = 'Kaiwen Wu'
__version__ = '2.2-beta'
__description__ = '''(C)ount (a)rchive (r)oot (e)ntries.
Count entries at the root of an archive file so that one may decide whether or
not to unpack it to a new folder or to the current folder without messing up
other files under the current folder. If ``magic`` module, installed via pip
by name ``python-magic``, is not found, and the file type is not provided
explicity via command line options, then filename extension will be used to
guess the archive type. The return code: 0) success; 1) if the archive type
is not recognizable; 2) if error is raised when opening the archive. Currently
supported archive type: ZIP, TAR, GZ-compressed TAR, BZ2-compressed TAR,
XZ-compressed TAR.'''


import argparse
import sys
import zipfile
import tarfile
import importlib
from functools import partial
from pathlib import PurePath


def make_parser():
    parser = argparse.ArgumentParser(
            description=__description__.replace('\n', ' ').replace('. ', '.  '))
    parser.add_argument('archive', help='the archive file')
    mfb = parser.add_mutually_exclusive_group()  # (m)agic (f)all(b)ack
    mfb.add_argument('-T', '--file-type', dest='file_type',
                     choices=('zip', 'tar'),
                     help='the file type of ARCHIVE, where "tar" option '
                          'includes TAR archive and that compressed by gzip, '
                          'bzip2, or XZ')
    mfb.add_argument('-M', '--no-magic', dest='no_magic',
                     action='store_true',
                     help='don\'t even attempt to import `magic` module')
    mfb.add_argument('-W', '--no-ext-warning', dest='suppress_ext_warning',
                     action='store_true',
                     help='suppress warning into stderr when `magic` module '
                          'cannot be found')
    pres = parser.add_mutually_exclusive_group()  # (pres)entation option
    pres.add_argument('-f', '--with-filename', action='store_true',
                      dest='with_filename',
                      help='print the count as: "${count} ${filename}"')
    pres.add_argument('-l', '--list', action='store_true',
                      help='rather than print the count, list all unique '
                           'root entries')
    return parser


class UnrecognizableArchiveError(BaseException): pass
class ArchiveReadError(BaseException): pass

def guess_archive_type_ext(filename: str) -> str:
    ext2at = [
        (['.zip'], 'zip'),
        (['.tar'], 'tar'),
        # to be opened with transparent compression
        (['.tar.gzip', '.tar.gz', '.tgz' ], 'tar'),
        (['.tar.bzip2', '.tar.bz2'], 'tar'),
        (['.tar.xzip', '.tar.xz'], 'tar'),
    ]
    expanded_ext2at = [(k, v) for l, v in ext2at for k in l]
    at = [v for k, v in expanded_ext2at if filename.endswith(k)]
    assert len(at) <= 1, 'Illegal ``ext2at`` specification'
    if at:
        return at[0]
    else:
        raise UnrecognizableArchiveError()


def guess_archive_type_magic(magic, filename: str) -> str:
    """
    :param magic: the python-magic module
    :param filename: the archive filename
    """
    mime = magic.from_file(filename)
    kw2at = [
        ('Zip archive', 'zip'),
        ('tar archive', 'tar'),
        # to be opened with transparent compression
        ('gzip compressed data', 'tar'),
        ('bzip2 compressed data', 'tar'),
        ('XZ compressed data', 'tar'),
    ]
    at = [v for k, v in kw2at if k in mime]
    assert len(at) <= 1, 'Illegal ``kw2at`` specification'
    if at:
        return at[0]
    else:
        return UnrecognizableArchiveError()


def get_archive_entries(filename, archive_type):
    if archive_type == 'zip':
        try:  # just in case
            with zipfile.ZipFile(filename) as infile:
                entries = map(PurePath, infile.namelist())
        except zipfile.BadZipFile:
            raise ArchiveReadError()
    elif archive_type == 'tar':
        try:
            with tarfile.open(filename) as infile:
                entries = map(PurePath, infile.getnames())
        except tarfile.ReadError:
            raise ArchiveReadError()
    else:
        assert False
    return entries  # iter object, not list


def get_root_entry(tokenized_entry: list):
    while len(tokenized_entry) and tokenized_entry[0] in ['.', '..']:
        tokenized_entry = tokenized_entry[1:]
    root = None
    if len(tokenized_entry):
        root = tokenized_entry[0]
    return root


def count_root_entries(entry_names, return_root_entries=False):
    """
    :param entry_names: the names of entries in the archive
    :param return_root_entries: if True, also returns the unique root entires
    :return: the count of root entries
    """
    tokenized_entries = iter(e.parts for e in entry_names)
    root_entries = map(get_root_entry, tokenized_entries)
    _seen = set()
    uniq_root_entries = []
    for e in root_entries:
        if e not in _seen:
            _seen.add(e)
            uniq_root_entries.append(e)
    count = len(uniq_root_entries)
    if return_root_entries:
        return count, uniq_root_entries
    else:
        return count


def main():
    args = make_parser().parse_args()
    if args.file_type:
        archive_type = args.file_type
    elif args.no_magic:
        try:
            archive_type = guess_archive_type_ext(args.archive)
        except UnrecognizableArchiveError:
            return 1
    else:
        try:
            magic = importlib.import_module('magic')
        except ImportError:
            if not args.suppress_ext_warning:
                msg = ('Warning: error loading `python-magic` module; using '
                       'filename extension to decide archive type')
                print(msg, file=sys.stderr)
            try:
                guess_archive_type = guess_archive_type_ext
            except UnrecognizableArchiveError:
                return 1
        else:
            guess_archive_type = partial(guess_archive_type_magic, magic)
        archive_type = guess_archive_type(args.archive)

    try:
        entries = get_archive_entries(args.archive, archive_type)
    except ArchiveReadError:
        return 2

    if args.list:
        _, rentries = count_root_entries(entries, return_root_entries=True)
        print('\n'.join(rentries))
    else:
        count = count_root_entries(entries)
        if args.with_filename:
            print(count, args.archive)
        else:
            print(count)

if __name__ == '__main__':
    retcode = main()
    sys.exit(retcode)
