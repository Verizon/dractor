# Copyright (C) 2017 Verizon. All Rights Reserved.
#
#     File:    Vagrantfile
#     Author:  Phil Chandler
#     Date:    2017-02-20
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

# -*- mode: ruby -*-
# vi: set ft=ruby :

RSYNC_EXCLUDES_FOR_SRC = %w(
  .git/
  .tox/
  __pycache__/
  *.py[cod]
  *$py.class
  *.so
  .Python
  env/
  build/
  dist/
  develop-eggs/
  docs/build/
  downloads/
  eggs/
  .eggs/
  lib/
  lib64/
  parts/
  sdist/
  var/
  *.egg-info/
  .installed.cfg
  *.egg
  *.manifest
  *.spec
  pip-log.txt
  pip-delete-this-directory.txt
  htmlcov/
  .tox/
  .coverage
  .coverage.*
  .cache
  nosetests.xml
  coverage.xml
  *,cover
  .hypothesis/
)

Vagrant.configure(2) do |config|

  # vagrant plugins
  if Vagrant.has_plugin?("vagrant-cachier")
    config.cache.scope = :box
  end

  # sync the bulk of the stuff via one-way rsync
  config.vm.synced_folder ".",
                          "/home/ubuntu/dractor",
                          type: "rsync",
                          rsync__auto: true,
                          rsync__verbose: true,
                          rsync__exclude: RSYNC_EXCLUDES_FOR_SRC

  # use two-way syncing for the wheel and sphinx docs output directories
  config.vm.synced_folder "dist/", "/home/ubuntu/dractor/dist"
  config.vm.synced_folder "docs/build/", "/home/ubuntu/dractor/docs/build"

  # vm for trusty
  config.vm.define "trusty64", primary: true, autostart: true do |trusty|
    trusty.vm.box = "ubuntu/trusty64"
    config.vm.provision "shell", privileged: true, inline: %q(
      apt-get update
      apt-get install -y python python-dev python-pip
      pip install -U pip setuptools tox
    )
  end

  # vm for xenial
  config.vm.define "xenial64", primary: false, autostart: false do |xenial|
    xenial.vm.box = "ubuntu/xenial64"
    config.vm.provision "shell", privileged: true, inline: %q(
      apt-get update
      apt-get install -y python2.7 python2.7-dev tox
    )
  end

end
