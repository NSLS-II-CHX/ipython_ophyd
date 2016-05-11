
from bluesky.plans import DeltaScanPlan
from bluesky.callbacks import LiveTable, LivePlot


subs = [LiveTable(['diff_xh', 'eiger4m_single_stats1_total', 'eiger4m_single_stats2_total']), 
        LivePlot('eiger4m_single_stats1_total', 'diff_xh')]
print ( 'The fast shutter will open/close three times, motor is diff.xh, camera is eiger4m_single')
RE(DeltaScanPlan([eiger4m_single], diff.xh, -.1, .1, 3), subs)

#can we change only one mater file for the same dscan?
