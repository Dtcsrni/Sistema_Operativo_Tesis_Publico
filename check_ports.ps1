$ports = 21434, 11434, 8765, 8080
Get-NetTCPConnection -State Listen | Where-Object {$_.LocalPort -in $ports} | Select-Object LocalPort, State, OwningProcess
