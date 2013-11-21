#!/usr/bin/env python

from obfsproxy.transports.base import BaseTransport
import obfsproxy.common.log as logging
from obfsproxy.network.buffer import Buffer

# This version of pynacl has the crypto_stream api:
# https://github.com/seanlynch/pynacl
import nacl
import binascii
import sys
from struct import pack, unpack

log = logging.get_obfslogger()

class SaltyStreamBuffer( object ):
    """
    encrypts/decrypts Salty Stream messages
    """
    HEADER_LEN = 4

    def __init__(self, shared_secret = None):
        self.sharedSecret = shared_secret
        self.payloadLen   = None
        self.counter      = 1
        self.messageBuf   = Buffer()

    def streamCrypt(self, data):
        # BUG: count with all 24 bytes
        nonce = pack('LLL', 0,0,self.counter)
        output = nacl.crypto_stream_xor(data, nonce, self.sharedSecret)
        self.counter += 1
        return output

    def encrypt(self, data):
        output = Buffer()
        packed_len = pack('i', len(data))
        output.write(packed_len)
        cipherText = self.streamCrypt(data.read())
        output.write(cipherText)
        return output.read()

    def decrypt(self, data):
        output = Buffer()
        self.messageBuf.write(data.read())

        while len(self.messageBuf) >= self.HEADER_LEN:
            if self.payloadLen is None:
                self.payloadLen = unpack("i", str(self.messageBuf.read(self.HEADER_LEN)))[0]

            if len(self.messageBuf) < self.payloadLen:
                break

            output.write(self.streamCrypt(self.messageBuf.read(self.payloadLen)))
            self.payloadLen = None

        if len(output) == 0:
            return None
        else:
            return output.read()


class SaltyStreamTransport(BaseTransport):
    
    def __init__(self, transport_config):
        self.downstreamMessageExtractor = SaltyStreamBuffer(shared_secret = self.downstream_shared_secret)
        self.upstreamMessageExtractor   = SaltyStreamBuffer(shared_secret = self.upstream_shared_secret)

    @classmethod
    def setup(cls, transport_config):
        """Setup the salty stream pluggable transport."""

        if not hasattr(cls, 'upstream_shared_secret') or not hasattr(cls, 'downstream_shared_secret'):
            # Check for shared-secret in the server transport options.
            transport_options = transport_config.getServerTransportOptions()
            cls.upstream_shared_secret_hex   = transport_options["upstream-shared-secret"]
            cls.downstream_shared_secret_hex = transport_options["downstream-shared-secret"]
        else:
            cls.upstream_shared_secret_hex   = cls.upstream_shared_secret
            cls.downstream_shared_secret_hex = cls.downstream_shared_secret

        if len(cls.upstream_shared_secret_hex) != (nacl.crypto_stream_KEYBYTES * 2) or len(cls.downstream_shared_secret_hex) != (nacl.crypto_stream_KEYBYTES * 2):
            log.error("SaltyStream setup error: invalid length key(s)")
            sys.exit(1)

        cls.upstream_shared_secret   = binascii.a2b_hex(cls.upstream_shared_secret_hex)
        cls.downstream_shared_secret = binascii.a2b_hex(cls.downstream_shared_secret_hex)

        log.info("SaltyStream setup: upstream-shared-secret %s" % binascii.b2a_hex(cls.upstream_shared_secret))
        log.info("SaltyStream setup: downstream-shared-secret %s" % binascii.b2a_hex(cls.downstream_shared_secret))

    def receivedDownstream(self, data, circuit):
        plainText = self.downstreamMessageExtractor.decrypt(data)
        if plainText is not None:
            circuit.upstream.write(plainText)
        return

    def receivedUpstream(self, data, circuit):
        cipherText = self.upstreamMessageExtractor.encrypt(data)
        circuit.downstream.write(cipherText)
        return
        
    @classmethod
    def register_external_mode_cli(cls, subparser):
        subparser.add_argument('--upstream-shared-secret', type=str, default='', help='shared secret for upstream nacl stream encoder/decoder')
        subparser.add_argument('--downstream-shared-secret', type=str, default='', help='shared secret for downstream nacl stream encoder/decoder')
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
