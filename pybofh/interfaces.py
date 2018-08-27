"""Module for network interfaces"""
import re

from pybofh import shell

IFCONFIG = "/sbin/ifconfig"
# regexes to parse ifconfig
REGEX_INTERFACE = r'([a-zA-Z0-9]+):.* mtu ([0-9]+)'
REGEX_ETHER = r'.*ether ([a-f0-9:]+).*'
REGEX_INET = r'.*inet ([0-9\.]+).*netmask ([0-9\.]+).*'
REGEX_INET6 = r'.*inet6 (.+?) .*prefixlen ([0-9]+).*'
REGEX_RXPACKETS = r'.*RX packets ([0-9]+).*'
REGEX_RXERRORS = r'.*RX errors ([0-9]+).*'
REGEX_TXPACKETS = r'.*TX packets ([0-9]+).*'
REGEX_TXERRORS = r'.*TX errors ([0-9]+).*'
# which regex contain which fields in which capture groups
REGEX_FIELDS = {
    REGEX_INTERFACE: ('name', 'mtu'),
    REGEX_ETHER: ('mac',),
    REGEX_INET: ('ipv4', 'netmask'),
    REGEX_INET6: ('ipv6',),
    REGEX_RXPACKETS: ('rx_packets',),
    REGEX_RXERRORS: ('rx_errors',),
    REGEX_TXPACKETS: ('tx_packets',),
    REGEX_TXERRORS: ('tx_errors',),
    }


class InexistentInterfaceError(Exception):
    def __init__(self, name):
        Exception.__init__(self, "Interface {} not found".format(name))

class Interface(object):
    """Represents a network interface"""
    def __init__(self, name, check_existence=True):
        self.name = name
        if check_existence:
            ifconfig_by_name(name) # raises exception if inexistent

    @property
    def data(self):
        return ifconfig_by_name(self.name)


class IfconfigEntry(object):
    # pylint: disable=too-many-instance-attributes, too-many-arguments
    def __init__(self, name, mtu, rx_packets, rx_errors, tx_packets, tx_errors, mac=None, ipv4=None, netmask=None, ipv6=None):
        self.name = name
        self.mtu = mtu
        self.rx_packets = rx_packets
        self.rx_errors = rx_errors
        self.tx_packets = tx_packets
        self.tx_errors = tx_errors
        self.mac = mac
        self.ipv4 = ipv4
        self.netmask = netmask
        self.ipv6 = ipv6
        assert isinstance(name, str)
        assert 0 < mtu <= 2**16
        if mac:
            assert mac.count(":") == 5
        if ipv4:
            assert ipv4.count(".") == 3
        if netmask:
            assert netmask.count(".") == 3
        assert isinstance(rx_packets, int)
        assert isinstance(rx_errors, int)
        assert isinstance(tx_packets, int)
        assert isinstance(tx_errors, int)

def ifconfig_by_name(name):
    """Returns a IfconfigEntry corresponding to the given interface name.
    Raises a exception if the interface is not found.
    """
    for intf in ifconfig():
        if intf.name == name:
            return intf
    raise InexistentInterfaceError(name)

def ifconfig():
    """Runs ifconfig -a, returns list of IfconfigEntry"""
    out = shell.get().check_output((IFCONFIG, "-a"))
    itfs = []
    current_itf = {}
    for line in out.splitlines():
        if line == "":
            # finished a interface
            itf = IfconfigEntry(**current_itf)
            itfs.append(itf)
            current_itf = {}
            continue
        for regex, fields in REGEX_FIELDS.items():
            match = re.match(regex, line)
            if match:
                for i, field in enumerate(fields):
                    val = match.group(1 + i)
                    try:
                        val = int(val)
                    except ValueError:
                        pass
                    current_itf[field] = val
    return itfs
