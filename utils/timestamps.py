#
# Copyright (c) 2018 by Spirent Communications Plc.
# All Rights Reserved.
#
# This software is confidential and proprietary to Spirent Communications Inc.
# No part of this software may be reproduced, transmitted, disclosed or used
# in violation of the Software License Agreement without the expressed
# written consent of Spirent Communications Inc.
#
#


import collections
import time


class TimeRecord(object):
    """
    This class is used for creating and storing time record objects.

    Attributes:
        time_records:   Dictionary containing time record names as keys and time record objects as values.
        dump_dict:      Ordered dictionary containing object names as keys and timestamps as values.
    """
    def __init__(self):
        """
        This method initializes the time records dictionary.
        """
        self.time_records = collections.OrderedDict()
        self.dump_dict = collections.OrderedDict()

    def START(self, label):
        """
        This method creates a time record object of type TimeRecordEventEntry and sets its start label.

        :param label:   Name of the time record object.
        :return:        None.
        """
        time_record_event_entry = self.time_records.setdefault(label, TimeRecordEventEntry(label))
        time_record_event_entry.START = time.time()

    def END(self, label):
        """
        This method creates a time record object of type TimeRecordEventEntry and sets its end label.

        :param label:   Name of the time record object.
        :return:        None.
        """
        time_record_event_entry = self.time_records.setdefault(label, TimeRecordEventEntry(label))
        time_record_event_entry.END = time.time()

    def MARK(self, label):
        """
        This method created a time record object of type TimeRecordMomentEntry and sets its timestamp.

        :param label:   Name of the time record object.
        :return:        None.
        """
        time_record_moment_entry = self.time_records.setdefault(label, TimeRecordMomentEntry(label))
        time_record_moment_entry.MARK = time.time()

    def duration(self, label):
        """
        This method calls the "duration" method on a time record object of type TimeRecordEventEntry.

        :param label:   Name of the time record object.
        :return:        The value returned by the duration method.
        """
        time_record_event_entry = self.time_records.get(label)
        try:
            assert time_record_event_entry is not None
            return time_record_event_entry.duration
        except AssertionError:
            raise ValueError('Time record "%s" does not exist' % label)
        except AttributeError:
            raise ValueError('Time record "%s" does not have a "duration" attribute' % time_record_event_entry)

    def delta(self, start_label, end_label):
        """
        This method subtracts the provided start label from the provided end label.

        :param start_label: Floating number representing the start label.
        :param end_label:   Floating number representing the end label.
        :return:            Subtraction result.
        """
        return self._get_timestamp(end_label) - self._get_timestamp(start_label)

    def _get_timestamp(self, label):
        """
        This method gets the time stamp for the provided label, if available.

        :param label:   Name of the label.
        :return:        Time stamp corresponding to the label.
        """
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

    def dump_data(self):
        """
        This method calls the dump_data method on each object in the time_records dictionary.

        :return:    Ordered dictionary containing object names as keys and timestamps as values.
        """
        for label in self.time_records:
            self.dump_dict.update(self.time_records[label].dump_data())
        return self.dump_dict


class TimeRecordEventEntry(object):
    """
    This class is used for time record entries that have a "start" label and an "end" label.

    Attributes:
        name:   Name of the time record.
        _START:     Floating number representing the start timestamp.
        _END:       Floating number representing the end timestamp.
        dump_dict:  Dictionary containing object name as key and timestamps as values.
    """
    def __init__(self, name):
        """
        This method sets the name of the time record to the provided name and the start and end labels to None.

        :param name: Name of the time record. It must not contain character "."
        """
        if isinstance(name, str) and '.' not in name:
            self.name = name
        else:
            raise ValueError('The label must not contain the "." character')
        self._START = None
        self._END = None
        self.dump_dict = collections.OrderedDict()

    @property
    def START(self):
        """
        This method returns the start timestamp of the time record.
        """
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
        """
        This method returns the end timestamp of the time record.
        """
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
        """
        This method subtracts the start timestamp from the end timestamp.

        :return: The subtraction result.
        """
        return self.END - self.START

    def dump_data(self):
        """
        This method dumps the current object name and timestamps in an ordered dictionary.

        :return:    Ordered dictionary containing object name as key and timestamps as values.
        """
        if self._START is not None:
            self.dump_dict[self.name + '.START'] = self._START
        if self._END is not None:
            self.dump_dict[self.name + '.END'] = self._END
        return self.dump_dict


class TimeRecordMomentEntry(object):
    """
    This class is used for time record entries that have only one label.

    Attributes:
        name:       Name of the time record.
        _MARK:      Floating number representing the timestamp.
        dump_dict:  Dictionary containing object name as key and timestamp as value.
    """
    def __init__(self, name):
        """
        This method sets the name of the time record and the timestamp to None.

        :param name:    Name of the time record. It must not contain character "."
        """
        if isinstance(name, str) and '.' not in name:
            self.name = name
        else:
            raise ValueError('The label must not contain the "." character')
        self._MARK = None
        self.dump_dict = dict()

    @property
    def MARK(self):
        """
        This method returns the timestamp of the time record.

        :return:
        """
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

    def dump_data(self):
        """
        This method dumps the name of the object and the timestamp in a dictionary.

        :return:    Dictionary containing object name as key and timestamp as value.
        """
        self.dump_dict = {self.name: self._MARK}
        return self.dump_dict
