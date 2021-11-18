ssh cap schtasks /end /tn StartAmdgpu
scp powermeter.py cap:Desktop
scp powermeter.json cap:Desktop
ssh cap schtasks /run /tn StartAmdgpu
