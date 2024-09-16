"""Verify that init() calls the expected set of endpoints for each Daikin device."""

import pytest

from pydaikin.daikin_skyfi import DaikinSkyFi

from .test_init import client_session

assert client_session


@pytest.mark.asyncio
async def test_daikinSkiFi(aresponses, client_session):
    aresponses.add(
        path_pattern="/zones.cgi",
        method_pattern="GET",
        response="nz=8&zone1=Zone%201&zone2=Zone%202&zone3=Zone%203&zone4=Zone%204&zone5=Zone%205&zone6=Zone%206&zone7=Zone%207&zone8=Zone%208",
    )
    aresponses.add(
        path_pattern="/ac.cgi",
        method_pattern="GET",
        response="opmode=0&units=.&settemp=24.0&fanspeed=3&fanflags=3&acmode=16&tonact=0&toffact=0&prog=0&time=23:36&day=6&roomtemp=23&outsidetemp=0&louvre=1&zone=0&flt=0&test=0&errdata=146&sensors=1",
    )

    device = DaikinSkyFi('ip', session=client_session, password="xxxpasswordxxx")

    await device.init()

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()

    assert device["mode"] == '16'
    assert device.support_away_mode is False
    assert device.support_fan_rate is True
    assert device.support_swing_mode is False
    assert device.represent("zone1") == ("zone1", "Zone 1")
    assert device.represent("zone") == ('zone', '00000000')
    assert device.inside_temperature == 23.0
    assert device.target_temperature == 24.0
    assert device.outside_temperature == 0

    assert device.represent("mode") == ('mode', 'off')

    aresponses.add(
        path_pattern="/ac.cgi",
        method_pattern="GET",
        response="opmode=0&units=.&settemp=20.0&fanspeed=3&fanflags=1&acmode=16&tonact=0&toffact=0&prog=0&time=23:36&day=6&roomtemp=23&outsidetemp=0&louvre=1&zone=0&flt=0&test=0&errdata=146&sensors=1",
    )
    aresponses.add(
        path_pattern="/set.cgi",
        method_pattern="GET",
        response="opmode=1&units=.&settemp=20.0&fanspeed=3&fanflags=1&acmode=8&tonact=0&toffact=0&prog=0&time=23:36&day=6&roomtemp=23&outsidetemp=0&louvre=1&zone=0&flt=0&test=0&errdata=146&sensors=1",
    )

    await device.set({"mode": "cool"})
    aresponses.assert_all_requests_matched()
    assert device.represent("mode") == ('mode', 'cool')
    assert device.target_temperature == 20.0

    aresponses.add(
        path_pattern="/ac.cgi",
        method_pattern="GET",
        response="opmode=1&units=.&settemp=20.0&fanspeed=3&fanflags=1&acmode=8&tonact=0&toffact=0&prog=0&time=23:36&day=6&roomtemp=23&outsidetemp=0&louvre=1&zone=0&flt=0&test=0&errdata=146&sensors=1",
    )
    aresponses.add(
        path_pattern="/set.cgi",
        method_pattern="GET",
        response="opmode=0&units=.&settemp=20.0&fanspeed=3&fanflags=1&acmode=8&tonact=0&toffact=0&prog=0&time=23:36&day=6&roomtemp=23&outsidetemp=0&louvre=1&zone=0&flt=0&test=0&errdata=146&sensors=1",
    )
    await device.set({"mode": "off"})
    assert device.zones == [
        ('Zone 1', '0'),
        ('Zone 2', '0'),
        ('Zone 3', '0'),
        ('Zone 4', '0'),
        ('Zone 5', '0'),
        ('Zone 6', '0'),
        ('Zone 7', '0'),
        ('Zone 8', '0'),
    ]

    await device.set_zone(0, "zone_onoff_", 1)
    aresponses.add(
        path_pattern="/setzone.cgi",
        method_pattern="GET",
        response="opmode=0&units=.&settemp=20.0&fanspeed=3&fanflags=1&acmode=8&tonact=0&toffact=0&prog=0&time=23:36&day=6&roomtemp=23&outsidetemp=0&louvre=1&zone=128&flt=0&test=0&errdata=146&sensors=1",
    )
    await device.set_zone(0, "zone_onoff", 1)
