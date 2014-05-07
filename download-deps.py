#!/usr/bin/env python
#coding=utf-8
#
# ./download-deps.py
#
# Download Cocos2D-X resources from github (https://github.com/cocos2d/cocos2d-x-external) and extract from ZIP
#
# Helps prevent repo bloat due to large binary files since they can
# be hosted separately.
#

"""****************************************************************************
Copyright (c) 2014 cocos2d-x.org
Copyright (c) 2014 Chukong Technologies Inc.

http://www.cocos2d-x.org

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
****************************************************************************"""


import urllib2
import os.path,zipfile
import shutil
import sys
import traceback
import distutils
import fileinput

from optparse import OptionParser
from time import time
from sys import stdout
from distutils.errors import DistutilsError
from distutils.dir_util import copy_tree, remove_tree

_workpath=''

# -- Section for configuring file url -----
# github server may not reponse a header information which contains `Content-Length`,
# therefore, the size needs to be written hardcode here. While server doesn't return
# `Content-Length`, use it instead
_zip_file_bytes = 57132755
_repo_name = 'cocos2d-x-external'
_filename_prefix = 'v3-deps-1'
_filename = _filename_prefix + '.zip'
_downloaded_file_url = 'https://github.com/cocos2d/' + _repo_name + '/archive/' + _filename
# 'v' letter was swallowed by github, so we need to substring it from the 2nd letter
_extracted_folder_name = _repo_name + '-' + _filename_prefix[1:]
# ----------------------------------------

_remove_downloaded_zip_file = None

def get_input_value(prompt):
    ret = raw_input(prompt)
    ret.rstrip(" \t")
    return ret

def download_file(url, filename):
    print("==> Ready to download '%s' from '%s'" % (filename, url))

    u = urllib2.urlopen(url)
    f = open(filename, 'wb')
    meta = u.info()
    content_len = meta.getheaders("Content-Length")
    file_size = 0
    if content_len and len(content_len) > 0:
        file_size = int(content_len[0])
    else:
        print("==> WARNING: Couldn't grab the file size!")
        file_size = _zip_file_bytes

    print("==> Start to download, please wait ...")

    file_size_dl = 0
    block_sz = 8192
    block_size_per_second = 0
    old_time=time()

    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        block_size_per_second += len(buffer)
        f.write(buffer)
        new_time = time()
        if (new_time - old_time) > 1:
            speed = block_size_per_second / (new_time - old_time) / 1000.0
            status = ""
            if file_size != 0:
                percent = file_size_dl * 100. / file_size
                status = r"Downloaded: %6dK / Total: %dK, Percent: %3.2f%%, Speed: %6.2f KB/S " % (file_size_dl / 1000, file_size / 1000, percent, speed)
            else:
                status = r"Downloaded: %6dK, Speed: %6.2f KB/S " % (file_size_dl / 1000, speed)

            status = status + chr(8)*(len(status)+1)
            print(status),
            sys.stdout.flush()
            block_size_per_second = 0
            old_time = new_time

    print("==> Downloading finished!")
    f.close()

def default_filter(src,dst):
    """The default progress/filter callback; returns True for all files"""
    return dst

def ensure_directory(target):
    if not os.path.exists(target):
        os.mkdir(target)


class UnrecognizedFormat:
    def __init__(self, prompt):
        self._prompt = prompt
    def __str__(self):
        return self._prompt

def unpack_zipfile(filename, extract_dir, progress_filter=default_filter):
    """Unpack zip `filename` to `extract_dir`

    Raises ``UnrecognizedFormat`` if `filename` is not a zipfile (as determined
    by ``zipfile.is_zipfile()``).  See ``unpack_archive()`` for an explanation
    of the `progress_filter` argument.
    """

    if not zipfile.is_zipfile(filename):
        raise UnrecognizedFormat("%s is not a zip file" % (filename))

    print("==> Extracting files, please wait ...")
    z = zipfile.ZipFile(filename)
    try:
        for info in z.infolist():
            name = info.filename

            # don't extract absolute paths or ones with .. in them
            if name.startswith('/') or '..' in name:
                continue

            target = os.path.join(extract_dir, *name.split('/'))
            target = progress_filter(name, target)
            if not target:
                continue
            if name.endswith('/'):
                # directory
                ensure_directory(target)
            else:
                # file
                data = z.read(info.filename)
                f = open(target,'wb')
                try:
                    f.write(data)
                finally:
                    f.close()
                    del data
            unix_attributes = info.external_attr >> 16
            if unix_attributes:
                os.chmod(target, unix_attributes)
    finally:
        z.close()
        print("==> Extraction done!")


def ask_to_delete_downloaded_zip_file(filename):
    ret = get_input_value("==> Whether to delete the downloaded zip file? It may be reused when you execute this script next time! (yes/no): ")
    ret = ret.strip()
    if ret != 'yes' and ret != 'no':
        print("==> Invalid answer, please answer 'yes' or 'no'!")
        ask_to_delete_downloaded_zip_file(filename)

    if ret == "yes":
        os.remove(filename)

def download_and_unzip_file(url, filename):
    if not os.path.isfile(filename):
        download_file(url, filename)
    try:
        unpack_zipfile(filename, _workpath)
    except UnrecognizedFormat as e:
        print("==> Unrecognized zip format from your local '%s' file!" % (filename))
        if os.path.isfile(filename):
            os.remove(filename)
        print("==> Download it from internet again, please wait...")
        download_and_unzip_file(url, filename)

def main():
    _workpath = os.path.dirname(os.path.realpath(__file__))

    if os.path.exists(_extracted_folder_name):
        shutil.rmtree(_extracted_folder_name)

    download_and_unzip_file(_downloaded_file_url, _filename)

    print("==> Copying files...")
    folder_for_extracting = os.path.join(_workpath, 'external')
    if not os.path.exists(folder_for_extracting):
        os.mkdir(folder_for_extracting)
    distutils.dir_util.copy_tree(_extracted_folder_name, folder_for_extracting)
    print("==> Cleaning...")
    if os.path.exists(_extracted_folder_name):
        shutil.rmtree(_extracted_folder_name)
    if _remove_downloaded_zip_file:
        if os.path.isfile(_filename):
            os.remove(_filename)
    else:
        if os.path.isfile(_filename):
            ask_to_delete_downloaded_zip_file(_filename)
    print("==> DONE! Prebuilt libraries were installed successfully! Cheers!")


def _check_python_version():
    major_ver = sys.version_info[0]
    if major_ver > 2:
        print ("The python version is %d.%d. But python 2.x is required. (Version 2.7 is well tested)\n"
               "Download it here: https://www.python.org/" % (major_ver, sys.version_info[1]))
        return False

    return True

# -------------- main --------------
if __name__ == '__main__':
    try:
        if not _check_python_version():
            exit()

        parser = OptionParser()
        parser.add_option('-r', '--remove-download',
                          action="store_true", dest='to_remove_downloaded_zip_file', default=False,
                          help='Whether to remove downloaded zip file')
        (opts, args) = parser.parse_args()

        if opts.to_remove_downloaded_zip_file:
            _remove_downloaded_zip_file = True

        main()
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)
