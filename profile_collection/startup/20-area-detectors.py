import time as ttime  # tea time
from ophyd import (ProsilicaDetector, SingleTrigger, TIFFPlugin,
                   ImagePlugin, StatsPlugin, DetectorBase, HDF5Plugin,
                   AreaDetector, EpicsSignal, EpicsSignalRO)
from ophyd.areadetector.cam import AreaDetectorCam
from ophyd.areadetector.base import ADComponent, EpicsSignalWithRBV
from ophyd.areadetector.filestore_mixins import (FileStoreTIFFIterativeWrite,
                                                 FileStoreHDF5IterativeWrite,
                                                 FileStoreBase, new_short_uid)
from ophyd import Component as Cpt
from ophyd.utils import set_and_wait
import filestore.api as fs


class Elm(SingleTrigger, DetectorBase):
    pass


class TIFFPluginWithFileStore(TIFFPlugin, FileStoreTIFFIterativeWrite):
    pass


class StandardProsilica(SingleTrigger, ProsilicaDetector):
    # tiff = Cpt(TIFFPluginWithFileStore,
    #           suffix='TIFF1:',
    #           write_path_template='/XF11ID/data/')
    image = Cpt(ImagePlugin, 'image1:')
    stats1 = Cpt(StatsPlugin, 'Stats1:')
    stats2 = Cpt(StatsPlugin, 'Stats2:')
    stats3 = Cpt(StatsPlugin, 'Stats3:')
    stats4 = Cpt(StatsPlugin, 'Stats4:')
    stats5 = Cpt(StatsPlugin, 'Stats5:')


class EigerSimulatedFilePlugin(Device, FileStoreBase):
    sequence_id = ADComponent(EpicsSignalRO, 'SequenceId')
    file_path = ADComponent(EpicsSignalWithRBV, 'FilePath', string=True)
    file_write_name_pattern = ADComponent(EpicsSignalWithRBV, 'FWNamePattern',
                                          string=True)
    file_write_images_per_file = ADComponent(EpicsSignalWithRBV, 'FWNImagesPerFile')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._datum_kwargs_map = dict()  # store kwargs for each uid

    def stage(self):
        res_uid = new_short_uid()
        set_and_wait(self.file_write_name_pattern, '{}_$id'.format(res_uid))
        super().stage()
        fn = os.path.join(self.file_path.get(), res_uid)
        res_kwargs = {'frame_per_point': self.get_frames_per_point()}
        logger.debug("Inserting resource with filename %s", fn)
        self._resource = fs.insert_resource('AD_EIGER', fn, res_kwargs)

    def get_frames_per_point(self):
        # TODO Get this from the fast trigger.
        return 1  # this is a placeholder, a lie

    def generate_datum(self, key, timestamp):
        # This code is similar (not identical) to FileStoreBulkWrite.
        "Stash kwargs for each datum, to be used below by unstage."
        uid = super().generate_datum(key, timestamp)
        i = next(self._point_counter)
        seq_id = 1 + int(self.sequence_id.get())  # det writes to the NEXT one
        self._datum_kwargs_map[uid] = {'seq_id': seq_id}
        # (don't insert, obviously)
        return uid

    def unstage(self):
        # This code is indentical to FileStoreBulkWrite -- refactor it out
        "Insert all datums at the end."
        for readings in self._datum_uids.values():
            for reading in readings:
                uid = reading['value']
                kwargs = self._datum_kwargs_map[uid]
                fs.insert_datum(self._resource, uid, kwargs)
        return super().unstage()


class EigerBase(AreaDetector):
    """
    Eiger, sans any triggering behavior.

    Use EigerSingleTrigger or EigerFastTrigger below.
    """
    num_triggers = ADComponent(EpicsSignalWithRBV, 'cam1:NumTriggers')
    file = Cpt(EigerSimulatedFilePlugin, suffix='cam1:',
               write_path_template='/XF11ID/data/%Y/%m/%d/')
    # cam = Cpt(CamWithFasterShutter, 'cam1:')
    # None of these are needed?
    image = Cpt(ImagePlugin, 'image1:')
    stats1 = Cpt(StatsPlugin, 'Stats1:')
    stats2 = Cpt(StatsPlugin, 'Stats2:')
    stats3 = Cpt(StatsPlugin, 'Stats3:')
    stats4 = Cpt(StatsPlugin, 'Stats4:')
    stats5 = Cpt(StatsPlugin, 'Stats5:')

    shutter_mode = ADComponent(EpicsSignalWithRBV, 'cam1:ShutterMode')


