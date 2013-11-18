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
        self.downstream_counter = 0
        self.upstream_counter   = 0

    @classmethod
    def setup(cls, transport_config):
        """Setup the salty stream pluggable transport."""
        if not hasattr(cls, 'upstream_shared_secret') or not hasattr(cls, 'downstream_shared_secret'):
            # Check for shared-secret in the server transport options.
            transport_options = transport_config.getServerTransportOptions()

            log.debug("Setting upstream shared-secret from server transport options: '%s'", transport_options["upstream-shared-secret"])
            log.debug("Setting downstream shared-secret from server transport options: '%s'", transport_options["downstream-shared-secret"])

            cls.upstream_shared_secret = binascii.a2b_hex(transport_options["upstream-shared-secret"])
            cls.downstream_shared_secret = binascii.a2b_hex(transport_options["downstream-shared-secret"])
        else:
            cls.upstream_shared_secret = binascii.a2b_hex(cls.upstream_shared_secret)
            cls.downstream_shared_secret = binascii.a2b_hex(cls.downstream_shared_secret)

        log.info("SaltyStream setup: upstream-shared-secret %s" % binascii.b2a_hex(cls.upstream_shared_secret))
        log.info("SaltyStream setup: downstream-shared-secret %s" % binascii.b2a_hex(cls.downstream_shared_secret))

    def receivedDownstream(self, data, circuit):
        log.debug("receivedDownstream counter %s" % self.downstream_counter)

        # BUG: count with all the bits
        nonce      = pack('LLL', 0,0,self.downstream_counter)
        cipherText = nacl.crypto_stream_xor(data.read(), nonce, self.downstream_shared_secret)
        self.downstream_counter += 1
        circuit.upstream.write(cipherText)
        return

    def receivedUpstream(self, data, circuit):
        log.debug("receivedUpstream counter %s" % self.upstream_counter)

        # BUG: count with all the bits
        nonce     = pack('LLL', 0,0,self.upstream_counter)
        plainText = nacl.crypto_stream_xor(data.read(), nonce, self.upstream_shared_secret)
        self.upstream_counter += 1
        circuit.downstream.write(plainText)
        return

    @classmethod
    def register_external_mode_cli(cls, subparser):
        subparser.add_argument('--upstream-shared-secret', type=str, default='deadbeef8457a76eee0acf4e0158f5861ddbb8ad2728c9ad201686d3d654537e', help='shared secret for upstream nacl stream encoder/decoder')
        subparser.add_argument('--downstream-shared-secret', type=str, default='deadface537b43e6a0f5e18314ff4d2a830f6187ac4216412ba6bb5dc3bded40', help='shared secret for downstream nacl stream encoder/decoder')
        super(SaltyStreamTransport, cls).register_external_mode_cli(subparser)

    @classmethod
    def validate_external_mode_cli(cls, args):
        cls.upstream_shared_secret = args.upstream_shared_secret
        cls.downstream_shared_secret = args.downstream_shared_secret
        super(SaltyStreamTransport, cls).validate_external_mode_cli(args)


class SaltyStreamClient(SaltyStreamTransport):
    pass

class SaltyStreamServer(SaltyStreamTransport):
    pass
