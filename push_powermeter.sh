ssh cap schtasks /end /tn StartPowermeter
scp powermeter.py cap:Desktop
scp powermeter.json cap:Desktop
ssh cap schtasks /run /tn StartPowermeter