class EigerSingleTrigger(SingleTrigger, EigerBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_sigs[self.cam.trigger_mode] = 0
        self.stage_sigs[self.shutter_mode] = 1  # 'EPICS PV'


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
    tr = Cpt(FastShutterTrigger, 'XF:11IDB-ES{Trigger:Eig4M}', add_prefix=())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage_sigs[self.cam.trigger_mode] = 3  # 'External Enable' mode
        self.stage_sigs[self.shutter_mode] = 0  # 'EPICS PV'

    def trigger(self):
        self.dispatch('image', ttime.time())
        return self.tr.trigger()

# test_trig4M = FastShutterTrigger('XF:11IDB-ES{Trigger:Eig4M}', name='test_trig4M')
        

## This renaming should be reversed: no correspondance between CSS screens, PV names and ophyd....
xray_eye1 = StandardProsilica('XF:11IDA-BI{Bpm:1-Cam:1}', name='xray_eye1')
# These two are not installed 21 Jan 2016.
# xray_eye2 = StandardProsilica('XF:11IDA-BI{?????}', name='xray_eye2')
xray_eye3 = StandardProsilica('XF:11IDB-BI{Cam:08}', name='xray_eye3')
fs1 = StandardProsilica('XF:11IDA-BI{FS:1-Cam:1}', name='fs1')
fs2 = StandardProsilica('XF:11IDA-BI{FS:2-Cam:1}', name='fs2')
fs_wbs = StandardProsilica('XF:11IDA-BI{BS:WB-Cam:1}', name='fs_wbs')
dcm_cam = StandardProsilica('XF:11IDA-BI{Mono:DCM-Cam:1}', name='dcm_cam')
fs_pbs = StandardProsilica('XF:11IDA-BI{BS:PB-Cam:1}', name='fs_pbs')
# elm = Elm('XF:11IDA-BI{AH401B}AH401B:')

all_standard_pros = [xray_eye1, xray_eye3, fs1, fs2, fs_wbs, dcm_cam, fs_pbs]
for camera in all_standard_pros:
    camera.read_attrs = ['stats1', 'stats2','stats3','stats4','stats5']
    # camera.tiff.read_attrs = []  # leaving just the 'image'
    camera.stats1.read_attrs = ['total']
    camera.stats2.read_attrs = ['total']
    camera.stats3.read_attrs = ['total']
    camera.stats4.read_attrs = ['total']
    camera.stats5.read_attrs = ['total']

# Eiger 1M using internal trigger
eiger1m_single = EigerSingleTrigger('XF:11IDB-ES{Det:Eig1M}', name='eiger1m_single')
eiger1m_single.file.read_attrs = []
eiger1m_single.read_attrs = ['file','stats1']
eiger1m_single.stats1.read_attrs = ['total']

# Eiger 4M using internal trigger
eiger4m_single = EigerSingleTrigger('XF:11IDB-ES{Det:Eig4M}', name='eiger4m_single')
eiger4m_single.file.read_attrs = []
eiger4m_single.read_attrs = ['file','stats1']
eiger4m_single.stats1.read_attrs = ['total']


# Eiger 1M using fast trigger assembly
eiger1m = EigerFastTrigger('XF:11IDB-ES{Det:Eig1M}', name='eiger1m')
eiger1m.file.read_attrs = []
#eiger1m.read_attrs = ['file']
eiger1m.read_attrs = ['file','stats1', 'stats2', 'stats3', 'stats4','stats5']
eiger1m.stats1.read_attrs = ['total']
eiger1m.stats2.read_attrs = ['total']
eiger1m.stats3.read_attrs = ['total']
eiger1m.stats4.read_attrs = ['total']
eiger1m.stats5.read_attrs = ['total']


# Eiger 4M using fast trigger assembly
eiger4m = EigerFastTrigger('XF:11IDB-ES{Det:Eig4M}', name='eiger4m')
#eiger4m.file.read_attrs = []
#eiger4m.read_attrs = ['file', 'stats1']
eiger4m.read_attrs = ['file', 'stats1', 'stats2', 'stats3', 'stats4','stats5']
#eiger4m.read_attrs = []
eiger4m.stats1.read_attrs = ['total']
eiger4m.stats2.read_attrs = ['total']
eiger4m.stats3.read_attrs = ['total']
eiger4m.stats4.read_attrs = ['total']
eiger4m.stats5.read_attrs = ['total']


# Comment this out to suppress deluge of logging messages.
#import logging
#logging.basicConfig(level=logging.DEBUG)
#import ophyd.areadetector.filestore_mixins
#ophyd.areadetector.filestore_mixins.logger.setLevel(logging.DEBUG)