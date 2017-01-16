import time


class TimeRecord(object):
    def __init__(self):
        self.time_records = dict()

    def START(self, label):
        time_record_event_entry = self.time_records.setdefault(label, TimeRecordEventEntry(label))
        time_record_event_entry.START = time.time()

    def STOP(self, label):
        time_record_event_entry = self.time_records.setdefault(label, TimeRecordEventEntry(label))
        time_record_event_entry.END = time.time()

    def MARK(self, label):
        time_record_moment_entry = self.time_records.setdefault(label, TimeRecordMomentEntry(label))
        time_record_moment_entry.MARK = time.time()

    def duration(self, label):
        time_record_event_entry = self.time_records.get(label)
        try:
            assert time_record_event_entry is not None
            return time_record_event_entry.duration
        except AssertionError:
            raise ValueError('Time record "%s" does not exist' % time_record_event_entry)
        except AttributeError:
            raise ValueError('Time record "%s" does not have a "duration" attribute' % time_record_event_entry)

    def _get_timestamp(self, label):
        if '.' not in label:
            label += '.MARK'
        time_record_label, time_record_attr = label.rsplit('.', 1)
        time_record_entry = self.time_records.get(time_record_label)

        try:
            assert time_record_entry is not None
            return getattr(time_record_entry, time_record_attr)
        except AssertionError:
            raise ValueError('Time record "%s" does not exist' % time_record_label)
        except AttributeError:
            raise ValueError('Time record "%s" does not have a "%s" attribute' % (time_record_label, time_record_attr))

    def delta(self, start_label, end_label):
        return self._get_timestamp(end_label) - self._get_timestamp(start_label)


class TimeRecordEventEntry(object):
    def __init__(self, name):
        if isinstance(name, str) and '.' not in name:
            self.name = name
        else:
            raise ValueError('The label must not contain the "." character')
        self._START = None
        self._END = None

    @property
    def START(self):
        if self._START is not None:
            return self._START
        else:
            raise ValueError('Time record %s does not have a start label' % self.name)

    @START.setter
    def START(self, timestamp):
        if self._START is None:
            self._START = timestamp
        else:
            raise ValueError('Time record %s already has a start label' % self.name)

    @property
    def END(self):
        if self._END is not None:
            return self._END
        else:
            raise ValueError('Time record %s does not have an end label' % self.name)

    @END.setter
    def END(self, timestamp):
        if self._START is None:
            raise ValueError('Time record %s does not have a start label so an end label cannot be set' %
                             self.name)
        if self._END is None:
            self._END = timestamp
        else:
            raise ValueError('Time record %s already has an end label' % self.name)

    @property
    def duration(self):
        return self.END - self.START


class TimeRecordMomentEntry(object):
    def __init__(self, name):
        self.name = name
        self._MARK = None

    @property
    def MARK(self):
        if self._MARK is not None:
            return self._MARK
        else:
            raise ValueError('Time record %s does not have a mark label' % self.name)

    @MARK.setter
    def MARK(self, value):
        if self._MARK is None:
            self._MARK = value
        else:
            raise ValueError('Time record with name %s already has a timestamp' % self.name)
