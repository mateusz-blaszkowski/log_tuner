from datetime import datetime
from datetime import timedelta
import getopt
import os
import random
import re
import sys


"""
Sample usage:
python log_tuner.py -i samples/igk-extreme-os.txt \
        -o processed_samples/igk-extreme-os-processed.txt \
        -s 1000 -c IgkExtremeLogTune
"""


class LogTuner(object):
    """
    Base class for tuning logs.
    Log tuning is divided into two phases: 
    1. Sample (pretty small) log file is read and all repetitive data
       like datetime or IP addresses is stubbed, i.e. the following line
        "Apr 14 14:09:06 CET: Vlan3649 Grp 92 state Speak -> Standby"
       will be  replaced to:
        "CET: <vlan> Grp <grp> state Speak -> Standby"
    2. Having a list of common lines with stubbed data, new lines
       are generated. Stub data will be replaced with usually random data.
    """

    def __init__(self, log_file_path):
        self._IP_ADDRESS_STUB = "<IP_ADDRESS_STUB>"
        self.log_file_path = log_file_path
        self.log_lines = self._read_log_lines(log_file_path)
        self.common_log_lines = self.gather_common_log_lines()

    def _read_log_lines(self, log_file_path):
        with open(log_file_path) as log_file:
            log_lines = log_file.readlines()
        return log_lines

    def gather_common_log_lines(self):
        common_log_lines = []
        for line in self.log_lines:
            line = self._stub_date_and_time(line)
            line = self._stub_ip_addresses(line)
            line = self._stub_miscellaneous(line)
            common_log_lines.append(line)
        return common_log_lines

    def _stub_ip_addresses(self, line):
        """
        Replace all occurrences of IP addresses with <IP_ADDRESS_STUB> 
        """
        ips = re.findall(r'[0-9]+(?:\.[0-9]+){3}', line)
        for ip in ips:
            line = line.replace(ip, self._IP_ADDRESS_STUB, 10)
        return line

    def _stub_date_and_time(self, line):
        """
        Each log file has its own format of logging time, so the method
        is child-class specific and needs to be overwritten.
        """
        return line

    def _stub_miscellaneous(self, line):
        """
        Stub some log-specific miscellaneous data, i.e. Vlan number.
        """
        return line

    def generate_log(self, size_mb, output_file_path):
        """
        Generates log file with the specified size and at the specified path.
        """
        required_lines_num = self._calculate_required_number_of_lines(size_mb)
        generated_logs = []
        for i in range(0, required_lines_num):
            line = random.choice(self.common_log_lines)
            line = self._replace_ip_addresses_stub(line)
            line = self._replace_miscellaneous_stub(line)
            generated_logs.append(line)
        generated_logs = self._replace_date_and_time_stub(lines=generated_logs)
        with open(output_file_path, 'w') as output_file:
            output_file.writelines(generated_logs)

    def _calculate_required_number_of_lines(self, size_mb):
        """
        Based on the sample log file, calculates required number of lines
        in the output file so that its size will be pretty much equals to
        size_mb
        """
        requested_size_b = size_mb * 1024 * 1024
        sample_log_lines_number = len(self.log_lines)
        sample_log_file_size = os.stat(self.log_file_path).st_size
        avg_line_size = sample_log_file_size / sample_log_lines_number
        number_of_lines_in_output_file = requested_size_b / avg_line_size
        return number_of_lines_in_output_file

    def _replace_ip_addresses_stub(self, line):
        """
        Replaces <IP_ADDRESS_STUB> with random IP address. 
        """
        random_ip = '.'.join('%s' % random.randint(0, 255) for i in range(4))
        return line.replace(self._IP_ADDRESS_STUB, random_ip, 10)

    def _replace_date_and_time_stub(self, lines):
        """
        Replaces datetime in log line. Needs to be overwritten in child class.
        """
        return lines

    def _replace_miscellaneous_stub(self, line):
        """
        Replaces miscellaneous data specific to a sample log file.
        Needs to be overwritten in child class.
        """
        return lines


class IgkExtremeLogTuner(LogTuner):

    def __init__(self, log_file_path):
        self._LAST_SECONDS_STUB = "<times_number> additional times in the " \
                                  "last <seconds_number> second"
        super(IgkExtremeLogTuner, self).__init__(log_file_path)

    def _stub_date_and_time(self, line):
        """
        Just removes first 22 characters as each log line has a datetime 
        at the beginning of the line.
        """
        if not line:
            return line
        return line[22:]

    def _stub_miscellaneous(self, line):
        """
        Finds "<number> additional times in the last <number> second(s)"
        """
        last_seconds_regex = re.findall(r'\d+ additional times in the '
                                        r'last \d+ second', line)
        for regex in last_seconds_regex:
            line = line.replace(regex, self._LAST_SECONDS_STUB)
        return line

    def _replace_date_and_time_stub(self, lines):
        """
        Adds a datetime at the beginning of each line. 
        """
        generated_datetime = datetime.strptime("05/10/2017 07:25:58.11",
                                               "%m/%d/%Y %H:%M:%S.%f")
        generated_lines = []
        for line in lines:
            if not line.strip():
                generated_lines.append(line)
                continue
            delta = timedelta(milliseconds=random.randint(0, 100))
            generated_datetime += delta
            line = generated_datetime.strftime("%m/%d/%Y %H:%M:%S.%f")[:-4] + \
                   line
            generated_lines.append(line)
        return generated_lines

    def _replace_miscellaneous_stub(self, line):
        """
        Replaces "<number> additional times in the last <number> second(s)"
        """
        if not line:
            return line
        times = str(random.randint(1, 300))
        seconds = str(random.randint(1, 100))
        last_seconds_stub = self._LAST_SECONDS_STUB.replace("<times_number>", times)\
                                                   .replace("<seconds_number>", seconds)
        line = line.replace(self._LAST_SECONDS_STUB, last_seconds_stub)
        return line


