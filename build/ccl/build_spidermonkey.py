#!/usr/bin/python3
#************************************************************************************************
#
# Build Script for Mozilla Spidermonkey
#
# This file is part of the CCL Cross-platform Framework. 
# Copyright (c) 2024 CCL Software Licensing GmbH. All Rights Reserved.
#
# Permission to use this file is subject to commercial licensing
# terms and conditions. For more information, please visit ccl.dev.
#
# Filename    : build/ccl/build_spidermonkey.py
# Description : Build Spidermonkey static libs from scratch
#
#************************************************************************************************

import argparse
import os
import subprocess
import sys
import zipfile

def create_mozconfig (platform, arch):
    config = '# Build only the JS shell\n'
    config += 'ac_add_options --enable-application=js\n'

    if args.debug:
        config += 'ac_add_options --enable-debug\n'
        config += '# Disable Optimization, for the most accurate debugging experience\n'
        config += 'ac_add_options --disable-optimize\n'

    if platform == 'macos':
        config += 'ac_add_options --with-macos-sdk=/Library/Developer/CommandLineTools/SDKs/MacOSX11.1.sdk\n'
        config += 'ac_add_options --enable-macos-target=10.13\n'

    if platform == 'win' or platform == 'android':
        if not args.debug and not args.symbols:
            config += 'ac_add_options --disable-debug-symbols\n'

    config += 'ac_add_options --disable-tests\n'

    if platform == 'android':
        config += 'ac_add_options --with-android-ndk=c:/mozilla-build/android-ndk-r27c\n'
        config += 'ac_add_options --target=' + arch + '-linux-android' + '\n'
    else:
        config += 'ac_add_options --target=' + arch + '\n'

    config += '# this enables static linking of mozglue\n'
    config += 'ac_add_options --disable-jemalloc\n'

    config += 'mk_add_options MOZ_OBJDIR=' + basedir + '/obj-' + platform + '-' + arch + '\n'
    return config

def exec_mach (command):
	if platform == 'macos' or platform == 'linux':
		subprocess.run ([machpath, command])
	elif platform == 'win' or platform == 'android':
		subprocess.run (['python3', machpath, command])

def build_one (platform, arch):
    with open ('MOZCONFIG', '+w') as f:
        f.write (create_mozconfig (platform, arch))

    exec_mach ('build')

    if (platform == 'macos') and not args.debug and not args.symbols:
        subprocess.run (['/usr/bin/strip', '-u', '-r', '-S', 'obj-' + platform + '-' + arch + '/js/src/build/libjs_static.a'])
        subprocess.run (['/usr/bin/strip', '-u', '-r', '-S', 'obj-' + platform + '-' + arch + '/' + arch + '-apple-darwin/release/libjsrust.a'])

    if (platform == 'linux') and not args.debug and not args.symbols:
        if arch == 'x86_64':
            subprocess.run (['/usr/bin/strip', '--strip-unneeded', '--strip-debug', 'obj-' + platform + '-' + arch + '/js/src/build/libjs_static.a'])
            subprocess.run (['/usr/bin/strip', '--strip-unneeded', '--strip-debug', 'obj-' + platform + '-' + arch + '/' + arch + '-unknown-linux-gnu/release/libjsrust.a'])
        else:
            subprocess.run (['/usr/bin/' + arch + '-linux-gnu-strip', '--strip-unneeded', '--strip-debug', 'obj-' + platform + '-' + arch + '/js/src/build/libjs_static.a'])
            subprocess.run (['/usr/bin/' + arch + '-linux-gnu-strip', '--strip-unneeded', '--strip-debug', 'obj-' + platform + '-' + arch + '/' + arch + '-unknown-linux-gnu/release/libjsrust.a'])

def zip_dir (zip, path):
    for root, dirs, files in os.walk (path):
        for file in files:
            zip.write (os.path.join (root, file))

scriptdir = os.path.dirname (os.path.abspath (__file__)).replace ('\\', '/')

parser = argparse.ArgumentParser (description = 'Build Spidermonkey static libs from scratch')
parser.add_argument ('-b', '--basedir', default = '.', help = 'working directory for build (default: pwd)')
parser.add_argument ('-r', '--sourcedir', default = scriptdir + '/../..', help = 'path to gecko source repository (default: {scriptdir}/../..)')
parser.add_argument ('-p', '--platform', default = 'macos', help = 'platform to build: macos or win or linux or android (default: macos)')
parser.add_argument ('--clobber', nargs = '?', const = '1', help = 'clean existing source directory')
parser.add_argument ('-d', '--debug', nargs = '?', const = '1', help = 'create a debug build (implies --debug-crt)')
parser.add_argument ('-s', '--symbols', nargs = '?', const = '1', help = 'include symbols in release builds')
parser.add_argument ('--debug-crt', nargs = '?', const = '1', help = 'use a debug CRT on Windows')
                   
args = parser.parse_args ()
platform = args.platform

basedir = os.path.abspath (args.basedir).replace ('\\', '/')
sourcedir = os.path.abspath (args.sourcedir).replace ('\\', '/')
machpath = os.path.abspath (os.path.join (sourcedir, 'mach')).replace ('\\', '/')

