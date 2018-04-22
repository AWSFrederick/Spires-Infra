#!/bin/bash

system_type=$(uname)

# Pull version for Mac, else default to linux x64
if [[ $system_type == *"Darwin"*  ]]; then
	curl https://releases.hashicorp.com/packer/1.2.2/packer_1.2.2_darwin_amd64.zip --output packer.zip
else
	curl https://releases.hashicorp.com/packer/1.2.2/packer_1.2.2_linux_amd64.zip --output packer.zip
fi
unzip -a packer.zip
rm packer.zip
chmod 755 ./packer
./packer version