class CiscoWlcLogTuner(LogTuner):

    def __init__(self, log_file_path):
        self._MAC_STUB = "<MAC>"
        self._DATETIME_STUB = "<DATETIME_STUB>"
        self._random_macs = self._generate_macs(macs_number=10000)
        super(CiscoWlcLogTuner, self).__init__(log_file_path)

    def _generate_macs(self, macs_number):
        """
        Generates MAC addresses first and then use
        random.choice(random_macs) because it's much faster than
        generating mac addresses on the fly for each line
        """
        macs = []
        for i in range(0, macs_number):
            generated_mac = "%02x:%02x:%02x:%02x:%02x:%02x" % (
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
            )
            macs.append(generated_mac)
        return macs

    def _stub_date_and_time(self, line):
        """
        Finds occurrences of timestamp and replaces them with <DATETIME_STUB>
        """
        times = re.findall(r'\d{2}:\d{2}:\d{2}\.\d{3}', line)
        for time in times:
            line = line.replace(time, self._DATETIME_STUB)
        return line

    def _stub_miscellaneous(self, line):
        """
        Finds MAC addresses and replaces them with <MAC>
        """
        mac_regex = re.compile(ur'([0-9a-f]{2}(?::[0-9a-f]{2}){5})',
                               re.IGNORECASE)
        mac_addresses = re.findall(mac_regex, line)
        for mac in mac_addresses:
            line = line.replace(mac, self._MAC_STUB, 10)
        return line

    def _replace_date_and_time_stub(self, lines):
        """
        Replaces <DATETIME_STUB> with generated timestamps
        """
        generated_datetime = datetime.strptime("14:14:51.655", "%H:%M:%S.%f")
        generated_lines = []
        for line in lines:
            delta = timedelta(milliseconds=random.randint(0, 100))
            generated_datetime += delta
            line = line.replace(self._DATETIME_STUB,
                                generated_datetime.strftime("%H:%M:%S.%f")[:-3])
            generated_lines.append(line)
        return generated_lines

    def _replace_miscellaneous_stub(self, line):
        """
        Replaces <MAC> occurrences with random MAC numbers 
        """
        mac = random.choice(self._random_macs)
        line = line.replace(self._MAC_STUB, mac, 10)
        return line


class CiscoIosLogTuner(LogTuner):

    def __init__(self, log_file_path):
        self._VLAN_STUB = "<vlan>"
        self._GRP_STUB = "<grp>"
        super(CiscoIosLogTuner, self).__init__(log_file_path)

    def _stub_date_and_time(self, line):
        """
        Just removes first 15 characters as each log line has a datetime 
        at the beginning of the line.
        """
        if not line:
            return line
        return line[15:]

    def _stub_miscellaneous(self, line):
        """
        Replaces "Vlan<number>" and "Grp <number>" occurrences with stubs  
        """
        vlan_regex = re.findall(r'Vlan\d+', line)
        for regex in vlan_regex:
            line = line.replace(regex, self._VLAN_STUB)

        grp_regex = re.findall(r'Grp \d+', line)
        for regex in grp_regex:
            line = line.replace(regex, self._GRP_STUB)
        return line

    def _replace_date_and_time_stub(self, lines):
        """
        Adds a datetime at the beginning of each line. 
        """
        generated_datetime = datetime.strptime("Feb 11 08:05:11.000",
                                               "%b %d %H:%M:%S.%f")
        generated_lines = []
        for line in lines:
            delta = timedelta(milliseconds=random.randint(0, 100))
            generated_datetime += delta
            line = generated_datetime.strftime("%b %d %H:%M:%S.%f")[:-4] + line
            generated_lines.append(line)
        return generated_lines

    def _replace_miscellaneous_stub(self, line):
        """
        Replaces Vlan and Grp occurrences with random data.
        """
        random_vlan = "Vlan" + str(random.randint(1, 5000))
        line = line.replace(self._VLAN_STUB, random_vlan)
        random_grp = "Grp " + str(random.randint(1, 300))
        line = line.replace(self._GRP_STUB, random_grp)
        return line


if __name__ == "__main__":
    options, _ = getopt.getopt(sys.argv[1:], 'i:o:s:c:')
    input_filepath = None
    output_filepath = None
    size = None
    class_name = None
    for opt, arg in options:
        if opt == "-i":
            input_filepath = arg
        elif opt == "-o":
            output_filepath = arg
        elif opt == "-s":
            size = int(arg)
        elif opt == "-c":
            class_name = arg
    for param in [input_filepath, output_filepath, size, class_name]:
        if param is None:
            print "One of the required parameters is not set."
            print "Usage: python log_tuner -i <input_filepath> " \
                  "-o <output_filepath> -i <size_in_mb> " \
                  "-c <LogTuner_subclass_name>"
            sys.exit(1)

    classes = {
        "CiscoIosLogTuner": CiscoIosLogTuner,
        "CiscoWlcLogTuner": CiscoWlcLogTuner,
        "IgkExtremeLogTuner": IgkExtremeLogTuner
    }

    if class_name not in classes.keys():
        print "Invalid class name: %s. Use one of: %s" % (class_name,
                                                          classes.keys())
        sys.exit(1)
    log_tuner = classes[class_name](input_filepath)
    log_tuner.generate_log(size, output_filepath)
