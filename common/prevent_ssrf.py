import re
import ipaddress
import socket

from django.conf import settings

class PreventSSRF:
    def is_ip_in_network(ip: str, network: str) -> bool:
        """
        Check if an IP address is in a network.
        """
        return ipaddress.ip_address(ip) in ipaddress.ip_network(network)

    def get_ip_from_hostname(hostname: str) -> str | None:
        """
        Get IP address from a hostname.
        """
        try:
            return socket.gethostbyname(hostname)
        except socket.gaierror:
            return None

    def is_host_allowed(hostname: str) -> bool:
        """
        Check if a host is allowed based on whitelist and blacklist.
        """
        ip = PreventSSRF.get_ip_from_hostname(hostname)

        try:
            if not ip:
                return False

            for network in settings.FORBIDDEN_HOSTS_BLACKLIST:
                if PreventSSRF.is_ip_in_network(ip, network):
                    return False

            if hostname not in settings.ALLOWED_HOSTS_WHITELIST:
                return False
        except Exception:
            return False

        return True

    def is_valid_url(url: str) -> bool:
        """
        Check if the given URI is valid.
        """
        regex = re.compile(
            r'^(?:http|ftp)s?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'
            r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        return re.match(regex, url) is not None