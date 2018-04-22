#!/bin/bash

DATABASE=false

### Install packages ###
apt-get update -y
apt-get install apache2 libapache2-mod-php7.0 -y
apt-get install php7.0-gd php7.0-json php7.0-mysql php7.0-curl php7.0-mbstring -y
apt-get install php7.0-intl php7.0-mcrypt php-imagick php7.0-xml php7.0-zip php7.0-ldap -y
apt-get install mariadb-client-core-10.0 -y

### Setup Database ###
if [[ $DATABASE == 'true' ]];  then
	echo "
	CREATE USER 'nextclouduser'@'%' IDENTIFIED BY 'nextcloud!!';
	GRANT ALL ON nextcloud.* TO 'nextclouduser'@'%';" > db_commands.mysql
	mysql -h armekh860d7bzp.c5xhgy8yojo5.us-east-1.rds.amazonaws.com -u awsfred -pnextcloudisthebestforfrederick < db_commands.mysql
fi

### Install NextCloud ###
wget https://download.nextcloud.com/server/releases/nextcloud-13.0.1.tar.bz2
tar -xjf nextcloud-13.0.1.tar.bz2
cp -r nextcloud /var/www

