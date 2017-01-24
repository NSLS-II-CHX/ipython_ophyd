from bluesky.plans import DeltaScanPlan
from bluesky.callbacks import LiveTable, LivePlot
subs = [LiveTable(['ivu_gap', 'xray_eye3_stats1_total', 'xray_eye3_stats1_total']), 
        LivePlot('xray_eye3_stats1_total', 'ivu_gap')]
print(ivu_gap.read())
RE(DeltaScanPlan([xray_eye3], ivu_gap, -.1, .1, 3), subs)
print(ivu_gap.read())
