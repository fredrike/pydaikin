"""Tests for the Discovery module."""

import socket
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from pydaikin.discovery import (
    DISCOVERY_MSG,
    UDP_DST_PORT,
    Discovery,
    get_devices,
    get_name,
)


def _addr(family, address, broadcast):
    """Build a mock psutil net_if_addrs address entry."""
    return SimpleNamespace(
        family=family,
        address=address,
        netmask="255.255.255.0",
        broadcast=broadcast,
    )


def _fake_socket():
    sock = Mock()
    sock.sendto.return_value = None
    sock.recvfrom.side_effect = socket.timeout()
    return sock


def test_poll_broadcasts_to_all_interface_broadcasts():
    """Broadcast is sent to every IPv4 interface broadcast address."""
    addrs = {
        "en0": [
            _addr(socket.AF_INET, "192.168.1.5", "192.168.1.255"),
            _addr(socket.AF_INET6, "fe80::1", None),
        ],
        "en1": [_addr(socket.AF_INET, "10.0.0.5", "10.0.0.255")],
        "lo0": [_addr(socket.AF_INET, "127.0.0.1", None)],
    }
    sock = _fake_socket()
    with (
        patch("psutil.net_if_addrs", return_value=addrs),
        patch("socket.socket", return_value=sock),
    ):
        discovery = Discovery()
        result = discovery.poll()

    targets = {call.args[1][0] for call in sock.sendto.call_args_list}
    assert targets == {"192.168.1.255", "10.0.0.255"}
    msg = bytes(DISCOVERY_MSG, "UTF-8")
    for call in sock.sendto.call_args_list:
        assert call.args[0] == msg
        assert call.args[1][1] == UDP_DST_PORT
    assert list(result) == []


def test_poll_with_ip_only_sends_to_given_ip():
    """When an ip is given, only that address is used as broadcast target."""
    sock = _fake_socket()
    with patch("socket.socket", return_value=sock):
        discovery = Discovery()
        discovery.poll(ip="192.168.1.255")

    sock.sendto.assert_called_once_with(
        bytes(DISCOVERY_MSG, "UTF-8"), ("192.168.1.255", UDP_DST_PORT)
    )


def test_poll_returns_discovered_devices():
    """Devices answering the broadcast are parsed and returned."""
    response = b"ret=OK,type=aircon,mac=409F38D107AC,name=Test,port=30050"
    sock = _fake_socket()
    sock.recvfrom.side_effect = [(response, ("192.168.1.10", 30050)), socket.timeout()]
    addrs = {"en0": [_addr(socket.AF_INET, "192.168.1.5", "192.168.1.255")]}
    with (
        patch("psutil.net_if_addrs", return_value=addrs),
        patch("socket.socket", return_value=sock),
    ):
        discovery = Discovery()
        devices = list(discovery.poll())

    assert len(devices) == 1
    device = devices[0]
    assert device["mac"] == "409F38D107AC"
    assert device["ip"] == "192.168.1.10"
    assert device["port"] == 30050


def test_poll_stops_when_device_name_matches():
    """Polling stops early when a device matching stop_if_found responds."""
    response = b"ret=OK,type=aircon,mac=409F38D107AC,name=Living Room,port=30050"
    sock = _fake_socket()
    sock.recvfrom.side_effect = [(response, ("192.168.1.10", 30050))]
    addrs = {"en0": [_addr(socket.AF_INET, "192.168.1.5", "192.168.1.255")]}
    with (
        patch("psutil.net_if_addrs", return_value=addrs),
        patch("socket.socket", return_value=sock),
    ):
        discovery = Discovery()
        devices = list(discovery.poll(stop_if_found="living room"))

    assert len(devices) == 1
    assert devices[0]["name"] == "Living Room"
    sock.recvfrom.assert_called_once()


@pytest.mark.parametrize("response", [b"garbage", b"ret=ERR,err=0"])
def test_poll_ignores_invalid_responses(response):
    """Invalid or error responses are ignored without raising."""
    sock = _fake_socket()
    sock.recvfrom.side_effect = [(response, ("192.168.1.99", 30050)), socket.timeout()]
    addrs = {"en0": [_addr(socket.AF_INET, "192.168.1.5", "192.168.1.255")]}
    with (
        patch("psutil.net_if_addrs", return_value=addrs),
        patch("socket.socket", return_value=sock),
    ):
        discovery = Discovery()
        devices = list(discovery.poll())

    assert devices == []


def test_get_devices():
    """get_devices() returns the devices found via broadcast."""
    sock = _fake_socket()
    with (
        patch("psutil.net_if_addrs", return_value={}),
        patch("socket.socket", return_value=sock),
    ):
        assert list(get_devices()) == []


def test_get_name_returns_matching_device():
    """get_name returns the discovered device matching the requested name."""
    response = b"ret=OK,type=aircon,mac=409F38D107AC,name=Living Room,port=30050"
    sock = _fake_socket()
    sock.recvfrom.side_effect = [(response, ("192.168.1.10", 30050))]
    addrs = {"en0": [_addr(socket.AF_INET, "192.168.1.5", "192.168.1.255")]}
    with (
        patch("psutil.net_if_addrs", return_value=addrs),
        patch("socket.socket", return_value=sock),
    ):
        device = get_name("living room")

    assert device["mac"] == "409F38D107AC"
    assert device["name"] == "Living Room"


def test_get_name_permission_error(monkeypatch):
    """get_name returns None when polling raises PermissionError."""

    def raise_permission_error(*args, **kwargs):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(Discovery, "poll", raise_permission_error)
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: Mock())

    assert get_name("Living Room") is None
