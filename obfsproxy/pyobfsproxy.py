#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This is the command line interface to py-obfsproxy.
It is designed to be a drop-in replacement for the obfsproxy executable.
Currently, not all of the obfsproxy command line options have been implemented.
"""

import sys
import argparse

import obfsproxy.network.launch_transport as launch_transport
import obfsproxy.transports.transports as transports
import obfsproxy.common.log as logging
import obfsproxy.common.heartbeat as heartbeat
import obfsproxy.managed.server as managed_server
import obfsproxy.managed.client as managed_client

from pyptlib.util import checkClientMode

from twisted.internet import task # for LoopingCall

log = logging.get_obfslogger()

def set_up_cli_parsing():
    """Set up our CLI parser. Register our arguments and options and
    query individual transports to register their own external-mode
    arguments."""

    parser = argparse.ArgumentParser(
        description='py-obfsproxy: A pluggable transports proxy written in Python')
    subparsers = parser.add_subparsers(title='supported transports', dest='name')

    parser.add_argument('--log-file', help='set logfile')
    parser.add_argument('--log-min-severity',
                        choices=['error', 'warning', 'info', 'debug'],
                        help='set minimum logging severity (default: %(default)s)')
    parser.add_argument('--no-log', action='store_true', default=False,
                        help='disable logging')
    parser.add_argument('--no-safe-logging', action='store_true',
                        default=False,
                        help='disable safe (scrubbed address) logging')

    # Managed mode is a subparser for now because there are no
    # optional subparsers: bugs.python.org/issue9253
    subparsers.add_parser("managed", help="managed mode")

    # Add a subparser for each transport. Also add a
    # transport-specific function to later validate the parsed
    # arguments.
    for transport, transport_class in transports.transports.items():
        subparser = subparsers.add_parser(transport, help='%s help' % transport)
        transport_class['client'].register_external_mode_cli(subparser)
        subparser.set_defaults(validation_function=transport_class['client'].validate_external_mode_cli)

    return parser

def do_managed_mode():
    """This function starts obfsproxy's managed-mode functionality."""

    if checkClientMode():
        log.info('Entering client managed-mode.')
        managed_client.do_managed_client()
    else:
        log.info('Entering server managed-mode.')
        managed_server.do_managed_server()

def do_external_mode(args):
    """This function starts obfsproxy's external-mode functionality."""

    assert(args)
    assert(args.name)
    assert(args.name in transports.transports)

    from twisted.internet import reactor

    launch_transport.launch_transport_listener(args.name, args.listen_addr, args.mode, args.dest, args.ext_cookie_file)
    log.info("Launched '%s' listener at '%s:%s' for transport '%s'." % \
                 (args.mode, log.safe_addr_str(args.listen_addr[0]), args.listen_addr[1], args.name))
    reactor.run()

def consider_cli_args(args):
    """Check out parsed CLI arguments and take the appropriate actions."""

    if args.log_file:
        log.set_log_file(args.log_file)
    if args.log_min_severity:
        log.set_log_severity(args.log_min_severity)
    if args.no_log:
        log.disable_logs()
    if args.no_safe_logging:
        log.set_no_safe_logging()

    # validate:
    if (args.name == 'managed') and (not args.log_file) and (args.log_min_severity):
        log.error("obfsproxy in managed-proxy mode can only log to a file!")
        sys.exit(1)
    elif (args.name == 'managed') and (not args.log_file):
        # managed proxies without a logfile must not log at all.
        log.disable_logs()

def run():
    parser = set_up_cli_parsing()

    args = parser.parse_args()

    consider_cli_args(args)

    log.debug('obfsproxy starting up!')
    log.debug('argv: ' + str(sys.argv))
    log.debug('args: ' + str(args))

    # Fire up our heartbeat.
    l = task.LoopingCall(heartbeat.heartbeat.talk)
    l.start(3600.0, now=False) # do heartbeat every hour

    # Initiate obfsproxy.
    if (args.name == 'managed'):
        do_managed_mode()
    else:
        # Pass parsed arguments to the appropriate transports so that
        # they can initialize and setup themselves. Exit if the
        # provided arguments were corrupted.

        # XXX use exceptions
        if (args.validation_function(args) == False):
            sys.exit(1)

        do_external_mode(args)

if __name__ == '__main__':
    run()