os.environ['MACH_BUILD_PYTHON_NATIVE_PACKAGE_SOURCE'] = 'system'

os.chdir (sourcedir)

if args.clobber and os.access (sourcedir, os.W_OK):
    print ('Cleaning up ' + sourcedir + ' ...')
    subprocess.run (["git", "clean", "-xdf"])

os.environ['NO_RUST_PANIC_HOOK'] = '1'
os.environ['MOZCONFIG'] = basedir + '/MOZCONFIG'

version = subprocess.check_output(['grep', '^[0-9]', 'config/milestone.txt']).decode(sys.stdout.encoding)
version = version.replace('a1', '').replace('\n', '')

os.chdir (basedir)

if args.debug:
    folder = 'debug'
else:
    folder = 'release'

if platform == 'macos':
    architectures = ['x86_64', 'aarch64']

    for architecture in architectures:
        build_one (platform, architecture)

    subprocess.run (['/usr/bin/lipo', '-create', '-output', 'libjs_static.a', 'obj-macos-x86_64/js/src/build/libjs_static.a', 'obj-macos-aarch64/js/src/build/libjs_static.a'])
    subprocess.run (['/usr/bin/lipo', '-create', '-output', 'libjsrust.a', 'obj-macos-x86_64/x86_64-apple-darwin/' + folder + '/libjsrust.a', 'obj-macos-aarch64/aarch64-apple-darwin/' + folder + '/libjsrust.a'])

    with zipfile.ZipFile (basedir + '/spidermonkey-' + version + '.mac.zip', mode = 'w') as buildproducts:
        os.chdir ('obj-' + platform + '-' + architectures[0])
        zip_dir (buildproducts, 'dist/include')
        os.chdir ('..')

        buildproducts.write ('libjs_static.a')
        buildproducts.write ('libjsrust.a')

elif platform == 'linux':
    architectures = ['x86_64', 'aarch64']

    for architecture in architectures:
        build_one (platform, architecture)

    with zipfile.ZipFile (basedir + '/spidermonkey-' + version + '.linux.zip', mode = 'w') as buildproducts:
        os.chdir ('obj-' + platform + '-' + architectures[0])
        zip_dir (buildproducts, 'dist/include')
        os.chdir ('..')

        for architecture in architectures:
            os.chdir ('obj-' + platform + '-' + architecture + '/js/src/build/')
            buildproducts.write ('libjs_static.a', 'obj-' + platform + '-' + architecture + '-' + folder + '/libjs_static.a')
            os.chdir ('../../../..')
            os.chdir ('obj-' + platform + '-' + architecture + '/' + architecture + '-unknown-linux-gnu/' + folder)
            buildproducts.write ('libjsrust.a', 'obj-' + platform + '-' + architecture + '-' + folder + '/libjsrust.a')
            os.chdir ('../../..')

elif platform == 'win':
    architectures = ['x86_64', 'i686', 'aarch64']

    os.environ['CXXFLAGS'] = ''

    if args.debug or args.debug_crt:
        # use multithreaded dynamic debug runtime
        os.environ['CXXFLAGS'] += '-D_DEBUG=1 -MDd'

    for architecture in architectures:
        build_one (platform, architecture)

    with zipfile.ZipFile (basedir + '/spidermonkey-' + version + '.win-' + folder + '.zip', mode = 'w')  as buildproducts:
        os.chdir ('obj-' + platform + '-' + architectures[0])
        zip_dir (buildproducts, 'dist/include')
        os.chdir ('..')

        for architecture in architectures:
            os.chdir ('obj-' + platform + '-' + architecture + '/js/src/build/')
            buildproducts.write ('js_static.lib', 'obj-' + platform + '-' + architecture + '-' + folder + '/js_static.lib')
            os.chdir ('../../../..')
            os.chdir ('obj-' + platform + '-' + architecture + '/' + architecture + '-pc-windows-msvc/' + folder)
            buildproducts.write ('jsrust.lib', 'obj-' + platform + '-' + architecture + '-' + folder + '/jsrust.lib')
            os.chdir ('../../..')

elif platform == 'android':
    architectures = ['x86_64', 'i686', 'aarch64', 'arm']
    
    os.environ['CXXFLAGS'] = '-frtti'

    for architecture in architectures:
        build_one (platform, architecture)
    
    with zipfile.ZipFile (basedir + '/spidermonkey-' + version + '.android-' + folder + '.zip', mode = 'w')  as buildproducts:
        os.chdir ('obj-' + platform + '-' + architectures[0])
        zip_dir (buildproducts, 'dist/include')
        os.chdir ('..')

        for architecture in architectures:
            rustabi = architecture + '-linux-android'
            if architecture == 'arm':
                rustabi = 'thumbv7neon-linux-androideabi'

            os.chdir ('obj-' + platform + '-' + architecture + '/js/src/build/')
            buildproducts.write ('libjs_static.a', 'obj-' + platform + '-' + architecture + '-' + folder + '/libjs_static.a')
            os.chdir ('../../../..')
            os.chdir ('obj-' + platform + '-' + architecture + '/' + rustabi + '/' + folder)
            buildproducts.write ('libjsrust.a', 'obj-' + platform + '-' + architecture + '-' + folder + '/libjsrust.a')
            os.chdir ('../../..')
