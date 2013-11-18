#!/usr/bin/env python

from obfsproxy.transports.base import BaseTransport
import obfsproxy.common.log as logging
from obfsproxy.network.buffer import Buffer

# This version of pynacl has the crypto_stream api:
# https://github.com/seanlynch/pynacl
import nacl
import binascii
import sys
from struct import pack

log = logging.get_obfslogger()

class SaltyStreamTransport(BaseTransport):
    
    def __init__(self, transport_config):
        self.downstreamCounter = 0
        self.upstreamCounter   = 0

    @classmethod
    def setup(cls, transport_config):
        """Setup the salty stream pluggable transport."""
        if not hasattr(cls, 'shared_secret'):
            # Check for shared-secret in the server transport options.
            transport_options = transport_config.getServerTransportOptions()
            if transport_options and "shared-secret" in transport_options:
                log.debug("Setting shared-secret from server transport options: '%s'", transport_options["shared-secret"])
                cls.shared_secret = binascii.a2b_hex(transport_options["shared-secret"])

            else:
                log.error("Cannot start salty stream without shared secret")
                sys.exit(0)
        else:
            cls.shared_secret = binascii.a2b_hex(cls.shared_secret)

        log.info("SaltyStream setup: shared-secret %s" % binascii.b2a_hex(cls.shared_secret))

    def receivedDownstream(self, data, circuit):
        # BUG: count with all the bits
        nonce      = pack('LLL', 0,0,self.downstreamCounter)
        cipherText = nacl.crypto_stream_xor(data.read(), nonce, self.shared_secret)
        circuit.upstream.write(cipherText)
        self.downstreamCounter += 1
        return

    def receivedUpstream(self, data, circuit):
        # BUG: count with all the bits
        nonce     = pack('LLL', 0,0,self.upstreamCounter)
        plainText = nacl.crypto_stream_xor(data.read(), nonce, self.shared_secret)
        circuit.downstream.write(plainText)
        self.upstreamCounter += 1
        return

    @classmethod
    def register_external_mode_cli(cls, subparser):
        subparser.add_argument('--shared-secret', type=str, default='abc123', help='shared secret for nacl stream encoder/decoder')
        super(SaltyStreamTransport, cls).register_external_mode_cli(subparser)

    @classmethod
    def validate_external_mode_cli(cls, args):
        cls.shared_secret = args.shared_secret
        super(SaltyStreamTransport, cls).validate_external_mode_cli(args)


class SaltyStreamClient(SaltyStreamTransport):
    pass

class SaltyStreamServer(SaltyStreamTransport):
    pass
