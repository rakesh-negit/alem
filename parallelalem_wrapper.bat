@ECHO off

SET /a i=0
:loop
IF %i%==1000 GOTO END

tasklist | gawk "/cmd.exe/ { print $2 }" > pids1
start python parallelalem.py %1 %2
tasklist | gawk "/cmd.exe/ { print $2 }" > pids2
diff pids1 pids2 | gawk "NR==2 { print $2 }" > tmpFile
set /p pid= < tmpFile
del pids1
del pids2
del tmpFile
sleep %3
taskkill /F /T /PID %pid%
taskkill /F /IM python.exe /T

SET /a i=%i%+1
GOTO LOOP
:end

@ECHO on