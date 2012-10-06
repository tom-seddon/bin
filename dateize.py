#!/usr/bin/python
import glob,re,os,os.path,stat,time,exceptions,shutil,sys

# dateize

# Moves files in the current folder into folders, based on the year
# and month of their ctime.
#
# Designed for periodic use in one's download folder.

dated_re=re.compile("^[0-9][0-9][0-9][0-9]-[0-9][0-9]$")

names=glob.glob("*")

# print names

for name in names:
    if dated_re.match(name):
        continue

    try:
        # The `ctime' is as good as it gets on Mac OS X.
        ctime=time.gmtime(os.path.getctime(name))

        month,year=ctime.tm_mon,ctime.tm_year

        dated_folder="%04d-%02d"%(year,
                                  month)

        if not os.path.isdir(dated_folder):
            os.makedirs(dated_folder)

        shutil.move(name,
                    dated_folder)

        print "%s -> %s"%(name,dated_folder)
        
    except (exceptions.OSError,
            shutil.Error),e:
        sys.stderr.write("%s: %s\n"%(name,
                                     str(e)))
