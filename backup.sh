# !/bin/bash
dir2make="/mnt/datamanager_backup/$(date +"%d-%m-%Y_%H-%M")"
sudo mount -o rw /mnt/datamanager_backup
mkdir $dir2make
cp -r -f --no-preserve=mode,ownership /home/aaron/Documents/Data-Manager/src/database/{db_main.db,uploaded_files,conditions} $dir2make
sudo umount /mnt/datamanager_backup
