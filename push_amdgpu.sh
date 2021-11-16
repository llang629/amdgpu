ssh cap schtasks /end /tn StartAmdgpu
scp amdgpu.py cap:Desktop
scp -r amdgpu-public cap:Desktop
ssh cap schtasks /run /tn StartAmdgpu
