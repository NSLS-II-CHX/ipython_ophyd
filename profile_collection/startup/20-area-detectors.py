import time as ttime  # tea time
from datetime import datetime
from ophyd import (ProsilicaDetector, SingleTrigger, TIFFPlugin,
                   ImagePlugin, StatsPlugin, DetectorBase, HDF5Plugin,
                   AreaDetector, EpicsSignal, EpicsSignalRO, ROIPlugin,
                   TransformPlugin, ProcessPlugin)
from ophyd.areadetector.cam import AreaDetectorCam
from ophyd.areadetector.base import ADComponent, EpicsSignalWithRBV
from ophyd.areadetector.filestore_mixins import (FileStoreTIFFIterativeWrite,
                                                 FileStoreHDF5IterativeWrite,
                                                 FileStoreBase, new_short_uid,
                                                 FileStoreIterativeWrite)
from ophyd import Component as Cpt, Signal
from ophyd.utils import set_and_wait
import filestore.api as fs


#class Elm(SingleTrigger, DetectorBase):
 #   pass






class TIFFPluginWithFileStore(TIFFPlugin, FileStoreTIFFIterativeWrite):
    """Add this as a component to detectors that write TIFFs."""
    pass


class TIFFPluginEnsuredOff(TIFFPlugin):
    """Add this as a component to detectors that do not write TIFFs."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_sigs.update([(self.auto_save, 'No')])


class StandardProsilica(SingleTrigger, ProsilicaDetector):
    image = Cpt(ImagePlugin, 'image1:')
    stats1 = Cpt(StatsPlugin, 'Stats1:')
    stats2 = Cpt(StatsPlugin, 'Stats2:')
    stats3 = Cpt(StatsPlugin, 'Stats3:')
    stats4 = Cpt(StatsPlugin, 'Stats4:')
    stats5 = Cpt(StatsPlugin, 'Stats5:')
    trans1 = Cpt(TransformPlugin, 'Trans1:')
    roi1 = Cpt(ROIPlugin, 'ROI1:')
    roi2 = Cpt(ROIPlugin, 'ROI2:')
    roi3 = Cpt(ROIPlugin, 'ROI3:')
    roi4 = Cpt(ROIPlugin, 'ROI4:')
    proc1 = Cpt(ProcessPlugin, 'Proc1:')

    # This class does not save TIFFs. We make it aware of the TIFF plugin
    # only so that it can ensure that the plugin is not auto-saving.
    tiff = Cpt(TIFFPluginEnsuredOff, suffix='TIFF1:')


class StandardProsilicaWithTIFF(StandardProsilica):
    tiff = Cpt(TIFFPluginWithFileStore,
               suffix='TIFF1:',
               write_path_template='/XF11ID/data/%Y/%m/%d/')


class EigerSimulatedFilePlugin(Device, FileStoreBase):
    sequence_id = ADComponent(EpicsSignalRO, 'SequenceId')
    file_path = ADComponent(EpicsSignalWithRBV, 'FilePath', string=True)
    file_write_name_pattern = ADComponent(EpicsSignalWithRBV, 'FWNamePattern',
                                          string=True)
    file_write_images_per_file = ADComponent(EpicsSignalWithRBV, 'FWNImagesPerFile')
    current_run_start_uid = Cpt(Signal, value='', add_prefix=())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._datum_kwargs_map = dict()  # store kwargs for each uid

    def stage(self):
        res_uid = new_short_uid()
        write_path = datetime.now().strftime(self.write_path_template)
        set_and_wait(self.file_path, write_path)
        set_and_wait(self.file_write_name_pattern, '{}_$id'.format(res_uid))
        super().stage()
        fn = os.path.join(self.file_path.get(), res_uid)
        ipf = int(self.file_write_images_per_file.get())
        # logger.debug("Inserting resource with filename %s", fn)
        self._resource = fs.insert_resource('AD_EIGER2', fn, {'images_per_file': ipf})

    def generate_datum(self, key, timestamp):
        uid = super().generate_datum(key, timestamp)
        # The detector keeps its own counter which is uses label HDF5 sub-files.
        # We access that counter via the sequence_id signal and stash it in the datum.
        seq_id = 1 + int(self.sequence_id.get())  # det writes to the NEXT one
        fs.insert_datum(self._resource, uid, {'seq_id': seq_id})
        return uid


class EigerBase(AreaDetector):
    """
    Eiger, sans any triggering behavior.

    Use EigerSingleTrigger or EigerFastTrigger below.
    """
    num_triggers = ADComponent(EpicsSignalWithRBV, 'cam1:NumTriggers')
    file = Cpt(EigerSimulatedFilePlugin, suffix='cam1:',
               write_path_template='/XF11ID/data/%Y/%m/%d/')
    beam_center_x = ADComponent(EpicsSignalWithRBV, 'cam1:BeamX')
    beam_center_y = ADComponent(EpicsSignalWithRBV, 'cam1:BeamY')
    wavelength = ADComponent(EpicsSignalWithRBV, 'cam1:Wavelength')
    det_distance = ADComponent(EpicsSignalWithRBV, 'cam1:DetDist')
    threshold_energy = ADComponent(EpicsSignalWithRBV, 'cam1:ThresholdEnergy')
    photon_energy = ADComponent(EpicsSignalWithRBV, 'cam1:PhotonEnergy')
    image = Cpt(ImagePlugin, 'image1:')
    stats1 = Cpt(StatsPlugin, 'Stats1:')
    stats2 = Cpt(StatsPlugin, 'Stats2:')
    stats3 = Cpt(StatsPlugin, 'Stats3:')
    stats4 = Cpt(StatsPlugin, 'Stats4:')
    stats5 = Cpt(StatsPlugin, 'Stats5:')
    roi1 = Cpt(ROIPlugin, 'ROI1:')
    roi2 = Cpt(ROIPlugin, 'ROI2:')
    roi3 = Cpt(ROIPlugin, 'ROI3:')
    roi4 = Cpt(ROIPlugin, 'ROI4:')
    proc1 = Cpt(ProcessPlugin, 'Proc1:')

    shutter_mode = ADComponent(EpicsSignalWithRBV, 'cam1:ShutterMode')

    # hotfix: shadow non-existant PV
    size_link = None

class EigerSingleTrigger(SingleTrigger, EigerBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_sigs[self.cam.trigger_mode] = 0
        self.stage_sigs[self.shutter_mode] = 1  # 'EPICS PV'
        self.stage_sigs.update({self.num_triggers: 1})


class FastShutterTrigger(Device):
    """This represents the fast trigger *device*.
    
    See below, FastTriggerMixin, which defines the trigging logic.
    """
    auto_shutter_mode = Cpt(EpicsSignal, 'Mode-Sts', write_pv='Mode-Cmd')
    num_images = Cpt(EpicsSignal, 'NumImages-SP')
    exposure_time = Cpt(EpicsSignal, 'ExposureTime-SP')
    acquire_period = Cpt(EpicsSignal, 'AcquirePeriod-SP')
    acquire = Cpt(EpicsSignal, 'Acquire-Cmd', trigger_value=1)


class EigerFastTrigger(EigerBase):
    tr = Cpt(FastShutterTrigger, '')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_sigs[self.cam.trigger_mode] = 3  # 'External Enable' mode
        self.stage_sigs[self.shutter_mode] = 0  # 'EPICS PV'
        self.stage_sigs[self.tr.auto_shutter_mode] = 1 # 'Enable'

    def trigger(self):
        self.dispatch('image', ttime.time())
        return self.tr.trigger()

# test_trig4M = FastShutterTrigger('XF:11IDB-ES{Trigger:Eig4M}', name='test_trig4M')
        

## This renaming should be reversed: no correspondance between CSS screens, PV names and ophyd....
xray_eye1 = StandardProsilica('XF:11IDA-BI{Bpm:1-Cam:1}', name='xray_eye1')
xray_eye2 = StandardProsilica('XF:11IDB-BI{Mon:1-Cam:1}', name='xray_eye2')
xray_eye3 = StandardProsilica('XF:11IDB-BI{Cam:08}', name='xray_eye3')
xray_eye1_writing = StandardProsilicaWithTIFF('XF:11IDA-BI{Bpm:1-Cam:1}', name='xray_eye1')
xray_eye2_writing = StandardProsilicaWithTIFF('XF:11IDB-BI{Mon:1-Cam:1}', name='xray_eye2')
xray_eye3_writing = StandardProsilicaWithTIFF('XF:11IDB-BI{Cam:08}', name='xray_eye3')
fs1 = StandardProsilica('XF:11IDA-BI{FS:1-Cam:1}', name='fs1')
fs2 = StandardProsilica('XF:11IDA-BI{FS:2-Cam:1}', name='fs2')
fs_wbs = StandardProsilica('XF:11IDA-BI{BS:WB-Cam:1}', name='fs_wbs')
dcm_cam = StandardProsilica('XF:11IDA-BI{Mono:DCM-Cam:1}', name='dcm_cam')
fs_pbs = StandardProsilica('XF:11IDA-BI{BS:PB-Cam:1}', name='fs_pbs')
#elm = Elm('XF:11IDA-BI{AH401B}AH401B:',)

all_standard_pros = [xray_eye1, xray_eye2, xray_eye3, xray_eye1_writing, xray_eye2_writing,
                     xray_eye3_writing, fs1, fs2, fs_wbs, dcm_cam, fs_pbs]
for camera in all_standard_pros:
    camera.read_attrs = ['stats1', 'stats2','stats3','stats4','stats5']
    # camera.tiff.read_attrs = []  # leaving just the 'image'
    for stats_name in ['stats1', 'stats2','stats3','stats4','stats5']:
        stats_plugin = getattr(camera, stats_name)
        stats_plugin.read_attrs = ['total']
        camera.stage_sigs[stats_plugin.blocking_callbacks] = 1

    camera.stage_sigs[camera.roi1.blocking_callbacks] = 1
    camera.stage_sigs[camera.trans1.blocking_callbacks] = 1
    camera.stage_sigs[camera.cam.trigger_mode] = 'Fixed Rate'


for camera in [xray_eye1_writing, xray_eye2_writing, xray_eye3_writing]:
    camera.read_attrs.append('tiff')
    camera.tiff.read_attrs = []

def set_eiger_defaults(eiger):
    "Choose which attributes to read per-step (read_attrs) or per-run (configuration attrs)."

    eiger.file.read_attrs = []
    eiger.read_attrs = ['file','stats1', 'stats2', 'stats3', 'stats4', 'stats5']
    for stats in [eiger.stats1, eiger.stats2, eiger.stats3, eiger.stats4, eiger.stats5]:
        stats.read_attrs = ['total']
    eiger.configuration_attrs = ['beam_center_x', 'beam_center_y', 'wavelength', 'det_distance', 'cam',
                                 'threshold_energy', 'photon_energy']
    eiger.cam.read_attrs = []
    eiger.cam.configuration_attrs = ['acquire_time', 'acquire_period', 'num_images']


# Eiger 1M using internal trigger
eiger1m_single = EigerSingleTrigger('XF:11IDB-ES{Det:Eig1M}', name='eiger1m_single')
set_eiger_defaults(eiger1m_single)

# Eiger 4M using internal trigger
eiger4m_single = EigerSingleTrigger('XF:11IDB-ES{Det:Eig4M}', name='eiger4m_single')
set_eiger_defaults(eiger4m_single)

# Eiger 1M using fast trigger assembly
eiger1m = EigerFastTrigger('XF:11IDB-ES{Det:Eig1M}', name='eiger1m')
set_eiger_defaults(eiger1m)

# Eiger 4M using fast trigger assembly
eiger4m = EigerFastTrigger('XF:11IDB-ES{Det:Eig4M}', name='eiger4m')
set_eiger_defaults(eiger4m)


# Comment this out to suppress deluge of logging messages.
#import logging
#logging.basicConfig(level=logging.DEBUG)
#import ophyd.areadetector.filestore_mixins
#ophyd.areadetector.filestore_mixins.logger.setLevel(logging.DEBUG)
